from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.core.database import obtener_db
from app.models.auth import Usuario, Perfil
from app.services.security import SecurityService

# Creamos el enrutador modular
router = APIRouter(prefix="/auth", tags=["Autenticación"])

# 1. El Molde (Esquema) de lo que debe enviar el Frontend
class LoginRequest(BaseModel):
    email: str # Usamos str básico por ahora para facilitar las pruebas
    password: str

# 2. La Ruta de Login (POST)
@router.post("/login")
def login(datos_login: LoginRequest, db: Session = Depends(obtener_db)):
    # A. Buscar al usuario por su correo
    usuario = db.query(Usuario).filter(Usuario.email == datos_login.email).first()
    
    # B. Si el usuario no existe, lanzamos un error genérico (por seguridad)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos"
        )
    
    # C. Verificar si el usuario está inactivo o suspendido
    if usuario.estado != "ACTIVO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"El usuario se encuentra {usuario.estado}. Contacte al administrador."
        )

    # D. Validar la contraseña usando nuestro servicio de Bcrypt
    password_valida = SecurityService.verificar_password(
        datos_login.password, 
        usuario.password_hash
    )
    
    if not password_valida:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos"
        )

    # E. Si todo está perfecto, extraemos los datos del perfil para Angular
    # Gracias a las relaciones de SQLAlchemy, podemos acceder a 'perfil' y 'rol' directamente
    return {
        "status": "success",
        "mensaje": "¡Inicio de sesión exitoso! 🎉",
        "usuario": {
            "id": usuario.id,
            "email": usuario.email,
            "nombre_completo": f"{usuario.perfil.nombre} {usuario.perfil.apellido}",
            "rol": usuario.rol.nombre,
            "cargo": usuario.perfil.cargo
        }
    }