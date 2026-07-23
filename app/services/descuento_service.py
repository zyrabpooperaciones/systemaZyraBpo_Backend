from sqlalchemy.orm import Session
from app.models.cobranzas import Cargo, DescuentoConfig

def calcular_descuento_cargo(cargo: Cargo, db: Session) -> float:
    """
    Busca las campañas de descuento activas del tramo y calcula el descuento
    aplicable para el deudor según las reglas de segmentación y montos.
    Aplica una limitación de seguridad para que el descuento no supere el saldo a cobrar actual.
    """
    from datetime import date
    # Los descuentos dinámicos solo se calculan y aplican para deudas en estado ACTIVO y que no hayan vencido su fecha de cierre
    if cargo.estado != "ACTIVO" or (cargo.fecha_cierre and cargo.fecha_cierre < date.today()):
        return 0.0

    # 1. Buscar descuentos activos para este tramo, ordenados por creación descendente (prioriza el más nuevo)
    descuentos_activos = db.query(DescuentoConfig).filter(
        DescuentoConfig.tramo_id == cargo.tramo_id,
        DescuentoConfig.activo == True
    ).order_by(DescuentoConfig.created_at.desc()).all()

    if not descuentos_activos:
        return 0.0

    cliente = cargo.cliente
    # Extraer nombres para comparar con filtros
    campana_nombre = cargo.campana.nombre if cargo.campana else ""
    depto_nombre = cliente.departamento.nombre if cliente and cliente.departamento else ""
    perfil_nombre = cliente.perfil_riesgo.nombre if cliente and cliente.perfil_riesgo else ""
    rolling_nombre = cliente.segmento_rolling.nombre if cliente and cliente.segmento_rolling else ""

    for desc in descuentos_activos:
        # Validar Filtro de Campañas (Si hay elementos en el filtro y la campaña del cliente no coincide)
        if desc.campanas and isinstance(desc.campanas, list):
            if campana_nombre not in desc.campanas:
                continue
                
        # Validar Filtro de Departamentos
        if desc.departamentos and isinstance(desc.departamentos, list):
            if depto_nombre not in desc.departamentos:
                continue
                
        # Validar Filtro de Perfiles de Riesgo
        if desc.perfiles_riesgo and isinstance(desc.perfiles_riesgo, list):
            if perfil_nombre not in desc.perfiles_riesgo:
                continue
                
        # Validar Filtro de Segmentos Rolling
        if desc.segmentos_rolling and isinstance(desc.segmentos_rolling, list):
            if rolling_nombre not in desc.segmentos_rolling:
                continue

        # Si supera todos los filtros, este descuento aplica
        desc_calculado = 0.0
        
        # Calcular porcentaje sobre capital inicial
        if desc.pct_descuento_capital > 0:
            desc_calculado += float(cargo.monto_inicial) * (float(desc.pct_descuento_capital) / 100.0)
            
        # Calcular porcentaje sobre intereses
        if desc.pct_descuento_interes > 0:
            desc_calculado += float(cargo.monto_interes) * (float(desc.pct_descuento_interes) / 100.0)
            
        # Calcular porcentaje sobre gastos administrativos
        if desc.pct_descuento_gasto > 0:
            desc_calculado += float(cargo.monto_gasto_adm) * (float(desc.pct_descuento_gasto) / 100.0)
            
        # Sumar el descuento de monto fijo
        desc_calculado += float(desc.descuento_monto_fijo)

        # Límite de seguridad: el descuento no puede superar el saldo actual a cobrar de la deuda
        saldo_actual = float(cargo.saldo_cobrar)
        desc_final = min(desc_calculado, saldo_actual)
        
        return round(max(desc_final, 0.0), 2)

    return 0.0
