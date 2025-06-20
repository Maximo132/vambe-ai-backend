# Gestión de Perfiles de Usuario

Este documento describe los endpoints disponibles para la gestión de perfiles de usuario en la API de Vambe.ai.

## Tabla de Contenidos

- [Obtener Perfil](#obtener-perfil)
- [Actualizar Perfil](#actualizar-perfil)
- [Cambiar Contraseña](#cambiar-contraseña)
- [Subir Avatar](#subir-avatar)
- [Obtener Configuración de Notificaciones](#obtener-configuración-de-notificaciones)
- [Actualizar Configuración de Notificaciones](#actualizar-configuración-de-notificaciones)
- [Eliminar Avatar](#eliminar-avatar)
- [Eliminar Cuenta](#eliminar-cuenta)

## Autenticación

Todos los endpoints requieren autenticación mediante un token JWT en el encabezado `Authorization`:

```
Authorization: Bearer <token>
```

## Endpoints

### Obtener Perfil

Obtiene la información del perfil del usuario autenticado.

- **URL**: `/api/v1/profile/me`
- **Método**: `GET`
- **Respuesta Exitosa**:
  - **Código**: `200 OK`
  - **Ejemplo de Respuesta**:
    ```json
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "usuario_ejemplo",
      "email": "usuario@ejemplo.com",
      "full_name": "Usuario de Ejemplo",
      "bio": "Descripción del perfil",
      "phone": "+1234567890",
      "avatar_url": "https://storage.example.com/avatars/550e8400-e29b-41d4-a716-446655440000.png",
      "is_active": true,
      "is_superuser": false,
      "created_at": "2023-01-01T00:00:00",
      "updated_at": "2023-01-01T00:00:00"
    }
    ```

### Actualizar Perfil

Actualiza la información del perfil del usuario autenticado.

- **URL**: `/api/v1/profile/me`
- **Método**: `PUT`
- **Cuerpo de la Solicitud**:
  ```json
  {
    "full_name": "Nuevo Nombre",
    "bio": "Nueva biografía",
    "phone": "+1234567890"
  }
  ```
- **Respuesta Exitosa**:
  - **Código**: `200 OK`
  - **Ejemplo de Respuesta**:
    ```json
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "usuario_ejemplo",
      "email": "usuario@ejemplo.com",
      "full_name": "Nuevo Nombre",
      "bio": "Nueva biografía",
      "phone": "+1234567890",
      "avatar_url": "https://storage.example.com/avatars/550e8400-e29b-41d4-a716-446655440000.png",
      "is_active": true,
      "is_superuser": false,
      "created_at": "2023-01-01T00:00:00",
      "updated_at": "2023-01-02T12:00:00"
    }
    ```

### Cambiar Contraseña

Cambia la contraseña del usuario autenticado.

- **URL**: `/api/v1/profile/me/change-password`
- **Método**: `POST`
- **Cuerpo de la Solicitud**:
  ```json
  {
    "current_password": "contraseña_actual",
    "new_password": "nueva_contraseña",
    "confirm_password": "nueva_contraseña"
  }
  ```
- **Respuesta Exitosa**:
  - **Código**: `200 OK`
  - **Ejemplo de Respuesta**:
    ```json
    {
      "message": "Contraseña actualizada correctamente"
    }
    ```

### Subir Avatar

Sube o actualiza el avatar del usuario.

- **URL**: `/api/v1/profile/me/avatar`
- **Método**: `POST`
- **Content-Type**: `multipart/form-data`
- **Parámetros de la Solicitud**:
  - `file`: Archivo de imagen (JPEG, PNG, GIF)
- **Respuesta Exitosa**:
  - **Código**: `200 OK`
  - **Ejemplo de Respuesta**:
    ```json
    {
      "avatar_url": "https://storage.example.com/avatars/550e8400-e29b-41d4-a716-446655440000.png"
    }
    ```

### Obtener Configuración de Notificaciones

Obtiene la configuración de notificaciones del usuario.

- **URL**: `/api/v1/profile/me/notifications`
- **Método**: `GET`
- **Respuesta Exitosa**:
  - **Código**: `200 OK`
  - **Ejemplo de Respuesta**:
    ```json
    {
      "email_notifications": true,
      "push_notifications": true,
      "message_notifications": true,
      "mention_notifications": true,
      "newsletter": false
    }
    ```

### Actualizar Configuración de Notificaciones

Actualiza la configuración de notificaciones del usuario.

- **URL**: `/api/v1/profile/me/notifications`
- **Método**: `PUT`
- **Cuerpo de la Solicitud**:
  ```json
  {
    "email_notifications": true,
    "push_notifications": false,
    "message_notifications": true,
    "mention_notifications": false,
    "newsletter": true
  }
  ```
- **Respuesta Exitosa**:
  - **Código**: `200 OK`
  - **Ejemplo de Respuesta**:
    ```json
    {
      "email_notifications": true,
      "push_notifications": false,
      "message_notifications": true,
      "mention_notifications": false,
      "newsletter": true
    }
    ```

### Eliminar Avatar

Elimina el avatar del usuario.

- **URL**: `/api/v1/profile/me/avatar`
- **Método**: `DELETE`
- **Respuesta Exitosa**:
  - **Código**: `200 OK`
  - **Ejemplo de Respuesta**:
    ```json
    {
      "message": "Avatar eliminado correctamente"
    }
    ```

### Eliminar Cuenta

Elimina la cuenta del usuario autenticado.

- **URL**: `/api/v1/profile/me`
- **Método**: `DELETE`
- **Cuerpo de la Solicitud (opcional)**:
  ```json
  {
    "password": "contraseña_actual"
  }
  ```
- **Respuesta Exitosa**:
  - **Código**: `200 OK`
  - **Ejemplo de Respuesta**:
    ```json
    {
      "message": "Cuenta eliminada correctamente"
    }
    ```

## Manejo de Errores

La API devuelve códigos de estado HTTP estándar para indicar el resultado de las operaciones. A continuación, se muestran algunos códigos de error comunes:

- `400 Bad Request`: La solicitud es incorrecta o falta información requerida.
- `401 Unauthorized`: No se proporcionó un token de autenticación o es inválido.
- `403 Forbidden`: El usuario no tiene permisos para realizar la acción.
- `404 Not Found`: El recurso solicitado no existe.
- `422 Unprocessable Entity`: Error de validación en los datos de entrada.
- `500 Internal Server Error`: Error interno del servidor.

Los mensajes de error incluyen un campo `detail` con una descripción del problema.
