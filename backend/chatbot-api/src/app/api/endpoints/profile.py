"""
Endpoints para la gestión de perfiles de usuario.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import logging

from app.db.session import get_db
from app.models.user import User
from app.schemas.profile import (
    ProfileResponse, ProfileUpdate, PasswordChange, 
    AvatarResponse, NotificationSettings
)
from app.services.profile_service import ProfileService
from app.api.deps import get_current_active_user

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/me", response_model=ProfileResponse, summary="Obtener perfil del usuario actual")
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene el perfil del usuario autenticado.
    """
    try:
        profile = ProfileService.get_user_profile(db, current_user.id)
        return profile
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error al obtener el perfil: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener el perfil"
        )

@router.put("/me", response_model=ProfileResponse, summary="Actualizar perfil del usuario actual")
async def update_my_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza el perfil del usuario autenticado.
    """
    try:
        updated_profile = ProfileService.update_profile(
            db=db,
            user_id=current_user.id,
            profile_data=profile_data
        )
        return updated_profile
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error al actualizar el perfil: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar el perfil"
        )

@router.post("/me/change-password", status_code=status.HTTP_200_OK, summary="Cambiar contraseña")
async def change_my_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cambia la contraseña del usuario autenticado.
    """
    try:
        result = ProfileService.change_password(
            db=db,
            user_id=current_user.id,
            password_data=password_data
        )
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error al cambiar la contraseña: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cambiar la contraseña"
        )

@router.post(
    "/me/avatar", 
    response_model=AvatarResponse, 
    status_code=status.HTTP_200_OK,
    summary="Subir avatar del usuario"
)
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Sube un archivo de avatar para el usuario autenticado.
    
    Formatos soportados: JPEG, PNG, GIF (máx. 5MB)
    """
    try:
        result = await ProfileService.upload_avatar(
            db=db,
            user_id=current_user.id,
            file=file
        )
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error al subir el avatar: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al subir el archivo"
        )

@router.get(
    "/me/notifications", 
    response_model=NotificationSettings, 
    summary="Obtener configuración de notificaciones"
)
async def get_notification_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene la configuración de notificaciones del usuario autenticado.
    """
    try:
        # Si no hay configuración, devolver valores por defecto
        if not hasattr(current_user, 'notification_settings') or not current_user.notification_settings:
            return NotificationSettings()
        return current_user.notification_settings
    except Exception as e:
        logger.error(f"Error al obtener la configuración de notificaciones: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener la configuración de notificaciones"
        )

@router.put(
    "/me/notifications", 
    response_model=Dict[str, Any], 
    summary="Actualizar configuración de notificaciones"
)
async def update_notification_settings(
    settings: NotificationSettings,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza la configuración de notificaciones del usuario autenticado.
    """
    try:
        result = ProfileService.update_notification_settings(
            db=db,
            user_id=current_user.id,
            settings=settings
        )
        return result
    except Exception as e:
        logger.error(f"Error al actualizar la configuración de notificaciones: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar la configuración de notificaciones"
        )
