from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import obtener_db
from app.models.auth import Usuario, Perfil, Sesion  # <-- Importamos Sesion
from app.services.security import SecurityService
from datetime import datetime, timezone, timedelta
import secrets
import hashlib

router = APIRouter(prefix="/auth", tags=["Autenticación"])

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(datos_login: LoginRequest, db: Session = Depends(obtener_db)):
    # 1. Buscar al usuario por correo
    usuario = db.query(Usuario).filter(Usuario.email == datos_login.email).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos"
        )
    
    # 2. Verificar estado operativo
    if usuario.estado != "ACTIVO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"El usuario se encuentra {usuario.estado}. Contacte al administrador."
        )

    # 3. Validar contraseña con Bcrypt
    password_valida = SecurityService.verificar_password(
        datos_login.password, 
        usuario.password_hash
    )
    
    if not password_valida:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos"
        )

    # ============================================================================
    # GENERACIÓN DE SESIÓN PERSISTENTE (EL NUEVO MOTOR)
    # ============================================================================

    # A. Generar un Token aleatorio único y ultra seguro (64 caracteres hex)
    token_original = secrets.token_hex(32)
    
    # B. Crear el Hash SHA-256 para guardar de forma segura en Postgres
    token_hasheado = hashlib.sha256(token_original.encode('utf-8')).hexdigest()
    
    # C. Establecer expiración de la sesión (24 horas de vigencia)
    tiempo_expiracion = datetime.now(timezone.utc) + timedelta(hours=24)
    
    # D. Guardar la nueva sesión en la base de datos
    nueva_sesion = Sesion(
        usuario_id=usuario.id,
        token_sesion_hash=token_hasheado,
        valida=True,
        expira_en=tiempo_expiracion
    )
    db.add(nueva_sesion)
    db.commit()  # Confirmamos la inserción en Postgres 17

    # 4. Retorno triunfal con el Token en bandeja de plata para Angular
    return {
        "status": "success",
        "mensaje": "¡Inicio de sesión exitoso! 🎉",
        "access_token": token_original,  # Angular guardará este string secreto
        "tipo_token": "bearer",
        "usuario": {
            "id": usuario.id,
            "email": usuario.email,
            "nombre_completo": f"{usuario.perfil.nombre} {usuario.perfil.apellido}",
            "rol": usuario.rol.nombre,
            "cargo": usuario.perfil.cargo
        }
    }