from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import obtener_db
from app.core.dependencies import verificar_permiso
from app.models.auth import Usuario
from app.services.usuario_service import UsuarioService
from app.schemas.usuarios import (
    UsuarioCreate,
    UsuarioUpdate,
    UsuarioResponse
)
from app.schemas.auth import SimpleResponse

router = APIRouter(prefix="/usuarios", tags=["Gestion de Usuarios"])

@router.get("", response_model=list[UsuarioResponse])
def listar_usuarios(
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="usuarios", nivel_requerido=1))
):
    """
    Lista todos los usuarios con sus perfiles y roles (Requiere Permiso: usuarios - Nivel 1).
    """
    return UsuarioService.listar_usuarios(db)

@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    datos: UsuarioCreate,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="usuarios", nivel_requerido=2))
):
    """
    Crea un nuevo usuario y su perfil asociado (Requiere Permiso: usuarios - Nivel 2).
    """
    return UsuarioService.crear_usuario(db, datos)

@router.put("/{id}", response_model=UsuarioResponse)
def actualizar_usuario(
    id: int,
    datos: UsuarioUpdate,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="usuarios", nivel_requerido=3))
):
    """
    Actualiza la informacion y estado de un usuario (Requiere Permiso: usuarios - Nivel 3).
    """
    return UsuarioService.actualizar_usuario(db, id, datos)

@router.delete("/{id}", response_model=SimpleResponse)
def eliminar_usuario(
    id: int,
    db: Session = Depends(obtener_db),
    usuario_actual: Usuario = Depends(verificar_permiso(modulo_interno="usuarios", nivel_requerido=3))
):
    """
    Elimina un usuario y su perfil de la base de datos (Requiere Permiso: usuarios - Nivel 3).
    Evita la auto-eliminacion del usuario logueado.
    """
    return UsuarioService.eliminar_usuario(db, id, usuario_actual.id)
