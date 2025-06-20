"""
Utilidades para el manejo de almacenamiento de archivos.
Soporta almacenamiento local y en la nube (S3, MinIO, etc.)
"""
import os
import logging
from typing import BinaryIO, Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
import uuid

from fastapi import UploadFile, HTTPException, status
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    """Servicio para manejar el almacenamiento de archivos."""
    
    def __init__(self):
        self.client = None
        self.bucket_name = settings.AWS_S3_BUCKET_NAME
        self.region = settings.AWS_REGION
        self.use_s3 = settings.STORAGE_PROVIDER.lower() == 's3'
        self.base_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com"
        
        if self.use_s3:
            self._initialize_s3_client()
    
    def _initialize_s3_client(self):
        """Inicializa el cliente de S3."""
        try:
            self.client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=self.region
            )
            # Verificar que el bucket existe y es accesible
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                logger.error(f"El bucket {self.bucket_name} no existe")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"El bucket de almacenamiento no existe: {self.bucket_name}"
                )
            elif error_code == 403:
                logger.error(f"Acceso denegado al bucket {self.bucket_name}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Acceso denegado al bucket de almacenamiento: {self.bucket_name}"
                )
            else:
                logger.error(f"Error al inicializar el cliente de S3: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error al inicializar el servicio de almacenamiento"
                )
    
    async def upload_file(
        self, 
        file: UploadFile, 
        file_path: str, 
        content_type: Optional[str] = None,
        public: bool = False
    ) -> str:
        """
        Sube un archivo al almacenamiento.
        
        Args:
            file: Archivo a subir
            file_path: Ruta donde se guardará el archivo (incluyendo el nombre del archivo)
            content_type: Tipo MIME del archivo
            public: Si es True, el archivo será accesible públicamente
            
        Returns:
            str: URL pública del archivo subido
        """
        try:
            content_type = content_type or file.content_type or 'application/octet-stream'
            
            if self.use_s3 and self.client:
                # Subir a S3
                extra_args = {'ContentType': content_type}
                if public:
                    extra_args['ACL'] = 'public-read'
                
                self.client.upload_fileobj(
                    file.file,
                    self.bucket_name,
                    file_path,
                    ExtraArgs=extra_args
                )
                
                # Generar URL firmada si no es público
                if public:
                    file_url = f"{self.base_url}/{file_path}"
                else:
                    file_url = self.client.generate_presigned_url(
                        'get_object',
                        Params={
                            'Bucket': self.bucket_name,
                            'Key': file_path
                        },
                        ExpiresIn=3600  # URL válida por 1 hora
                    )
            else:
                # Almacenamiento local
                upload_dir = Path(settings.UPLOAD_DIR) / os.path.dirname(file_path)
                upload_dir.mkdir(parents=True, exist_ok=True)
                
                file_path_full = upload_dir / os.path.basename(file_path)
                
                # Guardar el archivo
                with open(file_path_full, 'wb') as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                file_url = f"/uploads/{file_path}"
            
            return file_url
            
        except Exception as e:
            logger.error(f"Error al subir el archivo: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al subir el archivo: {str(e)}"
            )
    
    def delete_file(self, file_path: str) -> bool:
        """
        Elimina un archivo del almacenamiento.
        
        Args:
            file_path: Ruta del archivo a eliminar
            
        Returns:
            bool: True si se eliminó correctamente, False en caso contrario
        """
        try:
            if self.use_s3 and self.client:
                # Eliminar de S3
                self.client.delete_object(Bucket=self.bucket_name, Key=file_path)
            else:
                # Eliminar del almacenamiento local
                file_full_path = Path(settings.UPLOAD_DIR) / file_path
                if file_full_path.exists():
                    file_full_path.unlink()
            
            return True
            
        except Exception as e:
            logger.error(f"Error al eliminar el archivo {file_path}: {str(e)}")
            return False

# Instancia global del servicio de almacenamiento
storage_service = StorageService()

async def upload_file_to_storage(
    file: BinaryIO, 
    filename: str, 
    content_type: str = 'application/octet-stream',
    public: bool = False
) -> str:
    """
    Función de conveniencia para subir un archivo al almacenamiento.
    
    Args:
        file: Archivo a subir (objeto file-like)
        filename: Nombre del archivo (puede incluir carpetas)
        content_type: Tipo MIME del archivo
        public: Si es True, el archivo será accesible públicamente
        
    Returns:
        str: URL del archivo subido
    """
    try:
        # Crear un objeto UploadFile temporal
        upload_file = UploadFile(
            file=file,
            filename=filename,
            content_type=content_type
        )
        
        # Subir el archivo
        file_url = await storage_service.upload_file(
            file=upload_file,
            file_path=filename,
            content_type=content_type,
            public=public
        )
        
        return file_url
        
    except Exception as e:
        logger.error(f"Error en upload_file_to_storage: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar el archivo: {str(e)}"
        )
