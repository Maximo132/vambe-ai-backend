from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
import secrets
import pyotp
import qrcode
from io import BytesIO
import base64

from fastapi import (
    APIRouter, Depends, HTTPException, status, Request, 
    Response, Header, Body, Query
)
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import EmailStr, HttpUrl, ValidationError

from app.core.security import (
    create_access_token, 
    create_refresh_token,
    get_password_hash, 
    verify_password,
    verify_refresh_token,
    generate_password_reset_token,
    verify_password_reset_token,
    generate_email_verification_token,
    verify_email_verification_token,
    get_client_ip,
    get_user_agent
)
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User as UserModel, UserRole, AuthToken, Device, LoginHistory
from app.schemas.auth import (
    Token, UserCreate, UserInDB, UserRegister, UserResponse, UserUpdate,
    PasswordResetRequest, PasswordResetConfirm, TwoFactorSetupResponse,
    TwoFactorVerify, TwoFactorBackupCodes, DeviceInfo, SessionInfo,
    OAuth2Provider, OAuth2Token, OAuth2UserInfo, Message
)
from app.services.auth_service import AuthService
from app.core.security import oauth2_scheme

# Importar utilidades de correo
from app.utils.email_utils import send_email

# Importar CRUD
from app.crud import user as crud_user

# Configuración del router
router = APIRouter(tags=["auth"])

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> UserModel:
    """
    Obtiene el usuario actual a partir del token JWT.
    
    Verifica que el token sea válido, no esté revocado y no haya expirado.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó el token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar si el token está en la base de datos y no ha sido revocado
    db_token = db.query(AuthToken).filter(
        AuthToken.token == token,
        AuthToken.revoked == False,
        AuthToken.expires_at > datetime.utcnow()
    ).first()
    
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Obtener el usuario
    user = db.query(UserModel).filter(UserModel.id == db_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo o eliminado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Actualizar last_used_at del token
    db_token.last_used_at = datetime.utcnow()
    db.commit()
    
    # Almacenar el token en el estado de la solicitud para uso posterior
    request.state.auth_token = token
    request.state.current_user = user
    
    return user

@router.post("/login", response_model=Token, summary="Iniciar sesión")
async def login(
    request: Request,
    response: Response,
    user_login: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Iniciar sesión con email/username y contraseña.
    
    Devuelve tokens de acceso y actualización.
    """
    try:
        # Autenticar al usuario
        auth_result = await AuthService.login(
            db=db,
            user_login=user_login,
            request=request
        )
        
        # Si se requiere 2FA, devolver respuesta con indicador
        if auth_result.get("requires_2fa"):
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "message": "Se requiere autenticación de dos factores",
                    "requires_2fa": True,
                    "user_id": str(auth_result["user_id"]),
                    "email": auth_result.get("email")
                }
            )
        
        # Configurar cookies seguras para el frontend (opcional)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {auth_result['access_token']}",
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            secure=not settings.DEBUG,
            samesite="lax"
        )
        
        return auth_result
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error en el inicio de sesión: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en el servidor al procesar la solicitud de inicio de sesión"
        )

@router.post("/token", response_model=Token, include_in_schema=False)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Endpoint compatible con OAuth2 para obtener token de acceso.
    Mantenido para compatibilidad con clientes OAuth2.
    """
    # Convertir OAuth2PasswordRequestForm a UserLogin
    user_login = UserLogin(
        username=form_data.username,
        password=form_data.password,
        remember_me=False
    )
    
    # Llamar al endpoint de login normal
    result = await login(request, Response(), user_login, db)
    
    # Si es una respuesta de 2FA, devolver error 400 para OAuth2
    if isinstance(result, JSONResponse) and result.status_code == 202:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requiere autenticación de dos factores"
        )
    
    return result

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Registrar nuevo usuario")
async def register_user(
    request: Request,
    response: Response,
    user_in: UserRegister,
    db: Session = Depends(get_db),
):
    """
    Registrar un nuevo usuario en el sistema.
    
    Si la verificación de correo está habilitada, se enviará un correo de verificación.
    """
    try:
        # Registrar el nuevo usuario
        result = await AuthService.register_user(
            db=db,
            user_in=user_in,
            request=request
        )
        
        # Si la verificación de correo no es obligatoria, devolver tokens
        if not settings.EMAIL_VERIFICATION_REQUIRED and result.get("access_token"):
            # Configurar cookie segura para el frontend
            response.set_cookie(
                key="access_token",
                value=f"Bearer {result['access_token']}",
                httponly=True,
                max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                secure=not settings.DEBUG,
                samesite="lax"
            )
            
            # Si hay refresh token, configurar cookie
            if result.get("refresh_token"):
                response.set_cookie(
                    key="refresh_token",
                    value=result["refresh_token"],
                    httponly=True,
                    max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
                    secure=not settings.DEBUG,
                    samesite="lax"
                )
            
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content=result
            )
        
        # Si se requiere verificación de correo, devolver mensaje
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Usuario registrado exitosamente. Por favor verifica tu correo electrónico.",
                "requires_email_verification": True,
                "user_id": str(result.id) if hasattr(result, "id") else None
            }
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"Error al registrar usuario: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al registrar el usuario"
        )

@router.get("/me", response_model=UserInDB)
async def read_users_me(current_user: UserModel = Depends(get_current_user)):
    """
    Get current user
    """
    return current_user

@router.get("/me/role")
async def read_user_role(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener el rol del usuario actual.
    """
    try:
        return {"role": current_user.role}
    except Exception as e:
        logger.error(f"Error al obtener el rol del usuario: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener el rol del usuario"
        )

@router.post("/verify-email", response_model=Message, summary="Verificar correo electrónico")
async def verify_email(
    token: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Verificar la dirección de correo electrónico de un usuario.
    
    El token debe ser el que se envió por correo electrónico.
    """
    try:
        # Verificar el token
        email = verify_email_verification_token(token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de verificación inválido o expirado"
            )
        
        # Buscar al usuario por correo
        user = crud_user.get_by_email(db, email=email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Verificar si el correo ya está verificado
        if user.is_verified:
            return {"message": "El correo electrónico ya ha sido verificado"}
        
        # Marcar el correo como verificado
        user.is_verified = True
        user.verified_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Correo electrónico verificado exitosamente"}
        
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"Error al verificar el correo electrónico: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al verificar el correo electrónico"
        )

@router.post("/resend-verification-email", response_model=Message, summary="Reenviar correo de verificación")
async def resend_verification_email(
    email: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Reenviar el correo de verificación.
    """
    try:
        # Buscar al usuario por correo
        user = crud_user.get_by_email(db, email=email)
        if not user:
            # Por seguridad, no revelamos si el correo existe o no
            return {"message": "Si el correo está registrado, recibirás un enlace de verificación"}
        
        # Verificar si el correo ya está verificado
        if user.is_verified:
            return {"message": "El correo electrónico ya ha sido verificado"}
        
        # Generar un nuevo token de verificación
        token = generate_email_verification_token(user.email)
        
        # Enviar el correo de verificación
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        
        await send_email(
            email_to=user.email,
            subject="Verifica tu correo electrónico",
            template_name="email_verification.html",
            context={
                "name": user.full_name or user.username,
                "verification_url": verification_url,
                "support_email": settings.SUPPORT_EMAIL
            }
        )
        
        return {"message": "Correo de verificación enviado exitosamente"}
        
    except Exception as e:
        logger.error(f"Error al reenviar el correo de verificación: {str(e)}", exc_info=True)
        # Por seguridad, no revelamos el error real
        return {"message": "Si el correo está registrado, recibirás un enlace de verificación"}

@router.post("/password/forgot", response_model=Message, status_code=status.HTTP_202_ACCEPTED, summary="Solicitar restablecimiento de contraseña")
async def forgot_password(
    request: Request,
    email: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Solicitar un enlace para restablecer la contraseña.
    
    Se enviará un correo con un enlace para restablecer la contraseña.
    """
    try:
        # Buscar al usuario por correo
        user = crud_user.get_by_email(db, email=email)
        if not user:
            # Por seguridad, no revelamos si el correo existe o no
            return {"message": "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña"}
        
        # Generar token de restablecimiento
        token = generate_password_reset_token(user.email)
        
        # Construir la URL de restablecimiento
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        
        # Enviar el correo de restablecimiento
        await send_email(
            email_to=user.email,
            subject="Restablece tu contraseña",
            template_name="password_reset.html",
            context={
                "name": user.full_name or user.username,
                "reset_url": reset_url,
                "ip_address": get_client_ip(request),
                "user_agent": get_user_agent(request),
                "support_email": settings.SUPPORT_EMAIL,
                "expire_hours": settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS
            }
        )
        
        return {"message": "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña"}
        
    except Exception as e:
        logger.error(f"Error al procesar la solicitud de restablecimiento: {str(e)}", exc_info=True)
        # Por seguridad, no revelamos el error real
        return {"message": "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña"}

@router.post("/password/reset", response_model=Message, summary="Restablecer contraseña")
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Restablecer la contraseña usando un token de restablecimiento.
    """
    try:
        # Verificar el token
        email = verify_password_reset_token(reset_data.token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de restablecimiento inválido o expirado"
            )
        
        # Buscar al usuario por correo
        user = crud_user.get_by_email(db, email=email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Actualizar la contraseña
        hashed_password = get_password_hash(reset_data.new_password)
        user.hashed_password = hashed_password
        user.updated_at = datetime.utcnow()
        
        # Invalidar todos los tokens existentes del usuario
        db.query(AuthToken).filter(AuthToken.user_id == user.id).update(
            {AuthToken.revoked: True, AuthToken.revoked_at: datetime.utcnow()},
            synchronize_session=False
        )
        
        db.commit()
        
        # Opcional: Enviar notificación por correo
        try:
            await send_email(
                email_to=user.email,
                subject="Tu contraseña ha sido cambiada",
                template_name="password_changed.html",
                context={
                    "name": user.full_name or user.username,
                    "support_email": settings.SUPPORT_EMAIL,
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                }
            )
        except Exception as email_error:
            logger.error(f"Error al enviar notificación de cambio de contraseña: {str(email_error)}")
        
        return {"message": "Contraseña restablecida exitosamente. Por favor inicia sesión con tu nueva contraseña."}
        
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"Error al restablecer la contraseña: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al restablecer la contraseña"
        )

# =========================================================================
# Autenticación de dos factores (2FA)
# =========================================================================

@router.post("/2fa/setup", response_model=TwoFactorSetupResponse, summary="Configurar autenticación de dos factores")
async def setup_2fa(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Configurar la autenticación de dos factores para el usuario actual.
    
    Devuelve un código QR y un código secreto para configurar en una aplicación de autenticación.
    """
    try:
        # Verificar si ya tiene 2FA habilitado
        if current_user.two_factor_enabled:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "La autenticación de dos factores ya está habilitada"}
            )
        
        # Generar secreto y códigos de respaldo
        result = await AuthService.setup_2fa(current_user, db)
        
        return result
        
    except Exception as e:
        logger.error(f"Error al configurar 2FA: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al configurar la autenticación de dos factores"
        )

@router.post("/2fa/verify", response_model=TwoFactorBackupCodes, summary="Verificar código 2FA")
async def verify_2fa_setup(
    verify_data: TwoFactorVerify,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verificar el código de autenticación de dos factores durante la configuración.
    
    Devuelve los códigos de respaldo que el usuario debe guardar.
    """
    try:
        if current_user.two_factor_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La autenticación de dos factores ya está habilitada"
            )
        
        # Verificar el código
        backup_codes = await AuthService.verify_2fa_setup(
            user=current_user,
            code=verify_data.code,
            db=db
        )
        
        return {"backup_codes": backup_codes}
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al verificar 2FA: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al verificar el código de autenticación de dos factores"
        )

@router.post("/2fa/disable", response_model=Message, summary="Deshabilitar autenticación de dos factores")
async def disable_2fa(
    verify_data: TwoFactorVerify,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deshabilitar la autenticación de dos factores para el usuario actual.
    
    Requiere un código de autenticación o un código de respaldo válido.
    """
    try:
        if not current_user.two_factor_enabled:
            return {"message": "La autenticación de dos factores no está habilitada"}
        
        # Verificar el código
        success = await AuthService.disable_2fa(
            user=current_user,
            code=verify_data.code,
            db=db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código de verificación inválido"
            )
        
        return {"message": "Autenticación de dos factores deshabilitada exitosamente"}
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al deshabilitar 2FA: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al deshabilitar la autenticación de dos factores"
        )

# =========================================================================
# Gestión de sesiones
# =========================================================================

@router.get("/sessions", response_model=List[SessionInfo], summary="Obtener sesiones activas")
async def get_sessions(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Obtener las sesiones activas del usuario actual.
    """
    try:
        sessions = await AuthService.get_user_sessions(
            user_id=current_user.id,
            db=db,
            skip=skip,
            limit=limit
        )
        
        # Obtener el token actual para marcarlo
        current_token = getattr(request.state, 'auth_token', None)
        
        # Convertir a Pydantic models y marcar la sesión actual
        result = []
        for session in sessions:
            session_info = SessionInfo.from_orm(session)
            session_info.is_current = (session.token == current_token)
            result.append(session_info)
        
        return result
        
    except Exception as e:
        logger.error(f"Error al obtener sesiones: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener las sesiones"
        )

@router.post("/sessions/{session_id}/revoke", response_model=Message, summary="Revocar sesión")
async def revoke_session(
    session_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revocar una sesión específica del usuario actual.
    """
    try:
        success = await AuthService.revoke_session(
            user_id=current_user.id,
            session_id=session_id,
            db=db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión no encontrada"
            )
        
        return {"message": "Sesión revocada exitosamente"}
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al revocar sesión: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al revocar la sesión"
        )

@router.post("/sessions/revoke-all", response_model=Message, summary="Revocar todas las sesiones")
async def revoke_all_sessions(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revocar todas las sesiones del usuario actual, excepto la actual.
    """
    try:
        current_token = getattr(request.state, 'auth_token', None)
        
        count = await AuthService.revoke_all_sessions(
            user_id=current_user.id,
            current_token=current_token,
            db=db
        )
        
        return {"message": f"{count} sesiones revocadas exitosamente"}
        
    except Exception as e:
        logger.error(f"Error al revocar sesiones: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al revocar las sesiones"
        )

# =========================================================================
# Endpoints de administración
# =========================================================================

@router.post("/users/", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo usuario (solo administradores).
    """
    # Verificar permisos
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para realizar esta acción"
        )
    
    try:
        # Verificar si el nombre de usuario ya está registrado
        existing_user = crud_user.get_by_username(db, username=user_in.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya está en uso"
            )
        
        # Verificar si el correo ya está registrado
        existing_email = crud_user.get_by_email(db, email=user_in.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está registrado"
            )
        
        # Crear el usuario
        user = await AuthService.create_user(
            user_in=user_in,
            db=db,
            created_by=current_user.id
        )
        
        return user
        
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"Error al crear usuario: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear el usuario"
        )
