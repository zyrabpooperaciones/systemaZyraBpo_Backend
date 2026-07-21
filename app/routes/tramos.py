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
    PlantillaAsociacionesUpdate,
    TramoResumenKpiResponse
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

@router.get("/tramos/{id}/resumen-kpi", response_model=TramoResumenKpiResponse)
def obtener_resumen_kpi_tramo(
    id: int,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="importacion", nivel_requerido=1))
):
    """
    Retorna indicadores clave de rendimiento (KPIs) y montos consolidados de una cartera/tramo.
    Requiere Permiso: importacion - Nivel 1.
    """
    from app.models.cobranzas import Cliente, Cargo, Campana
    from sqlalchemy import func
    from datetime import date

    # Verificar si el tramo existe
    from app.models.cobranzas import Tramo
    tramo_ex = db.query(Tramo).filter(Tramo.id == id).first()
    if not tramo_ex:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="La cartera especificada no existe.")

    # 1. Conteo de Clientes únicos
    total_clientes = db.query(Cliente).join(Cargo, Cliente.id == Cargo.cliente_id).filter(Cargo.tramo_id == id).distinct().count()

    # 2. Conteo de cargos
    total_cargos = db.query(Cargo).filter(Cargo.tramo_id == id).count()

    # 3. Distribución por estados
    cargos_activos = db.query(Cargo).filter(Cargo.tramo_id == id, Cargo.estado == "ACTIVO").count()
    cargos_vencidos = db.query(Cargo).filter(Cargo.tramo_id == id, Cargo.estado == "VENCIDO").count()
    cargos_pagados = db.query(Cargo).filter(Cargo.tramo_id == id, Cargo.estado == "PAGADO").count()

    # 4. Fecha de cierre más cercana no vencida y no pagada
    cierre_q = db.query(Cargo.fecha_cierre).filter(
        Cargo.tramo_id == id,
        Cargo.fecha_cierre >= date.today(),
        Cargo.estado != "PAGADO"
    ).order_by(Cargo.fecha_cierre.asc()).first()
    fecha_cierre_cercana = str(cierre_q[0]) if cierre_q and cierre_q[0] else None

    fecha_cierre_cercana_campanas = []
    if cierre_q and cierre_q[0]:
        camps = db.query(Campana.nombre).join(Cargo, Campana.id == Cargo.campana_id).filter(
            Cargo.tramo_id == id,
            Cargo.fecha_cierre == cierre_q[0]
        ).distinct().all()
        fecha_cierre_cercana_campanas = [c[0] for c in camps]

    # 5. Agregados financieros
    fin_sums = db.query(
        func.sum(Cargo.monto_inicial),
        func.sum(Cargo.monto_interes),
        func.sum(Cargo.monto_gasto_adm),
        func.sum(Cargo.monto_pagado),
        func.sum(Cargo.saldo_cobrar)
    ).filter(Cargo.tramo_id == id).first()

    monto_inicial_total = float(fin_sums[0] or 0.0)
    monto_interes_total = float(fin_sums[1] or 0.0)
    monto_gasto_adm_total = float(fin_sums[2] or 0.0)
    monto_pagado_total = float(fin_sums[3] or 0.0)
    saldo_cobrar_total = float(fin_sums[4] or 0.0)

    # 6. Eficiencia de cobro
    denom = monto_inicial_total + monto_interes_total + monto_gasto_adm_total
    porcentaje_recuperacion = round((monto_pagado_total / denom) * 100, 2) if denom > 0 else 0.0

    return TramoResumenKpiResponse(
        total_clientes=total_clientes,
        total_cargos=total_cargos,
        cargos_activos=cargos_activos,
        cargos_vencidos=cargos_vencidos,
        cargos_pagados=cargos_pagados,
        fecha_cierre_cercana=fecha_cierre_cercana,
        fecha_cierre_cercana_campanas=fecha_cierre_cercana_campanas,
        monto_inicial_total=monto_inicial_total,
        monto_interes_total=monto_interes_total,
        monto_gasto_adm_total=monto_gasto_adm_total,
        monto_pagado_total=monto_pagado_total,
        saldo_cobrar_total=saldo_cobrar_total,
        porcentaje_recuperacion=porcentaje_recuperacion
    )
