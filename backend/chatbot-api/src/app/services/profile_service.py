"""
Servicio para la gestión de perfiles de usuario.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import and_
import shutil
import os
import uuid

from app.core.config import settings
from app.models.user import User
from app.schemas.profile import ProfileUpdate, PasswordChange, NotificationSettings
from app.core.security import get_password_hash, verify_password
from app.utils.storage import upload_file_to_storage

logger = logging.getLogger(__name__)

class ProfileService:
    """Servicio para gestionar perfiles de usuario."""
    
    @staticmethod
    def get_user_profile(db: Session, user_id: str) -> Dict[str, Any]:
        """Obtiene el perfil de un usuario por su ID."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        return user
    
    @staticmethod
    def update_profile(
        db: Session, 
        user_id: str, 
        profile_data: ProfileUpdate
    ) -> Dict[str, Any]:
        """Actualiza el perfil de un usuario."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Actualizar campos básicos
        update_data = profile_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == 'email' and value != user.email:
                # Si el correo cambia, marcarlo como no verificado
                setattr(user, 'email_verified', False)
                setattr(user, field, value)
            elif hasattr(user, field):
                setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    def change_password(
        db: Session, 
        user_id: str, 
        password_data: PasswordChange
    ) -> Dict[str, str]:
        """Cambia la contraseña de un usuario."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Verificar la contraseña actual
        if not verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña actual es incorrecta"
            )
        
        # Actualizar la contraseña
        user.hashed_password = get_password_hash(password_data.new_password)
        user.updated_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Contraseña actualizada correctamente"}
    
    @staticmethod
    async def upload_avatar(
        db: Session, 
        user_id: str, 
        file: UploadFile
    ) -> Dict[str, str]:
        """Sube un archivo de avatar para el usuario."""
        # Validar tipo de archivo
        allowed_content_types = ["image/jpeg", "image/png", "image/gif"]
        if file.content_type not in allowed_content_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de archivo no soportado. Use JPEG, PNG o GIF"
            )
        
        # Validar tamaño del archivo (máx 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        file.file.seek(0, 2)  # Ir al final del archivo para obtener el tamaño
        file_size = file.file.tell()
        file.file.seek(0)  # Volver al inicio del archivo
        
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El archivo es demasiado grande. Tamaño máximo permitido: 5MB"
            )
        
        # Generar nombre único para el archivo
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"avatars/{user_id}/{uuid.uuid4()}{file_extension}"
        
        # Subir el archivo al almacenamiento
        try:
            file_url = await upload_file_to_storage(
                file=file.file,
                filename=filename,
                content_type=file.content_type
            )
            
            # Actualizar el perfil del usuario con la nueva URL del avatar
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.avatar_url = file_url
                user.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(user)
            
            return {
                "avatar_url": file_url,
                "message": "Avatar actualizado correctamente"
            }
            
        except Exception as e:
            logger.error(f"Error al subir el avatar: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al procesar el archivo"
            )
    
    @staticmethod
    def update_notification_settings(
        db: Session,
        user_id: str,
        settings: NotificationSettings
    ) -> Dict[str, Any]:
        """Actualiza la configuración de notificaciones del usuario."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Convertir el modelo Pydantic a diccionario y actualizar
        settings_dict = settings.dict()
        if not hasattr(user, 'notification_settings'):
            user.notification_settings = {}
        
        user.notification_settings.update(settings_dict)
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        return {
            "notification_settings": user.notification_settings,
            "message": "Configuración de notificaciones actualizada"
        }
