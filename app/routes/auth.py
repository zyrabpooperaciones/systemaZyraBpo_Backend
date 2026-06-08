from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import obtener_db
from app.models.auth import Usuario, Perfil, Sesion
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
    
    # 2. Verificar estado administrativo básico
    if usuario.estado != "ACTIVO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"El usuario se encuentra {usuario.estado}. Contacte al administrador."
        )

    # 3. ESCUDO EVOLUCIONADO: Manejo inteligente de penalizaciones de tiempo
    ahora = datetime.now(timezone.utc)
    if usuario.bloqueado_hasta:
        if ahora < usuario.bloqueado_hasta:
            # Sigue bloqueado: Calculamos los minutos restantes
            tiempo_restante = usuario.bloqueado_hasta - ahora
            minutos_restantes = int(tiempo_restante.total_seconds() / 60) + 1
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cuenta temporalmente bloqueada por seguridad. Intente de nuevo en {minutos_restantes} minuto(s)."
            )
        else:
            # REGLA JAIRO: El tiempo ya pasó. Reiniciamos la pizarra a 0 de forma automática
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
            db.commit() # Guardamos el reseteo de inmediato

    # 4. Validar contraseña con Bcrypt
    password_valida = SecurityService.verificar_password(
        datos_login.password, 
        usuario.password_hash
    )
    
    # --- MANEJO DE INTENTOS FALLIDOS (LÍMITE: 5) ---
    if not password_valida:
        usuario.intentos_fallidos += 1
        
        # Al llegar al 5to intento fallido, se congela por 15 minutos
        if usuario.intentos_fallidos >= 5:
            usuario.bloqueado_hasta = ahora + timedelta(minutes=15)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Demasiados intentos incorrectos. Tu cuenta ha sido bloqueada por 15 minutos."
            )
        
        db.commit() # Guardamos el contador actual (1, 2, 3 o 4)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos"
        )

    # --- INICIO EXITOSO: RESETEO TOTAL ---
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None

    # 5. Generación de Sesión Persistente (Token)
    token_original = secrets.token_hex(32)
    token_hasheado = hashlib.sha256(token_original.encode('utf-8')).hexdigest()
    tiempo_expiracion = ahora + timedelta(hours=24)
    
    nueva_sesion = Sesion(
        usuario_id=usuario.id,
        token_sesion_hash=token_hasheado,
        valida=True,
        expira_en=tiempo_expiracion
    )
    db.add(nueva_sesion)
    db.commit() 

    return {
        "status": "success",
        "mensaje": "¡Inicio de sesión exitoso! 🎉",
        "access_token": token_original,
        "tipo_token": "bearer",
        "usuario": {
            "id": usuario.id,
            "email": usuario.email,
            "nombre_completo": f"{usuario.perfil.nombre} {usuario.perfil.apellido}",
            "rol": usuario.rol.nombre,
            "cargo": usuario.perfil.cargo
        }
    }