from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import obtener_db
from app.core.dependencies import verificar_permiso
from app.services.tramo_service import TramoService
from app.schemas.tramos import (
    TramoResponse,
    TramoUpdateEstado,
    MapeoColumnasTramoCreate,
    MapeoColumnasTramoResponse,
    ConfiguracionPrioridadTelefonosCreate,
    ConfiguracionPrioridadTelefonosResponse,
    PlantillaMapeoCreate,
    PlantillaMapeoResponse,
    PlantillaMapeoDetailResponse,
    PlantillaAsociacionesUpdate
)
from app.schemas.auth import SimpleResponse

router = APIRouter(tags=["Configuracion de Tramos"])

# ============================================================================
# ENDPOINTS DE TRAMOS
# ============================================================================

@router.get("/tramos", response_model=list[TramoResponse])
def listar_tramos(
    ver_inactivos: bool = False,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="configuracion_tramos", nivel_requerido=1))
):
    """
    Lista todos los tramos (Requiere Permiso: configuracion_tramos - Nivel 1).
    Permite filtrar para ver tramos inactivos mediante ?ver_inactivos=true.
    """
    return TramoService.listar_tramos(db, ver_inactivos)

@router.get("/tramos/{id}", response_model=TramoResponse)
def obtener_tramo(
    id: int,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="configuracion_tramos", nivel_requerido=1))
):
    """
    Obtiene los detalles de un tramo por su ID (Requiere Permiso: configuracion_tramos - Nivel 1).
    """
    return TramoService.obtener_tramo(db, id)

@router.put("/tramos/{id}/estado", response_model=TramoResponse)
def actualizar_estado_tramo(
    id: int,
    datos: TramoUpdateEstado,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="configuracion_tramos", nivel_requerido=3))
):
    """
    Activa o desactiva lógicamente un tramo (Requiere Permiso: configuracion_tramos - Nivel 3).
    """
    return TramoService.actualizar_estado_tramo(db, id, datos.activo)

# ============================================================================
# ENDPOINTS DE CATALOGO DE COLUMNAS (DATOS Y MONTOS)
# ============================================================================

@router.get("/tramos/{id}/columnas", response_model=list[MapeoColumnasTramoResponse])
def obtener_columnas_tramo(
    id: int,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="configuracion_tramos", nivel_requerido=1))
):
    """
    Obtiene el catálogo de columnas (datos y montos) configuradas para un tramo (Requiere Permiso: configuracion_tramos - Nivel 1).
    """
    return TramoService.obtener_columnas_tramo(db, id)

@router.post("/tramos/{id}/columnas", response_model=list[MapeoColumnasTramoResponse])
def guardar_columnas_tramo(
    id: int,
    columnas: list[MapeoColumnasTramoCreate],
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="configuracion_tramos", nivel_requerido=2))
):
    """
    Guarda o actualiza las columnas del catálogo de un tramo (Requiere Permiso: configuracion_tramos - Nivel 2).
    """
    return TramoService.guardar_columnas_tramo(db, id, columnas)

# ============================================================================
# ENDPOINTS DE CATALOGO DE TELEFONOS
# ============================================================================

@router.get("/tramos/{id}/telefonos", response_model=list[ConfiguracionPrioridadTelefonosResponse])
def obtener_telefonos_tramo(
    id: int,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="configuracion_tramos", nivel_requerido=1))
):
    """
    Obtiene la lista de teléfonos y prioridades configuradas para un tramo (Requiere Permiso: configuracion_tramos - Nivel 1).
    """
    return TramoService.obtener_telefonos_tramo(db, id)

@router.post("/tramos/{id}/telefonos", response_model=list[ConfiguracionPrioridadTelefonosResponse])
def guardar_telefonos_tramo(
    id: int,
    telefonos: list[ConfiguracionPrioridadTelefonosCreate],
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="configuracion_tramos", nivel_requerido=2))
):
    """
    Guarda o actualiza la lista de teléfonos y prioridades del catálogo de un tramo (Requiere Permiso: configuracion_tramos - Nivel 2).
    """
    return TramoService.guardar_telefonos_tramo(db, id, telefonos)

# ============================================================================
# ENDPOINTS DE PLANTILLAS DE MAPEO
# ============================================================================

@router.get("/tramos/{id}/plantillas", response_model=list[PlantillaMapeoResponse])
def listar_plantillas_tramo(
    id: int,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="configuracion_tramos", nivel_requerido=1))
):
    """
    Lista todas las plantillas asociadas a un tramo (Requiere Permiso: configuracion_tramos - Nivel 1).
    """
    return TramoService.listar_plantillas_tramo(db, id)

@router.post("/tramos/{id}/plantillas", response_model=PlantillaMapeoResponse, status_code=status.HTTP_201_CREATED)
def crear_plantilla_tramo(
    id: int,
    datos: PlantillaMapeoCreate,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="configuracion_tramos", nivel_requerido=2))
):
    """
    Crea una plantilla de mapeo nueva para un tramo.
    Si se envía 'copiar_desde_plantilla_id', clona la configuración de columnas y prioridades de dicha plantilla (Requiere Permiso: configuracion_tramos - Nivel 2).
    """
    return TramoService.crear_plantilla_tramo(db, id, datos)

@router.get("/plantillas/{id}", response_model=PlantillaMapeoDetailResponse)
def obtener_plantilla_mapeo(
    id: int,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="configuracion_tramos", nivel_requerido=1))
):
    """
    Obtiene los detalles de una plantilla y la lista de columnas y teléfonos asociados (Requiere Permiso: configuracion_tramos - Nivel 1).
    """
    return TramoService.obtener_plantilla_mapeo(db, id)

@router.put("/plantillas/{id}/asociaciones", response_model=PlantillaMapeoDetailResponse)
def actualizar_asociaciones_plantilla(
    id: int,
    asociaciones: PlantillaAsociacionesUpdate,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="configuracion_tramos", nivel_requerido=2))
):
    """
    Actualiza la asociación Muchos a Muchos de columnas y teléfonos para una plantilla de mapeo (Requiere Permiso: configuracion_tramos - Nivel 2).
    """
    return TramoService.actualizar_asociaciones_plantilla(db, id, asociaciones)

@router.delete("/plantillas/{id}", response_model=SimpleResponse)
def eliminar_plantilla(
    id: int,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="configuracion_tramos", nivel_requerido=3))
):
    """
    Elimina físicamente una plantilla de mapeo (Requiere Permiso: configuracion_tramos - Nivel 3).
    """
    return TramoService.eliminar_plantilla(db, id)
