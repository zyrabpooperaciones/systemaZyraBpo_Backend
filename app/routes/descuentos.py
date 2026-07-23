from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import obtener_db
from app.core.dependencies import verificar_permiso
from app.models.cobranzas import (
    DescuentoConfig, Tramo, Cargo, Cliente, Campana, 
    Departamento, PerfilRiesgo, SegmentoRolling
)
from app.schemas.descuentos import DescuentoConfigCreate, DescuentoConfigResponse

router = APIRouter(prefix="/descuentos", tags=["descuentos"])

@router.post("", response_model=DescuentoConfigResponse)
def crear_descuento(
    descuento_in: DescuentoConfigCreate,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="descuentos", nivel_requerido=2))
):
    """
    Crea una nueva campaña de descuento para un tramo específico.
    Requiere Permiso: descuentos - Nivel 2 (Supervisor).
    """
    # Verificar si el tramo existe
    tramo = db.query(Tramo).filter(Tramo.id == descuento_in.tramo_id).first()
    if not tramo:
        raise HTTPException(status_code=404, detail="El tramo especificado no existe.")

    # Validar porcentajes
    if not (0 <= descuento_in.pct_descuento_capital <= 100):
        raise HTTPException(status_code=400, detail="El porcentaje de descuento de capital debe estar entre 0 y 100.")
    if not (0 <= descuento_in.pct_descuento_interes <= 100):
        raise HTTPException(status_code=400, detail="El porcentaje de descuento de interés debe estar entre 0 y 100.")
    if not (0 <= descuento_in.pct_descuento_gasto <= 100):
        raise HTTPException(status_code=400, detail="El porcentaje de descuento de gastos debe estar entre 0 y 100.")

    db_desc = DescuentoConfig(
        tramo_id=descuento_in.tramo_id,
        nombre=descuento_in.nombre,
        descuento_monto_fijo=descuento_in.descuento_monto_fijo,
        pct_descuento_capital=descuento_in.pct_descuento_capital,
        pct_descuento_interes=descuento_in.pct_descuento_interes,
        pct_descuento_gasto=descuento_in.pct_descuento_gasto,
        campanas=descuento_in.campanas,
        departamentos=descuento_in.departamentos,
        perfiles_riesgo=descuento_in.perfiles_riesgo,
        segmentos_rolling=descuento_in.segmentos_rolling,
        activo=descuento_in.activo
    )
    db.add(db_desc)
    db.commit()
    db.refresh(db_desc)
    return db_desc

@router.get("/catalogos-filtrados/{tramo_id}")
def obtener_catalogos_filtrados(
    tramo_id: int,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="descuentos", nivel_requerido=1))
):
    """
    Retorna listas de filtros (Campañas, Departamentos, Perfiles de Riesgo, Segmentos Rolling)
    que tienen al menos una deuda activa (ACTIVO) en el tramo indicado.
    """
    # Campañas activas
    campanas_activas = db.query(Campana.nombre).join(Cargo, Cargo.campana_id == Campana.id).filter(
        Cargo.tramo_id == tramo_id,
        Cargo.estado == "ACTIVO"
    ).distinct().all()
    campanas = [c[0] for c in campanas_activas if c[0]]

    # Departamentos activos
    deptos_activos = db.query(Departamento.nombre).join(Cliente, Cliente.departamento_id == Departamento.id).join(Cargo, Cargo.cliente_id == Cliente.id).filter(
        Cargo.tramo_id == tramo_id,
        Cargo.estado == "ACTIVO"
    ).distinct().all()
    departamentos = [d[0] for d in deptos_activos if d[0]]

    # Perfiles de riesgo activos
    perfiles_activos = db.query(PerfilRiesgo.nombre).join(Cliente, Cliente.perfil_riesgo_id == PerfilRiesgo.id).join(Cargo, Cargo.cliente_id == Cliente.id).filter(
        Cargo.tramo_id == tramo_id,
        Cargo.estado == "ACTIVO"
    ).distinct().all()
    perfiles = [p[0] for p in perfiles_activos if p[0]]

    # Segmentos rolling activos
    rolling_activos = db.query(SegmentoRolling.nombre).join(Cliente, Cliente.segmento_rolling_id == SegmentoRolling.id).join(Cargo, Cargo.cliente_id == Cliente.id).filter(
        Cargo.tramo_id == tramo_id,
        Cargo.estado == "ACTIVO"
    ).distinct().all()
    rolling = [r[0] for r in rolling_activos if r[0]]

    return {
        "campanas": sorted(campanas),
        "departamentos": sorted(departamentos),
        "perfiles_riesgo": sorted(perfiles),
        "segmentos_rolling": sorted(rolling)
    }

@router.get("/tramo/{tramo_id}", response_model=List[DescuentoConfigResponse])
def listar_descuentos_tramo(
    tramo_id: int,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="descuentos", nivel_requerido=1))
):
    """
    Lista todas las campañas de descuento (activas e inactivas) de un tramo específico.
    Requiere Permiso: descuentos - Nivel 1 (Operador).
    """
    # Verificar si el tramo existe
    tramo = db.query(Tramo).filter(Tramo.id == tramo_id).first()
    if not tramo:
        raise HTTPException(status_code=404, detail="El tramo especificado no existe.")

    descuentos = db.query(DescuentoConfig).filter(
        DescuentoConfig.tramo_id == tramo_id
    ).order_by(DescuentoConfig.created_at.desc()).all()
    return descuentos

@router.put("/{id}/desactivar", response_model=DescuentoConfigResponse)
def desactivar_descuento(
    id: int,
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="descuentos", nivel_requerido=2))
):
    """
    Desactiva manualmente una campaña de descuento activa.
    Requiere Permiso: descuentos - Nivel 2 (Supervisor).
    """
    descuento = db.query(DescuentoConfig).filter(DescuentoConfig.id == id).first()
    if not descuento:
        raise HTTPException(status_code=404, detail="La campaña de descuento no existe.")
    
    descuento.activo = False
    db.commit()
    db.refresh(descuento)
    return descuento
