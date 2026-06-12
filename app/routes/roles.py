from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import obtener_db
from app.core.dependencies import verificar_permiso
from app.services.rol_service import RolService
from app.schemas.roles import (
    RolCreate,
    RolUpdate,
    RolResponse,
    ModuloResponse,
    PermisoResponse,
    RolPermisosUpdate
)
from app.schemas.auth import SimpleResponse

router = APIRouter(prefix="/roles", tags=["Gestion de Roles y Permisos"])

@router.get("", response_model=list[RolResponse])
def listar_roles(
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="roles", nivel_requerido=1))
):
    """
    Lista todos los roles del sistema (Requiere Permiso: roles - Nivel 1).
    """
    return RolService.listar_roles(db)

@router.post("", response_model=RolResponse, status_code=status.HTTP_201_CREATED)
def crear_rol(
    datos: RolCreate,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="roles", nivel_requerido=2))
):
    """
    Crea un nuevo rol en el sistema (Requiere Permiso: roles - Nivel 2).
    """
    return RolService.crear_rol(db, datos)

@router.put("/{id}", response_model=RolResponse)
def actualizar_rol(
    id: int,
    datos: RolUpdate,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="roles", nivel_requerido=3))
):
    """
    Actualiza la informacion de un rol (Requiere Permiso: roles - Nivel 3).
    """
    return RolService.actualizar_rol(db, id, datos)

@router.delete("/{id}", response_model=SimpleResponse)
def eliminar_rol(
    id: int,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="roles", nivel_requerido=3))
):
    """
    Elimina un rol si no tiene usuarios asociados (Requiere Permiso: roles - Nivel 3).
    """
    return RolService.eliminar_rol(db, id)

@router.get("/modulos", response_model=list[ModuloResponse])
def listar_modulos(
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="roles", nivel_requerido=1))
):
    """
    Lista todos los modulos registrados para configuracion de permisos (Requiere Permiso: roles - Nivel 1).
    """
    return RolService.listar_modulos(db)

@router.get("/{id}/permisos", response_model=list[PermisoResponse])
def obtener_permisos_rol(
    id: int,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="roles", nivel_requerido=1))
):
    """
    Retorna la configuracion actual de permisos de un rol para todos los modulos (Requiere Permiso: roles - Nivel 1).
    """
    return RolService.obtener_permisos_rol(db, id)

@router.put("/{id}/permisos", response_model=SimpleResponse)
def actualizar_permisos_rol(
    id: int,
    datos: RolPermisosUpdate,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="roles", nivel_requerido=3))
):
    """
    Guarda y actualiza los niveles de acceso de un rol para multiples modulos (Requiere Permiso: roles - Nivel 3).
    """
    return RolService.actualizar_permisos_rol(db, id, datos)
