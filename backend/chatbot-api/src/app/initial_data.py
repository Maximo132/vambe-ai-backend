from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash

def init_db(db: Session) -> None:
    """Inicializa la base de datos con datos por defecto"""
    # Crear usuario administrador si no existe
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin_user = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Administrator",
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        print("Usuario administrador creado:")
        print(f"Usuario: admin")
        print(f"Contraseña: admin123")
        print("¡Por favor, cambia la contraseña después del primer inicio de sesión!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()
