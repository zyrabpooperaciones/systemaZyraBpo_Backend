from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.core.database import obtener_db
from app.models.auth import Usuario, Perfil, Sesion
from app.services.security import SecurityService
from app.core.dependencies import obtener_usuario_actual 
from app.services.email_service import EmailService
from datetime import datetime, timezone, timedelta
import secrets
import hashlib

# --- NUEVA IMPORTACIÓN PARA CAPTURAR TOKENS DE FORMA PROFESIONAL ---
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
seguridad_bearer = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["Autenticación"])

# ============================================================================
# MODELOS DE PETICIÓN (PYDANTIC)
# ============================================================================
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RecuperarPasswordRequest(BaseModel): 
    email: EmailStr

class RestablecerPasswordRequest(BaseModel):
    token: str
    nueva_password: str


# ============================================================================
# RUTA: INICIO DE SESIÓN (LOGIN)
# ============================================================================
@router.post("/login")
def login(datos_login: LoginRequest, db: Session = Depends(obtener_db)):
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
# RUTA: CERRAR SESIÓN (LOGOUT)
# ============================================================================
@router.post("/logout")
def logout(credenciales: HTTPAuthorizationCredentials = Depends(seguridad_bearer), db: Session = Depends(obtener_db)):
    token_cliente = credenciales.credentials.strip('"').strip()
    token_hasheado = hashlib.sha256(token_cliente.encode('utf-8')).hexdigest()
    
    sesion_activa = db.query(Sesion).filter(Sesion.token_sesion_hash == token_hasheado).first()
    
    if not sesion_activa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesión invalida o no encontrada"
        )
    
    sesion_activa.valida = False
    db.commit() 
    
    return {
        "status": "success",
        "mensaje": "Sesión cerrada correctamente. ¡El token ha muerto con éxito! 💀"
    }
    

# ============================================================================
# RUTA PROTEGIDA DE PRUEBA: OBTENER DATOS DEL USUARIO LOGUEADO
# ============================================================================
@router.get("/me")
def obtener_perfil_autenticado(usuario_actual: Usuario = Depends(obtener_usuario_actual)):
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


# ============================================================================
# RUTA: SOLICITAR RECUPERACIÓN (¡Automatizada con envío real! 📨)
# ============================================================================
@router.post("/recuperar-password")
def solicitar_recuperacion(datos: RecuperarPasswordRequest, db: Session = Depends(obtener_db)):
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
    
    if not usuario:
        return {
            "status": "success",
            "mensaje": "Si el correo electrónico institucional existe, se han generado las instrucciones."
        }
        
    ahora = datetime.now(timezone.utc)
    token_original = secrets.token_hex(32)
    token_hasheado = hashlib.sha256(token_original.encode('utf-8')).hexdigest()
    tiempo_expiracion = ahora + timedelta(minutes=15)
    
    usuario.recuperar_password_token_hash = token_hasheado
    usuario.recuperar_password_expira = tiempo_expiracion
    db.commit()
    
    # ¡EL ROBOT CARTERO ENTRA EN ACCIÓN!
    # Intenta enviar el correo real de forma segura usando la cuenta configurada
    correo_enviado = EmailService.enviar_correo_recuperacion(usuario.email, token_original)
    
    # Si Google rechaza la conexión o falla el SMTP, el backend frena y avisa
    if not correo_enviado:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="El token se generó, pero el servidor de correos falló al enviarlo."
        )
    
    # El token_de_prueba se eliminó del JSON. Ahora viaja 100% oculto y seguro en el Mail
    return {
        "status": "success",
        "mensaje": "Las instrucciones de recuperación han sido enviadas a tu correo electrónico institucional. Revisa tu bandeja de entrada."
    }


# ============================================================================
# RUTA: REESCRIBIR LA CONTRASEÑA (Usa el token para validar)
# ============================================================================
@router.post("/restablecer-password")
def restablecer_password(datos: RestablecerPasswordRequest, db: Session = Depends(obtener_db)):
    token_cliente_hash = hashlib.sha256(datos.token.encode('utf-8')).hexdigest()
    usuario = db.query(Usuario).filter(Usuario.recuperar_password_token_hash == token_cliente_hash).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El enlace de recuperación es inválido o ya fue utilizado."
        )
        
    ahora = datetime.now(timezone.utc)
    if ahora > usuario.recuperar_password_expira:
        usuario.recuperar_password_token_hash = None
        usuario.recuperar_password_expira = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El enlace de recuperación ha expirado (Límite: 15 minutos)."
        )
        
    # Acoplado perfectamente al nombre real de tu SecurityService
    nueva_password_cifrada = SecurityService.generar_hash(datos.nueva_password)
    
    usuario.password_hash = nueva_password_cifrada
    usuario.recuperar_password_token_hash = None
    usuario.recuperar_password_expira = None
    
    # Desbloqueo inmediato por cambio exitoso de credenciales
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    
    db.commit()
    
    return {
        "status": "success",
        "mensaje": "¡Contraseña actualizada con éxito! 🎉 Ya puedes iniciar sesión con tus nuevas credenciales."
    }