from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import obtener_db
from app.models.auth import Usuario, Perfil, Sesion
from app.services.security import SecurityService
from datetime import datetime, timezone, timedelta
import secrets
import hashlib

# --- NUEVA IMPORTACIÓN PARA CAPTURAR TOKENS DE FORMA PROFESIONAL ---
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
seguridad_bearer = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["Autenticación"])

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(datos_login: LoginRequest, db: Session = Depends(obtener_db)):
    # ... (Todo tu código de login con el escudo de 5 intentos se queda EXACTAMENTE igual) ...
    usuario = db.query(Usuario).filter(Usuario.email == datos_login.email).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Correo o contraseña incorrectos")
    if usuario.estado != "ACTIVO":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"El usuario se encuentra {usuario.estado}.")
    
    ahora = datetime.now(timezone.utc)
    if usuario.bloqueado_hasta:
        if ahora < usuario.bloqueado_hasta:
            tiempo_restante = usuario.bloqueado_hasta - ahora
            minutos_restantes = int(tiempo_restante.total_seconds() / 60) + 1
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Cuenta bloqueada. Intente en {minutos_restantes} min.")
        else:
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
            db.commit()

    password_valida = SecurityService.verificar_password(datos_login.password, usuario.password_hash)
    if not password_valida:
        usuario.intentos_fallidos += 1
        if usuario.intentos_fallidos >= 5:
            usuario.bloqueado_hasta = ahora + timedelta(minutes=15)
            db.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Demasiados intentos. Bloqueado por 15 minutos.")
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Correo o contraseña incorrectos")

    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None

    token_original = secrets.token_hex(32)
    token_hasheado = hashlib.sha256(token_original.encode('utf-8')).hexdigest()
    tiempo_expiracion = ahora + timedelta(hours=12)
    
    nueva_sesion = Sesion(usuario_id=usuario.id, token_sesion_hash=token_hasheado, valida=True, expira_en=tiempo_expiracion)
    db.add(nueva_sesion)
    db.commit() 

    return {
        "status": "success",
        "mensaje": "¡Inicio de sesión exitoso! 🎉",
        "access_token": token_original,
        "tipo_token": "bearer",
        "usuario": {"id": usuario.id, "email": usuario.email, "nombre_completo": f"{usuario.perfil.nombre} {usuario.perfil.apellido}", "rol": usuario.rol.nombre, "cargo": usuario.perfil.cargo}
    }

# ============================================================================
# NUEVA RUTA: CERRAR SESIÓN (LOGOUT)
# ============================================================================
@router.post("/logout")
def logout(credenciales: HTTPAuthorizationCredentials = Depends(seguridad_bearer), db: Session = Depends(obtener_db)):
    # A. Extraer el token puro que mandó el cliente
    token_cliente = credenciales.credentials.strip('"').strip()
    
    # B. Aplicarle el mismo hash SHA-256 para poder buscarlo en Postgres
    token_hasheado = hashlib.sha256(token_cliente.encode('utf-8')).hexdigest()
    
    # C. Buscar la sesión en la base de datos
    sesion_activa = db.query(Sesion).filter(Sesion.token_sesion_hash == token_hasheado).first()
    
    # D. Si no existe la sesión o ya era falsa, simplemente avisamos
    if not sesion_activa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesión invalida o no encontrada"
        )
    
    # E. ¡LA REGLA DE JAIRO! Cambiamos la bandera a FALSE para matar el token
    sesion_activa.valida = False
    db.commit() # Guardamos en Postgres
    
    return {
        "status": "success",
        "mensaje": "Sesión cerrada correctamente. ¡El token ha muerto con éxito! 💀"
    }
    
    # --- IMPORTAMOS EL GUARDIA QUE ACABAMOS DE CREAR (Agrégalo arriba junto a las importaciones si prefieres o déjalo ahí) ---
from app.core.dependencies import obtener_usuario_actual

# ============================================================================
# RUTA PROTEGIDA DE PRUEBA: OBTENER DATOS DEL USUARIO LOGUEADO
# ============================================================================
@router.get("/me")
def obtener_perfil_autenticado(usuario_actual: Usuario = Depends(obtener_usuario_actual)):
    """
    Ruta bloqueada. Solo responde si le envías un token válido en las cabeceras.
    """
    return {
        "status": "success",
        "mensaje": "¡Acceso concedido por el Guardián!",
        "datos_seguros": {
            "usuario_id": usuario_actual.id,
            "email": usuario_actual.email,
            "rol": usuario_actual.rol.nombre,
            "nombre": usuario_actual.perfil.nombre,
            "apellido": usuario_actual.perfil.apellido
        }
    }