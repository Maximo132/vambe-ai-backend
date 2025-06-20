from enum import Enum as PyEnum

class MessageRole(str, PyEnum):
    """Roles de los mensajes en el chat."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    FUNCTION = "function"

class UserRole(str, PyEnum):
    """Roles de usuario en el sistema"""
    SUPERADMIN = "superadmin"  # Acceso total al sistema
    ADMIN = "admin"           # Administradores de la plataforma
    AGENT = "agent"           # Agentes de soporte
    CUSTOMER = "customer"      # Clientes finales
    GUEST = "guest"           # Usuarios invitados (acceso limitado)
    
    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_
