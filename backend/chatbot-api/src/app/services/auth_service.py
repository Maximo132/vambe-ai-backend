"""
Servicio de autenticación para manejar el registro, inicio de sesión, verificación de correo,
restablecimiento de contraseña y gestión de sesiones de usuario.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

from fastapi import HTTPException, status, Depends, Request, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import EmailStr, ValidationError
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    generate_password_reset_token,
    verify_password_reset_token,
    generate_email_verification_token,
    verify_email_verification_token
)
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.auth_token import AuthToken
from app.models.login_history import LoginHistory
from app.schemas.token import Token, TokenPayload
from app.schemas.user import UserCreate, UserResponse
from app.utils.email_utils import send_email
from app.utils.security_utils import get_client_ip, get_user_agent

# Configuración de logging
logger = logging.getLogger(__name__)

# Contexto para el hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema OAuth2 para la autenticación con token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

class AuthService:
    """
    Servicio para manejar la autenticación de usuarios.
    """
    
    @classmethod
    def get_current_user(
        cls,
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
    ) -> User:
        """
        Obtiene el usuario actual a partir del token de acceso.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo validar las credenciales",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            # Verificar el token
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Extraer el ID de usuario del token
            token_data = TokenPayload(**payload)
            user_id = token_data.sub
            
            if user_id is None:
                raise credentials_exception
                
            # Verificar si el token está revocado
            auth_token = AuthToken.get_active_token(token, "access")
            if not auth_token or auth_token.user_id != user_id:
                raise credentials_exception
                
        except (JWTError, ValidationError) as e:
            logger.error(f"Error al decodificar el token: {str(e)}")
            raise credentials_exception
            
        # Obtener el usuario de la base de datos
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise credentials_exception
            
        # Verificar si el usuario está activo
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )
            
        # Verificar si la cuenta está bloqueada
        if user.is_locked():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cuenta bloqueada temporalmente"
            )
            
        return user
    
    @classmethod
    def get_current_active_user(
        cls,
        current_user: User = Depends(get_current_user)
    ) -> User:
        """
        Obtiene el usuario actual activo.
        """
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario inactivo"
            )
        return current_user
    
    @classmethod
    def get_current_active_superuser(
        cls,
        current_user: User = Depends(get_current_user)
    ) -> User:
        """
        Obtiene el usuario administrador actual.
        """
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario no tiene suficientes privilegios"
            )
        return current_user
        
    @classmethod
    def login(
        cls,
        db: Session,
        form_data: OAuth2PasswordRequestForm,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """
        Maneja el inicio de sesión de un usuario y devuelve los tokens de acceso.
        """
        # Autenticar al usuario
        user = cls.authenticate_user(
            db=db,
            username=form_data.username,
            password=form_data.password,
            request=request
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nombre de usuario o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verificar si el usuario ya tiene una sesión activa en este dispositivo
        device_id = request.headers.get("X-Device-Id") if request else None
        
        # Crear tokens de acceso
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "is_verified": user.is_verified,
                "scopes": form_data.scopes
            },
            expires_delta=access_token_expires
        )
        
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)},
            expires_delta=refresh_token_expires
        )
        
        # Guardar el token en la base de datos
        auth_token = AuthToken(
            user_id=user.id,
            token=access_token,
            refresh_token=refresh_token,
            scopes=form_data.scopes or [],
            device_id=device_id,
            device_name=request.headers.get("X-Device-Name") if request else None,
            device_type=request.headers.get("X-Device-Type") if request else None,
            ip_address=get_client_ip(request) if request else None,
            user_agent=get_user_agent(request) if request else None,
            expires_at=datetime.utcnow() + refresh_token_expires
        )
        
        db.add(auth_token)
        
        # Actualizar last_seen y last_ip_address
        user.last_seen = datetime.utcnow()
        if request:
            user.last_ip_address = get_client_ip(request)
        
        db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": UserResponse.from_orm(user).dict()
        }
    
    @classmethod
    def authenticate_user(
        cls, 
        db: Session, 
        username: str, 
        password: str,
        request: Optional[Request] = None
    ) -> Optional[User]:
        """
        Autentica a un usuario con nombre de usuario/correo y contraseña.
        """
        try:
            # Buscar usuario por nombre de usuario o correo
            user = db.query(User).filter(
                (User.email == username) | (User.username == username)
            ).first()
            
            if not user:
                logger.warning(f"Intento de inicio de sesión fallido: Usuario no encontrado - {username}")
                return None
                
            # Verificar si la cuenta está bloqueada
            if user.is_locked():
                logger.warning(f"Intento de inicio de sesión fallido: Cuenta bloqueada - {user.email}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="La cuenta está bloqueada temporalmente. Por favor, intente más tarde.",
                )
            
            # Verificar la contraseña
            if not verify_password(password, user.hashed_password):
                # Registrar intento fallido
                user.record_failed_login()
                db.commit()
                
                # Bloquear cuenta después de varios intentos fallidos
                if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                    user.lock_account()
                    db.commit()
                    logger.warning(f"Cuenta bloqueada por múltiples intentos fallidos - {user.email}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Demasiados intentos fallidos. La cuenta ha sido bloqueada temporalmente.",
                    )
                
                logger.warning(f"Intento de inicio de sesión fallido: Contraseña incorrecta - {user.email}")
                return None
            
            # Verificar si la cuenta está activa
            if not user.is_active:
                logger.warning(f"Intento de inicio de sesión fallido: Cuenta desactivada - {user.email}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="La cuenta está desactivada. Contacte al administrador.",
                )
            
            # Verificar si el correo está verificado (si es requerido)
            if settings.EMAILS_ENABLED and settings.EMAIL_VERIFICATION_REQUIRED and not user.email_verified:
                logger.warning(f"Intento de inicio de sesión fallido: Correo no verificado - {user.email}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Por favor, verifique su dirección de correo electrónico antes de iniciar sesión.",
                )
            
            # Restablecer contador de intentos fallidos
            if user.failed_login_attempts > 0:
                user.failed_login_attempts = 0
                db.commit()
            
            # Registrar inicio de sesión exitoso
            user.record_login()
            
            # Registrar en el historial de inicio de sesión
            if request:
                ip_address = get_client_ip(request)
                user_agent = get_user_agent(request)
                
                LoginHistory.create_login_attempt(
                    user_id=user.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status="success",
                    device_id=request.headers.get("X-Device-Id"),
                    device_name=request.headers.get("X-Device-Name"),
                    device_type=request.headers.get("X-Device-Type"),
                    is_2fa_used=False,
                    is_remember_me=False
                )
            
            db.commit()
            logger.info(f"Inicio de sesión exitoso - {user.email}")
            return user
            
        except Exception as e:
            logger.error(f"Error en la autenticación: {str(e)}", exc_info=True)
            raise
            
    @classmethod
    def register_user(
        cls,
        db: Session,
        user_in: UserCreate,
        request: Optional[Request] = None
    ) -> User:
        """
        Registra un nuevo usuario en el sistema.
        """
        # Verificar si el correo ya está registrado
        if db.query(User).filter(User.email == user_in.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está registrado"
            )
        
        # Verificar si el nombre de usuario ya está en uso
        if db.query(User).filter(User.username == user_in.username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya está en uso"
            )
        
        try:
            # Crear el usuario
            hashed_password = get_password_hash(user_in.password)
            
            # Configurar valores por defecto
            user_data = user_in.dict(exclude={"password"})
            user_data.update(
                hashed_password=hashed_password,
                is_active=True,
                is_verified=not settings.EMAIL_VERIFICATION_REQUIRED,
                role=UserRole.CUSTOMER,  # Rol por defecto
            )
            
            # Crear el usuario en la base de datos
            db_user = User(**user_data)
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            # Enviar correo de verificación si es necesario
            if settings.EMAILS_ENABLED and settings.EMAIL_VERIFICATION_REQUIRED:
                cls.send_verification_email(db=db, email=db_user.email, request=request)
            
            # Registrar en el historial de inicio de sesión
            if request:
                LoginHistory.create_login_attempt(
                    user_id=db_user.id,
                    ip_address=get_client_ip(request),
                    user_agent=get_user_agent(request),
                    status="registered",
                    device_id=request.headers.get("X-Device-Id"),
                    device_name=request.headers.get("X-Device-Name"),
                    device_type=request.headers.get("X-Device-Type"),
                )
            
            logger.info(f"Nuevo usuario registrado: {db_user.email}")
            return db_user
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error al registrar usuario: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al registrar el usuario"
            )
    
    @classmethod
    def send_verification_email(
        cls,
        db: Session,
        email: str,
        request: Optional[Request] = None
    ) -> None:
        """
        Envía un correo electrónico de verificación al usuario.
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        if user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya ha sido verificado"
            )
        
        # Generar token de verificación
        token = generate_email_verification_token(email=email)
        
        # Guardar el token en el usuario
        user.verification_token = token
        user.verification_token_expires = datetime.utcnow() + timedelta(hours=24)  # Token válido por 24 horas
        db.commit()
        
        # Enviar correo electrónico
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        
        # En un entorno real, aquí se enviaría el correo electrónico
        if settings.EMAILS_ENABLED:
            send_email(
                email_to=user.email,
                subject="Verifica tu dirección de correo electrónico",
                template_name="verify_email.html",
                context={
                    "name": user.first_name or user.username,
                    "verification_url": verification_url,
                    "expiration_hours": 24
                }
            )
            
            logger.info(f"Correo de verificación enviado a {user.email}")
        else:
            # En entorno de desarrollo, imprimir el enlace en los logs
            logger.info(f"Enlace de verificación para {user.email}: {verification_url}")
    
    @classmethod
    def verify_email(
        cls,
        db: Session,
        token: str,
        request: Optional[Request] = None
    ) -> Dict[str, str]:
        """
        Verifica la dirección de correo electrónico de un usuario usando un token.
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
            user = db.query(User).filter(User.email == email).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado"
                )
            
            # Verificar si el correo ya está verificado
            if user.email_verified:
                return {"message": "El correo electrónico ya ha sido verificado"}
            
            # Verificar si el token coincide
            if user.verification_token != token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token de verificación no válido"
                )
            
            # Verificar si el token ha expirado
            if user.verification_token_expires < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El token de verificación ha expirado"
                )
            
            # Marcar el correo como verificado
            user.email_verified = True
            user.verification_token = None
            user.verification_token_expires = None
            user.is_active = True  # Activar la cuenta si estaba inactiva
            
            db.commit()
            
            # Registrar el evento
            logger.info(f"Correo electrónico verificado para el usuario: {user.email}")
            
            return {"message": "Correo electrónico verificado exitosamente"}
            
        except JWTError as e:
            logger.error(f"Error al verificar el token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de verificación inválido o expirado"
            )
    
    @classmethod
    def forgot_password(
        cls,
        db: Session,
        email: str,
        request: Optional[Request] = None
    ) -> Dict[str, str]:
        """
        Inicia el proceso de restablecimiento de contraseña enviando un correo con un enlace seguro.
        """
        user = db.query(User).filter(User.email == email).first()
        
        # Por seguridad, no revelamos si el correo existe o no
        if not user:
            logger.warning(f"Intento de restablecer contraseña para correo no registrado: {email}")
            return {"message": "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña"}
        
        # Generar token de restablecimiento
        reset_token = generate_password_reset_token(email=email)
        
        # Guardar el token en el usuario
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)  # Token válido por 1 hora
        db.commit()
        
        # Enviar correo electrónico con el enlace de restablecimiento
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        if settings.EMAILS_ENABLED:
            send_email(
                email_to=user.email,
                subject="Restablece tu contraseña",
                template_name="reset_password.html",
                context={
                    "name": user.first_name or user.username,
                    "reset_url": reset_url,
                    "expiration_minutes": 60
                }
            )
            
            logger.info(f"Correo de restablecimiento de contraseña enviado a {user.email}")
        else:
            # En entorno de desarrollo, imprimir el enlace en los logs
            logger.info(f"Enlace de restablecimiento para {user.email}: {reset_url}")
        
        return {"message": "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña"}
    
    @classmethod
    def reset_password(
        cls,
        db: Session,
        token: str,
        new_password: str,
        request: Optional[Request] = None
    ) -> Dict[str, str]:
        """
        Restablece la contraseña de un usuario usando un token de restablecimiento.
        """
        try:
            # Verificar el token
            email = verify_password_reset_token(token)
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token de restablecimiento inválido o expirado"
                )
            
            # Buscar al usuario por correo
            user = db.query(User).filter(User.email == email).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado"
                )
            
            # Verificar si el token coincide
            if user.reset_token != token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token de restablecimiento no válido"
                )
            
            # Verificar si el token ha expirado
            if user.reset_token_expires < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El token de restablecimiento ha expirado"
                )
            
            # Actualizar la contraseña
            user.hashed_password = get_password_hash(new_password)
            
            # Invalidar el token
            user.reset_token = None
            user.reset_token_expires = None
            
            # Invalidar todas las sesiones activas del usuario (opcional, por seguridad)
            AuthToken.revoke_all_user_tokens(db, user_id=user.id)
            
            db.commit()
            
            # Registrar el evento
            logger.info(f"Contraseña restablecida para el usuario: {user.email}")
            
            return {"message": "Contraseña restablecida exitosamente"}
            
        except JWTError as e:
            logger.error(f"Error al verificar el token de restablecimiento: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de restablecimiento inválido o expirado"
            )
    
    @classmethod
    def setup_2fa(
        cls,
        db: Session,
        current_user: User,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """
        Configura la autenticación de dos factores para un usuario.
        Devuelve el secreto y un URI para configurar en una app de autenticación.
        """
        if current_user.two_factor_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La autenticación de dos factores ya está habilitada"
            )
        
        # Generar un secreto para 2FA
        secret = pyotp.random_base32()
        
        # Crear un URI para la aplicación de autenticación
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=current_user.email,
            issuer_name=settings.PROJECT_NAME
        )
        
        # Generar un código QR
        qr_code = qrcode.make(totp_uri)
        
        # Guardar el secreto temporalmente (sin habilitar 2FA aún)
        current_user.two_factor_secret = secret
        current_user.two_factor_enabled = False  # No habilitar hasta que se verifique
        
        db.commit()
        
        # En un entorno de producción, podrías devolver el URI y generar el QR en el frontend
        # Aquí lo hacemos en el backend para simplificar
        from io import BytesIO
        import base64
        
        buffered = BytesIO()
        qr_code.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "secret": secret,  # Solo para fines de depuración, no debería exponerse en producción
            "qr_code": f"data:image/png;base64,{qr_code_base64}",
            "manual_entry_code": secret,  # Para entrada manual en la app de autenticación
            "verification_required": True
        }
    
    @classmethod
    def verify_2fa(
        cls,
        db: Session,
        current_user: User,
        token: str,
        request: Optional[Request] = None
    ) -> Dict[str, str]:
        """
        Verifica el código 2FA proporcionado por el usuario y activa 2FA si es correcto.
        """
        if not current_user.two_factor_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Primero debe configurar la autenticación de dos factores"
            )
        
        # Verificar el código
        totp = pyotp.TOTP(current_user.two_factor_secret)
        if not totp.verify(token, valid_window=1):  # Permite un margen de 1 intervalo (30 segundos)
            # Registrar intento fallido
            if request:
                LoginHistory.create_login_attempt(
                    user_id=current_user.id,
                    ip_address=get_client_ip(request),
                    user_agent=get_user_agent(request),
                    status="2fa_failed",
                    device_id=request.headers.get("X-Device-Id"),
                    device_name=request.headers.get("X-Device-Name"),
                    device_type=request.headers.get("X-Device-Type"),
                )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código de verificación inválido"
            )
        
        # Si llegamos aquí, el código es correcto
        current_user.two_factor_enabled = True
        
        # Generar códigos de respaldo
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        current_user.two_factor_backup_codes = [
            get_password_hash(code) for code in backup_codes
        ]
        
        db.commit()
        
        # Registrar el evento
        logger.info(f"2FA habilitado para el usuario: {current_user.email}")
        
        return {
            "message": "Autenticación de dos factores habilitada exitosamente",
            "backup_codes": backup_codes  # Mostrar solo una vez al usuario
        }
    
    @classmethod
    def verify_2fa_code(
        cls,
        db: Session,
        user: User,
        token: str,
        request: Optional[Request] = None
    ) -> bool:
        """
        Verifica un código 2FA para un usuario durante el inicio de sesión.
        Devuelve True si el código es válido, False en caso contrario.
        """
        if not user.two_factor_enabled or not user.two_factor_secret:
            return False
        
        # Verificar si es un código de respaldo
        if user.two_factor_backup_codes:
            for i, hashed_code in enumerate(user.two_factor_backup_codes):
                if verify_password(token, hashed_code):
                    # Eliminar el código de respaldo usado
                    user.two_factor_backup_codes.pop(i)
                    db.commit()
                    logger.info(f"Código de respaldo usado para el usuario: {user.email}")
                    return True
        
        # Verificar el código TOTP
        totp = pyotp.TOTP(user.two_factor_secret)
        is_valid = totp.verify(token, valid_window=1)  # Permite un margen de 1 intervalo (30 segundos)
        
        if not is_valid and request:
            # Registrar intento fallido
            LoginHistory.create_login_attempt(
                user_id=user.id,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                status="2fa_failed",
                device_id=request.headers.get("X-Device-Id"),
                device_name=request.headers.get("X-Device-Name"),
                device_type=request.headers.get("X-Device-Type"),
            )
        
        return is_valid
    
    @classmethod
    def disable_2fa(
        cls,
        db: Session,
        current_user: User,
        password: str,
        request: Optional[Request] = None
    ) -> Dict[str, str]:
        """
        Desactiva la autenticación de dos factores para un usuario.
        """
        # Verificar la contraseña actual
        if not verify_password(password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contraseña incorrecta"
            )
        
        # Desactivar 2FA
        current_user.two_factor_enabled = False
        current_user.two_factor_secret = None
        current_user.two_factor_backup_codes = None
        
        # Invalidar todas las sesiones activas del usuario (opcional, por seguridad)
        AuthToken.revoke_all_user_tokens(db, user_id=current_user.id)
        
        db.commit()
        
        # Registrar el evento
        logger.info(f"2FA deshabilitado para el usuario: {current_user.email}")
        
        return {"message": "Autenticación de dos factores deshabilitada exitosamente"}
    
    @classmethod
    def get_user_sessions(
        cls,
        db: Session,
        current_user: User,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene las sesiones activas del usuario actual.
        """
        sessions = db.query(AuthToken).filter(
            AuthToken.user_id == current_user.id,
            AuthToken.revoked == False,
            AuthToken.expires_at > datetime.utcnow()
        ).order_by(AuthToken.created_at.desc()).offset(skip).limit(limit).all()
        
        return [
            {
                "id": str(session.id),
                "created_at": session.created_at,
                "last_used_at": session.last_used_at,
                "expires_at": session.expires_at,
                "device_name": session.device_name,
                "device_type": session.device_type,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
                "is_current": session.token == getattr(request.state, 'auth_token', None)
            }
            for session in sessions
        ]
    
    @classmethod
    def revoke_session(
        cls,
        db: Session,
        current_user: User,
        session_id: str,
        request: Optional[Request] = None
    ) -> Dict[str, str]:
        """
        Revoca una sesión específica del usuario actual.
        """
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de sesión inválido"
            )
        
        # Obtener la sesión
        session = db.query(AuthToken).filter(
            AuthToken.id == session_uuid,
            AuthToken.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión no encontrada o no tienes permisos para acceder a ella"
            )
        
        # No permitir revocar la sesión actual
        current_token = getattr(request.state, 'auth_token', None)
        if session.token == current_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes revocar tu sesión actual"
            )
        
        # Revocar la sesión
        session.revoked = True
        session.revoked_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Sesión {session_id} revocada para el usuario: {current_user.email}")
        
        return {"message": "Sesión revocada exitosamente"}
    
    @classmethod
    def revoke_all_sessions(
        cls,
        db: Session,
        current_user: User,
        current_token: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Revoca todas las sesiones del usuario actual excepto la actual.
        """
        # Revocar todas las sesiones excepto la actual
        result = db.query(AuthToken).filter(
            AuthToken.user_id == current_user.id,
            AuthToken.revoked == False,
            AuthToken.token != current_token
        ).update({
            AuthToken.revoked: True,
            AuthToken.revoked_at: datetime.utcnow()
        })
        
        db.commit()
        
        logger.info(f"Todas las sesiones revocadas para el usuario: {current_user.email} (excepto la actual)")
        
        return {"message": f"{result} sesiones revocadas exitosamente"}
    
    @classmethod
    def verify_device(
        cls,
        db: Session,
        current_user: User,
        device_token: str,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """
        Verifica un dispositivo para autenticación sin contraseña.
        """
        if not settings.DEVICE_AUTH_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La autenticación por dispositivo no está habilitada"
            )
        
        # Verificar si el token del dispositivo es válido
        device = db.query(Device).filter(
            Device.user_id == current_user.id,
            Device.token == device_token,
            Device.revoked == False,
            Device.expires_at > datetime.utcnow()
        ).first()
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de dispositivo inválido o expirado"
            )
        
        # Crear tokens de acceso
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = create_access_token(
            data={
                "sub": str(current_user.id),
                "email": current_user.email,
                "role": current_user.role,
                "is_verified": current_user.is_verified,
                "scopes": ["authenticated"]
            },
            expires_delta=access_token_expires
        )
        
        refresh_token = create_refresh_token(
            data={"sub": str(current_user.id)},
            expires_delta=refresh_token_expires
        )
        
        # Guardar el token en la base de datos
        auth_token = AuthToken(
            user_id=current_user.id,
            token=access_token,
            refresh_token=refresh_token,
            scopes=["authenticated"],
            device_id=device.device_id,
            device_name=device.device_name,
            device_type=device.device_type,
            ip_address=get_client_ip(request) if request else None,
            user_agent=get_user_agent(request) if request else None,
            expires_at=datetime.utcnow() + refresh_token_expires
        )
        
        db.add(auth_token)
        
        # Actualizar last_used en el dispositivo
        device.last_used_at = datetime.utcnow()
        
        # Actualizar last_seen y last_ip_address del usuario
        current_user.last_seen = datetime.utcnow()
        if request:
            current_user.last_ip_address = get_client_ip(request)
        
        db.commit()
        
        # Registrar el evento
        logger.info(f"Dispositivo verificado para el usuario: {current_user.email} - {device.device_name}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": UserResponse.from_orm(current_user).dict()
        }
    
    @classmethod
    def get_trusted_devices(
        cls,
        db: Session,
        current_user: User,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene los dispositivos de confianza del usuario actual.
        """
        if not settings.DEVICE_AUTH_ENABLED:
            return []
        
        devices = db.query(Device).filter(
            Device.user_id == current_user.id,
            Device.revoked == False,
            Device.expires_at > datetime.utcnow()
        ).order_by(Device.last_used_at.desc()).offset(skip).limit(limit).all()
        
        return [
            {
                "id": str(device.id),
                "device_id": device.device_id,
                "device_name": device.device_name,
                "device_type": device.device_type,
                "os": device.os,
                "browser": device.browser,
                "last_used_at": device.last_used_at,
                "created_at": device.created_at,
                "expires_at": device.expires_at,
                "is_current": device.device_id == getattr(request, 'headers', {}).get('X-Device-Id')
            }
            for device in devices
        ]
    
    @classmethod
    def revoke_trusted_device(
        cls,
        db: Session,
        current_user: User,
        device_id: str,
        request: Optional[Request] = None
    ) -> Dict[str, str]:
        """
        Revoca un dispositivo de confianza.
        """
        if not settings.DEVICE_AUTH_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La autenticación por dispositivo no está habilitada"
            )
        
        # Obtener el dispositivo
        device = db.query(Device).filter(
            Device.id == device_id,
            Device.user_id == current_user.id,
            Device.revoked == False
        ).first()
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispositivo no encontrado o ya revocado"
            )
        
        # Revocar el dispositivo
        device.revoked = True
        device.revoked_at = datetime.utcnow()
        
        # Invalidar todas las sesiones asociadas a este dispositivo
        db.query(AuthToken).filter(
            AuthToken.user_id == current_user.id,
            AuthToken.device_id == device.device_id,
            AuthToken.revoked == False
        ).update({
            AuthToken.revoked: True,
            AuthToken.revoked_at: datetime.utcnow()
        })
        
        db.commit()
        
        logger.info(f"Dispositivo revocado para el usuario: {current_user.email} - {device.device_name}")
        
        return {"message": "Dispositivo revocado exitosamente"}
