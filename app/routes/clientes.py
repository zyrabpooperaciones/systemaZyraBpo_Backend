from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timezone
from app.core.database import obtener_db
from app.core.dependencies import verificar_permiso
from app.models.auth import Usuario
from app.models.cobranzas import Cliente, Cargo, TelefonoCliente, MovimientoCargo, Campana
from app.schemas.clientes import (
    PaginatedClientesResponse, DetalleCliente360Response,
    ClienteSearchItem, TelefonoClienteDetalle, CargoClienteDetalle,
    MovimientoCargoDetalle, DeshabilitarCargoRequest
)
from app.services.descuento_service import calcular_descuento_cargo
from app.services.security import SecurityService

router = APIRouter(prefix="/clientes", tags=["Modulo de Clientes"])

@router.get("/buscar", response_model=PaginatedClientesResponse)
def buscar_clientes(
    query: Optional[str] = None,
    numero_cargo: Optional[str] = None,
    tramo_id: Optional[int] = None,
    campana_id: Optional[int] = None,
    estado: Optional[str] = None,
    limit: int = 15,
    offset: int = 0,
    db: Session = Depends(obtener_db),
    _usuario: Usuario = Depends(verificar_permiso(modulo_interno="clientes", nivel_requerido=1))
):
    """
    Realiza la búsqueda paginada y filtrada de clientes en base a diversos criterios (Código, Nombre, CI, Teléfono, Número de Cargo).
    Requiere Permiso: clientes - Nivel 1.
    """
    # 1. Construir la consulta base
    base_query = db.query(Cliente)

    # 2. Aplicar filtro específico por Número de Cargo
    if numero_cargo and numero_cargo.strip() != "":
        has_cargo = select(Cargo.cliente_id).filter(Cargo.numero_cargo.ilike(f"%{numero_cargo.strip()}%"))
        base_query = base_query.filter(Cliente.id.in_(has_cargo))

    # 3. Aplicar filtros relacionados a cargos
    if tramo_id or campana_id or estado:
        base_query = base_query.join(Cargo, Cliente.id == Cargo.cliente_id)
        if tramo_id:
            base_query = base_query.filter(Cargo.tramo_id == tramo_id)
        if campana_id:
            base_query = base_query.filter(Cargo.campana_id == campana_id)
        if estado:
            base_query = base_query.filter(Cargo.estado == estado)

    # 4. Aplicar búsqueda global por texto (Código, Nombre, CI, Teléfono o Número de Cargo)
    if query:
        q_text = f"%{query}%"
        # Subquery para buscar por número telefónico y por número de cargo
        has_phone = select(TelefonoCliente.cliente_id).filter(TelefonoCliente.numero.ilike(q_text))
        has_cargo_num = select(Cargo.cliente_id).filter(Cargo.numero_cargo.ilike(q_text))
        base_query = base_query.filter(
            (Cliente.codigo_cliente_belcor.ilike(q_text)) |
            (Cliente.nombre_completo.ilike(q_text)) |
            (Cliente.numero_documento.ilike(q_text)) |
            (Cliente.id.in_(has_phone)) |
            (Cliente.id.in_(has_cargo_num))
        )

    # Evitar duplicados si hay joins
    base_query = base_query.distinct()

    # 4. Obtener totales y paginar
    total_count = base_query.count()
    page_clientes = base_query.order_by(Cliente.nombre_completo).offset(offset).limit(limit).all()

    # 5. Mapear al esquema de respuesta con cálculos (solamente sobre cargos activos)
    items = []
    for c in page_clientes:
        cargos_q = db.query(Cargo).filter(Cargo.cliente_id == c.id, Cargo.activo == True)
        if tramo_id:
            cargos_q = cargos_q.filter(Cargo.tramo_id == tramo_id)
        if campana_id:
            cargos_q = cargos_q.filter(Cargo.campana_id == campana_id)
        if estado:
            cargos_q = cargos_q.filter(Cargo.estado == estado)
        
        cargos_list = cargos_q.all()

        saldo_total = sum(float(cargo.saldo_cobrar) for cargo in cargos_list)
        saldo_neto_total = 0.0
        for cargo in cargos_list:
            desc_val = calcular_descuento_cargo(cargo, db)
            saldo_neto_total += max(float(cargo.saldo_cobrar) - desc_val, 0.0)

        campanas = list(set(cargo.campana.nombre for cargo in cargos_list if cargo.campana))

        # Teléfono principal (menor prioridad = más importante)
        tel_principal = db.query(TelefonoCliente.numero).filter(
            TelefonoCliente.cliente_id == c.id,
            TelefonoCliente.estado == "ACTIVO"
        ).order_by(TelefonoCliente.prioridad.asc()).first()
        
        tel_str = tel_principal[0] if tel_principal else None

        # Determinar estado general del cliente
        estados = [cargo.estado.upper() for cargo in cargos_list]
        if "ACTIVO" in estados:
            est_gen = "ACTIVO"
        elif "VENCIDO" in estados:
            est_gen = "VENCIDO"
        elif "PAGADO" in estados:
            est_gen = "PAGADO"
        else:
            est_gen = "INACTIVO"

        items.append(ClienteSearchItem(
            id=c.id,
            codigo_cliente_belcor=c.codigo_cliente_belcor,
            nombre_completo=c.nombre_completo,
            numero_documento=c.numero_documento,
            cantidad_cargos=len(cargos_list),
            saldo_total_pendiente=saldo_total,
            saldo_neto_pendiente=round(saldo_neto_total, 2),
            telefono_principal=tel_str,
            campanas_activas=campanas,
            estado_general=est_gen
        ))

    return PaginatedClientesResponse(total=total_count, items=items)

@router.get("/{cliente_id}/detalle", response_model=DetalleCliente360Response)
def obtener_detalle_cliente_360(
    cliente_id: int,
    db: Session = Depends(obtener_db),
    _usuario: Usuario = Depends(verificar_permiso(modulo_interno="clientes", nivel_requerido=1))
):
    """
    Retorna la ficha del deudor consolidada con teléfonos, cargos y movimientos contables.
    Requiere Permiso: clientes - Nivel 1.
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El deudor especificado no existe en el sistema."
        )

    # Cargar teléfonos ordenados por prioridad_calculada ascendente
    telefonos = db.query(TelefonoCliente).filter(
        TelefonoCliente.cliente_id == cliente_id
    ).order_by(TelefonoCliente.prioridad.asc()).all()

    # Cargar deudas (cargos)
    cargos = db.query(Cargo).filter(
        Cargo.cliente_id == cliente_id
    ).order_by(Cargo.numero_cargo).all()

    cargos_res = []
    for cg in cargos:
        desc_val = calcular_descuento_cargo(cg, db)
        liq_val = round(max(float(cg.saldo_cobrar) - desc_val, 0.0), 2)
        usr_nom = None
        if cg.usuario_deshabilitacion:
            u = cg.usuario_deshabilitacion
            usr_nom = f"{u.perfil.nombre} {u.perfil.apellido}".strip() if u.perfil else u.email

        cargos_res.append(CargoClienteDetalle(
            id=cg.id,
            numero_cargo=cg.numero_cargo,
            campana_nombre=cg.campana.nombre if cg.campana else "",
            dias_atraso=cg.dias_atraso,
            fecha_cierre=cg.fecha_cierre,
            monto_inicial=float(cg.monto_inicial),
            monto_interes=float(cg.monto_interes),
            monto_gasto_adm=float(cg.monto_gasto_adm),
            monto_pagado=float(cg.monto_pagado),
            saldo_cobrar=float(cg.saldo_cobrar),
            descuento_aplicable=desc_val,
            monto_para_liquidar=liq_val,
            estado=cg.estado,
            observacion=cg.observacion,
            activo=cg.activo,
            motivo_deshabilitacion=cg.motivo_deshabilitacion,
            fecha_deshabilitacion=cg.fecha_deshabilitacion,
            usuario_deshabilitacion_nombre=usr_nom
        ))

    # Cargar movimientos contables cruzando con cargos para obtener el numero_cargo
    movimientos = db.query(MovimientoCargo).join(Cargo).filter(
        Cargo.cliente_id == cliente_id
    ).order_by(MovimientoCargo.fecha_movimiento.desc()).all()

    movimientos_res = [
        MovimientoCargoDetalle(
            id=m.id,
            numero_cargo=m.cargo.numero_cargo,
            tipo_movimiento=m.tipo_movimiento,
            monto=float(m.monto),
            fecha_movimiento=m.fecha_movimiento
        ) for m in movimientos
    ]

    return DetalleCliente360Response(
        id=cliente.id,
        codigo_cliente_belcor=cliente.codigo_cliente_belcor,
        nombre_completo=cliente.nombre_completo,
        numero_documento=cliente.numero_documento,
        correo_electronico=cliente.correo_electronico,
        departamento=cliente.departamento.nombre if cliente.departamento else None,
        seccion=cliente.seccion.nombre if cliente.seccion else None,
        perfil_riesgo=cliente.perfil_riesgo.nombre if cliente.perfil_riesgo else None,
        segmento_rolling=cliente.segmento_rolling.nombre if cliente.segmento_rolling else None,
        telefonos=[TelefonoClienteDetalle.model_validate(t) for t in telefonos],
        cargos=cargos_res,
        movimientos=movimientos_res
    )

@router.put("/cargos/{cargo_id}/deshabilitar")
def deshabilitar_cargo(
    cargo_id: int,
    body: DeshabilitarCargoRequest,
    db: Session = Depends(obtener_db),
    usuario_actual: Usuario = Depends(verificar_permiso(modulo_interno="clientes", nivel_requerido=3))
):
    """
    Inhabilita un cargo (Soft-Delete) conservándolo en la base de datos para auditoría,
    excluyéndolo de métricas y cobros previa verificación de contraseña.
    Requiere Permiso: clientes - Nivel 3.
    """
    cargo = db.query(Cargo).filter(Cargo.id == cargo_id).first()
    if not cargo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El cargo especificado no existe."
        )
    
    motivo = body.motivo.strip() if body.motivo else ""
    if not motivo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Es obligatorio indicar el motivo de la inhabilitación del cargo."
        )

    # REGLA DE SEGURIDAD JAIRO: Verificación obligatoria de la contraseña del usuario logueado
    if not body.password or not SecurityService.verificar_password(body.password, usuario_actual.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña ingresada es incorrecta. No se puede inhabilitar el cargo."
        )

    cargo.activo = False
    cargo.motivo_deshabilitacion = motivo
    cargo.fecha_deshabilitacion = datetime.now(timezone.utc)
    cargo.usuario_deshabilitacion_id = usuario_actual.id
    cargo.estado = "DESHABILITADO"

    db.commit()
    db.refresh(cargo)

    return {"mensaje": f"El cargo {cargo.numero_cargo} ha sido inhabilitado correctamente."}

@router.put("/cargos/{cargo_id}/reactivar")
def reactivar_cargo(
    cargo_id: int,
    db: Session = Depends(obtener_db),
    _usuario: Usuario = Depends(verificar_permiso(modulo_interno="clientes", nivel_requerido=3))
):
    """
    Vuelve a habilitar un cargo que fue inhabilitado previamente.
    Requiere Permiso: clientes - Nivel 3.
    """
    cargo = db.query(Cargo).filter(Cargo.id == cargo_id).first()
    if not cargo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El cargo especificado no existe."
        )

    cargo.activo = True
    cargo.motivo_deshabilitacion = None
    cargo.fecha_deshabilitacion = None
    cargo.usuario_deshabilitacion_id = None

    # Recalcular estado operativo
    today = date.today()
    if float(cargo.saldo_cobrar) <= 1.00:
        cargo.estado = "PAGADO"
    elif cargo.fecha_cierre and cargo.fecha_cierre < today:
        cargo.estado = "VENCIDO"
    else:
        cargo.estado = "ACTIVO"

    db.commit()
    db.refresh(cargo)

    return {"mensaje": f"El cargo {cargo.numero_cargo} ha sido reactivado exitosamente."}

@router.get("/campanas", response_model=List[dict])
def listar_todas_campanas(
    db: Session = Depends(obtener_db),
    _usuario: Usuario = Depends(verificar_permiso(modulo_interno="clientes", nivel_requerido=1))
):
    """
    Retorna la lista de todas las campañas registradas en el sistema para los filtros.
    """
    campanas = db.query(Campana).order_by(Campana.nombre.desc()).all()
    return [{"id": c.id, "nombre": c.nombre} for c in campanas]
