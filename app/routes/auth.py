from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import obtener_db
from app.models.auth import Usuario
from app.core.dependencies import obtener_usuario_actual 
from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    PerfilUpdateRequest,
    PerfilUpdateResponse,
    CambiarPasswordRequest,
    RecuperarPasswordRequest,
    RestablecerPasswordRequest,
    SimpleResponse
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

seguridad_bearer = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/login", response_model=LoginResponse)
def login(datos_login: LoginRequest, db: Session = Depends(obtener_db)):
    """
    Inicia sesión, verifica credenciales y genera un token de acceso seguro.
    """
    return AuthService.iniciar_sesion(db, datos_login)

@router.post("/logout", response_model=SimpleResponse)
def logout(credenciales: HTTPAuthorizationCredentials = Depends(seguridad_bearer), db: Session = Depends(obtener_db)):
    """
    Invalida el token actual desactivando la sesión del usuario.
    """
    token_cliente = credenciales.credentials.strip('"').strip()
    return AuthService.cerrar_sesion(db, token_cliente)

@router.get("/me", response_model=MeResponse)
def obtener_perfil_autenticado(usuario_actual: Usuario = Depends(obtener_usuario_actual)):
    """
    Retorna los datos del usuario autenticado si la sesión es válida.
    """
    return AuthService.obtener_perfil(usuario_actual)

@router.put("/perfil", response_model=PerfilUpdateResponse)
def actualizar_perfil(
    datos_perfil: PerfilUpdateRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_db)
):
    """
    Actualiza la información personal del usuario logueado.
    """
    return AuthService.actualizar_perfil(db, usuario_actual, datos_perfil)

@router.put("/cambiar-password", response_model=SimpleResponse)
def cambiar_password(
    datos: CambiarPasswordRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_db)
):
    """
    Cambia la contraseña del usuario tras validar la contraseña actual.
    """
    return AuthService.cambiar_password(db, usuario_actual, datos)

@router.post("/recuperar-password", response_model=SimpleResponse)
def solicitar_recuperacion(datos: RecuperarPasswordRequest, db: Session = Depends(obtener_db)):
    """
    Envía instrucciones de recuperación al correo electrónico si está registrado.
    """
    return AuthService.solicitar_recuperacion(db, datos)

@router.post("/restablecer-password", response_model=SimpleResponse)
def restablecer_password(datos: RestablecerPasswordRequest, db: Session = Depends(obtener_db)):
    """
    Establece una nueva contraseña utilizando el token de recuperación recibido por email.
    """
    return AuthService.restablecer_password(db, datos)