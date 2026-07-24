from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, or_, and_
from datetime import date
from typing import Optional, List, Dict, Any
from app.core.database import obtener_db
from app.core.dependencies import verificar_permiso
from app.models.cobranzas import Cargo, Cliente, Tramo, Campana

router = APIRouter(prefix="/metricas", tags=["Modulo de Metricas"])

@router.get("/catalogos-filtrados")
def obtener_catalogos_filtros(
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="metricas", nivel_requerido=1))
):
    """
    Retorna la lista de tramos activos y campañas registradas para llenar los selectores de filtro.
    """
    tramos = db.query(Tramo.id, Tramo.nombre).filter(Tramo.activo == True).order_by(Tramo.nombre).all()
    campanas = db.query(Campana.id, Campana.nombre).order_by(Campana.nombre).all()

    return {
        "tramos": [{"id": t.id, "nombre": t.nombre} for t in tramos],
        "campanas": [{"id": c.id, "nombre": c.nombre} for c in campanas]
    }

@router.get("/resumen")
def obtener_resumen_metricas(
    tramo_id: Optional[int] = Query(None, description="Filtrar por ID de Tramo/Cartera"),
    campana_id: Optional[int] = Query(None, description="Filtrar por ID de Campaña"),
    vigencia: Optional[str] = Query(None, description="Filtrar por Vigencia Temporal (VIGENTE, VENCIDO)"),
    situacion_pago: Optional[str] = Query(None, description="Filtrar por Situación de Pago (PENDIENTE, PAGADO)"),
    db: Session = Depends(obtener_db),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="metricas", nivel_requerido=1))
):
    """
    Retorna métricas consolidadas de la cartera con desgloses en 2 dimensiones:
    1. Vigencia Temporal (VIGENTE vs VENCIDO según Fecha de Cierre).
    2. Situación Financiera (PENDIENTE vs PAGADO según Saldo por Cobrar).
    """
    today = date.today()
    query = db.query(Cargo).filter(Cargo.activo == True)

    # 1. Filtros base por Cartera y Campaña
    if tramo_id:
        query = query.filter(Cargo.tramo_id == tramo_id)
    if campana_id:
        query = query.filter(Cargo.campana_id == campana_id)

    # 2. Dimensión 1: Vigencia Operativa (Fecha Cierre)
    if vigencia and vigencia.strip() != "":
        v_str = vigencia.strip().upper()
        if v_str == "VIGENTE":
            query = query.filter(or_(Cargo.fecha_cierre == None, Cargo.fecha_cierre >= today))
        elif v_str == "VENCIDO":
            query = query.filter(and_(Cargo.fecha_cierre != None, Cargo.fecha_cierre < today))

    # 3. Dimensión 2: Situación Financiera (Pago)
    if situacion_pago and situacion_pago.strip() != "":
        p_str = situacion_pago.strip().upper()
        if p_str == "PENDIENTE":
            query = query.filter(Cargo.saldo_cobrar > 1.00)
        elif p_str == "PAGADO":
            query = query.filter(Cargo.saldo_cobrar <= 1.00)

    # Agregaciones dinámicas sobre los filtros actualmente aplicados
    stats = query.with_entities(
        func.count(distinct(Cargo.cliente_id)).label("total_deudores"),
        func.count(Cargo.id).label("total_cargos"),
        func.coalesce(func.sum(Cargo.monto_inicial), 0.0).label("monto_inicial_total"),
        func.coalesce(func.sum(Cargo.monto_interes), 0.0).label("monto_interes_total"),
        func.coalesce(func.sum(Cargo.monto_gasto_adm), 0.0).label("monto_gasto_adm_total"),
        func.coalesce(func.sum(Cargo.deuda_total), 0.0).label("deuda_total_bruta"),
        func.coalesce(func.sum(Cargo.monto_pagado), 0.0).label("monto_pagado_total"),
        func.coalesce(func.sum(Cargo.monto_descontar), 0.0).label("monto_descontar_total"),
        func.coalesce(func.sum(Cargo.saldo_cobrar), 0.0).label("saldo_cobrar_total")
    ).first()

    # --- MATRIZ PANORÁMICA DE 4 CUADRANTES DE CARTERA (Vigencia x Estado Financiero) ---
    base_q = db.query(Cargo).filter(Cargo.activo == True)
    if tramo_id:
        base_q = base_q.filter(Cargo.tramo_id == tramo_id)
    if campana_id:
        base_q = base_q.filter(Cargo.campana_id == campana_id)

    # Helper para obtener estadísticas completas de cada cuadrante
    def get_quadrant_stats(q_filter, is_pagado=False):
        res = q_filter.with_entities(
            func.count(Cargo.id).label("cargos"),
            func.count(distinct(Cargo.cliente_id)).label("deudores"),
            func.coalesce(func.sum(Cargo.monto_inicial), 0.0).label("monto_inicial"),
            func.coalesce(func.sum(Cargo.deuda_total), 0.0).label("deuda_total"),
            func.coalesce(func.sum(Cargo.monto_pagado), 0.0).label("monto_pagado"),
            func.coalesce(func.sum(Cargo.saldo_cobrar), 0.0).label("saldo_cobrar")
        ).first()
        raw_s = float(res.saldo_cobrar or 0.0)
        # Si es un cuadrante de pagados, el saldo pendiente es 0.00 (los montos <= 1.00 son margen de tolerancia)
        final_s = 0.0 if is_pagado else max(0.0, raw_s)
        return {
            "cargos": res.cargos or 0,
            "deudores": res.deudores or 0,
            "monto_inicial": round(float(res.monto_inicial or 0.0), 2),
            "deuda_total": round(float(res.deuda_total or 0.0), 2),
            "monto_pagado": round(float(res.monto_pagado or 0.0), 2),
            "saldo_cobrar": round(final_s, 2)
        }

    # 1. Vigentes con Deuda (En gestión activa)
    v_pend_stats = get_quadrant_stats(base_q.filter(
        or_(Cargo.fecha_cierre == None, Cargo.fecha_cierre >= today),
        Cargo.saldo_cobrar > 1.00
    ), is_pagado=False)

    # 2. Vigentes Pagados (Liquidados a tiempo)
    v_pag_stats = get_quadrant_stats(base_q.filter(
        or_(Cargo.fecha_cierre == None, Cargo.fecha_cierre >= today),
        Cargo.saldo_cobrar <= 1.00
    ), is_pagado=True)

    # 3. Vencidos con Deuda (Expirados sin cobrar)
    venc_pend_stats = get_quadrant_stats(base_q.filter(
        Cargo.fecha_cierre != None,
        Cargo.fecha_cierre < today,
        Cargo.saldo_cobrar > 1.00
    ), is_pagado=False)

    # 4. Vencidos Pagados (Liquidados fuera de fecha)
    venc_pag_stats = get_quadrant_stats(base_q.filter(
        Cargo.fecha_cierre != None,
        Cargo.fecha_cierre < today,
        Cargo.saldo_cobrar <= 1.00
    ), is_pagado=True)

    monto_inicial = float(stats.monto_inicial_total or 0.0)
    monto_interes = float(stats.monto_interes_total or 0.0)
    monto_gasto = float(stats.monto_gasto_adm_total or 0.0)
    deuda_bruta = float(stats.deuda_total_bruta or 0.0)
    monto_pagado = float(stats.monto_pagado_total or 0.0)
    monto_descontar = float(stats.monto_descontar_total or 0.0)
    
    # Manejo de centavos de tolerancia en saldo por cobrar
    raw_saldo = float(stats.saldo_cobrar_total or 0.0)
    if situacion_pago and situacion_pago.strip().upper() == "PAGADO":
        saldo_cobrar = 0.0
    else:
        saldo_cobrar = max(0.0, raw_saldo)

    # Lógica de Efectividad (%): tope del 100.0% para evitar porcentajes ilógicos por sobrepagos o centavos
    pct_recuperacion = 0.0
    if deuda_bruta > 0:
        raw_pct = ((monto_pagado + monto_descontar) / deuda_bruta) * 100.0
        pct_recuperacion = round(min(raw_pct, 100.0), 2)

    # Cálculo específico de la tolerancia acumulada por centavos/montos no cobrados (0 < saldo <= 1.00 BOB)
    tolerancia_query = base_q.filter(Cargo.saldo_cobrar > 0, Cargo.saldo_cobrar <= 1.00)
    monto_tolerancia = tolerancia_query.with_entities(func.coalesce(func.sum(Cargo.saldo_cobrar), 0.0)).scalar()
    
    # Desglose en dos orígenes: pagos parciales (centavos faltantes) vs micro-deudas iniciales sin pago
    tol_pagos = base_q.filter(Cargo.monto_pagado > 0, Cargo.saldo_cobrar > 0, Cargo.saldo_cobrar <= 1.00).with_entities(func.coalesce(func.sum(Cargo.saldo_cobrar), 0.0)).scalar()
    tol_micro = base_q.filter(Cargo.monto_pagado == 0, Cargo.saldo_cobrar > 0, Cargo.saldo_cobrar <= 1.00).with_entities(func.coalesce(func.sum(Cargo.saldo_cobrar), 0.0)).scalar()

    return {
        "total_deudores": stats.total_deudores or 0,
        "total_cargos": stats.total_cargos or 0,
        
        # Matriz panorámica 2x2 desglosada
        "matriz": {
            "vigentes_pendientes": v_pend_stats,
            "vigentes_pagados": v_pag_stats,
            "vencidos_pendientes": venc_pend_stats,
            "vencidos_pagados": venc_pag_stats
        },

        # Totales financieros dinámicos según los 4 filtros
        "monto_inicial_total": round(monto_inicial, 2),
        "monto_interes_total": round(monto_interes, 2),
        "monto_gasto_adm_total": round(monto_gasto, 2),
        "deuda_total_bruta": round(deuda_bruta, 2),
        "monto_pagado_total": round(monto_pagado, 2),
        "monto_descontar_total": round(monto_descontar, 2),
        "saldo_cobrar_total": round(saldo_cobrar, 2),
        "monto_tolerancia_total": round(float(monto_tolerancia or 0.0), 2),
        "monto_tolerancia_pagos_parciales": round(float(tol_pagos or 0.0), 2),
        "monto_tolerancia_micro_deudas": round(float(tol_micro or 0.0), 2),
        "porcentaje_recuperacion": pct_recuperacion
    }
