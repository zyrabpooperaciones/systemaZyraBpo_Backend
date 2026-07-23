import sys
import os

# Añadir ruta del backend al path para importar módulos correctamente
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.auth import Usuario  # Asegura la resolución de la relación en HistorialImportacion
from app.models.cobranzas import Cargo, Cliente, MovimientoCargo, DescuentoConfig, Tramo, Campana
from app.services.descuento_service import calcular_descuento_cargo

def test_descuentos_reglas():
    db: Session = SessionLocal()
    print("====================================================")
    print("INICIANDO PRUEBAS UNITARIAS DE DESCUENTOS")
    print("====================================================")

    try:
        # 1. Buscar una cartera/tramo de prueba y un cliente activo
        tramo = db.query(Tramo).filter(Tramo.nombre == "CE1").first()
        if not tramo:
            print("[ERROR] No se encontró el tramo 'CE1'.")
            return

        cargo = db.query(Cargo).filter(Cargo.tramo_id == tramo.id, Cargo.estado == "ACTIVO").first()
        if not cargo:
            print("[ADVERTENCIA] No hay cargos 'ACTIVO' en el tramo CE1. Buscando cualquier cargo.")
            cargo = db.query(Cargo).filter(Cargo.tramo_id == tramo.id).first()
            if not cargo:
                print("[ERROR] No hay cargos en el tramo 'CE1'. Sube una base antes de correr esta prueba.")
                return

        print(f"[TEST INFO] Cliente seleccionado: {cargo.cliente.nombre_completo}")
        print(f"[TEST INFO] Cargo seleccionado: #{cargo.numero_cargo}")
        print(f"[TEST INFO] Campaña del cargo: {cargo.campana.nombre if cargo.campana else 'Ninguna'}")
        print(f"[TEST INFO] Departamento de deudor: {cargo.cliente.departamento.nombre if cargo.cliente.departamento else 'Ninguno'}")
        print(f"[TEST INFO] Deuda Actual (Saldo Cobrar): {cargo.saldo_cobrar} BOB")

        # Guardar valores originales para restaurar después
        saldo_original = float(cargo.saldo_cobrar)
        pagado_original = float(cargo.monto_pagado)

        # 2. CREAR DESCUENTO DE PRUEBA ACTIVO (100% sobre Intereses + 50 BOB fijo)
        campanas_filtro = [cargo.campana.nombre] if cargo.campana else []
        descuento_test = DescuentoConfig(
            tramo_id=tramo.id,
            nombre="TEST DESC 100% INT + 50 FIJO",
            descuento_monto_fijo=50.00,
            pct_descuento_capital=0.00,
            pct_descuento_interes=100.00,
            pct_descuento_gasto=0.00,
            campanas=campanas_filtro,
            departamentos=[],
            perfiles_riesgo=[],
            segmentos_rolling=[],
            activo=True
        )
        db.add(descuento_test)
        db.commit()
        db.refresh(descuento_test)
        print(f"\n[OK] Descuento de prueba registrado: ID={descuento_test.id}")

        # 3. EVALUAR CÁLCULO DINÁMICO
        desc_calculado = calcular_descuento_cargo(cargo, db)
        print(f"[EVAL] Descuento Dinámico Calculado: {desc_calculado} BOB")
        
        # El descuento esperado debe ser: 50.00 + 100% de los intereses del cargo
        interes_esperado = float(cargo.monto_interes)
        monto_esperado = min(50.0 + interes_esperado, float(cargo.saldo_cobrar))
        print(f"[EVAL] Descuento Esperado: {monto_esperado} BOB")
        
        assert abs(desc_calculado - monto_esperado) < 0.01, "El cálculo del descuento no coincide con la fórmula esperada."
        print("[OK] Prueba de Cálculo Dinámico de Descuento: EXITOSA")

        # 4. SIMULAR CONSOLIDACIÓN AL PAGAR SALDO NETO LIQUIDABLE
        saldo_neto_liq = float(cargo.saldo_cobrar) - desc_calculado
        print(f"\n[EVAL] Saldo Neto para Liquidar: {saldo_neto_liq} BOB")
        
        # Simulamos que ingresa un pago de exactamente el saldo neto liquidable
        diff_p = saldo_neto_liq
        print(f"[PAGO] Registrando pago simulación por {diff_p} BOB...")
        
        if desc_calculado > 0 and diff_p >= (saldo_neto_liq - 1.0):
            # Consolidar descuento en movimientos
            desc_final = max(min(desc_calculado, float(cargo.saldo_cobrar) - diff_p), 0.0)
            
            mov_pago = MovimientoCargo(
                cargo_id=cargo.id,
                tipo_movimiento="PAGO",
                monto=diff_p
            )
            db.add(mov_pago)
            
            if desc_final > 0:
                mov_desc = MovimientoCargo(
                    cargo_id=cargo.id,
                    tipo_movimiento="DESCUENTO",
                    monto=desc_final
                )
                db.add(mov_desc)
                print(f"[OK] Condonación automática consolidada en movimiento DESCUENTO por {desc_final} BOB")
        
        db.commit()
        db.refresh(cargo)
        
        print(f"\n[POST-PAGO] Nuevo Saldo Cobrar: {cargo.saldo_cobrar} BOB")
        print(f"[POST-PAGO] Estado de la Cuenta: {cargo.estado}")
        
        # Como pagamos el saldo liquidable + descuento condonado, el saldo a cobrar final debe ser 0.00
        assert float(cargo.saldo_cobrar) < 0.05, f"La cuenta debió liquidarse en 0.00, pero quedó en {cargo.saldo_cobrar}"
        assert cargo.estado == "PAGADO", f"La cuenta debió quedar en estado PAGADO, pero quedó en {cargo.estado}"
        print("[OK] Prueba de Consolidación y Condonación de Pago: EXITOSA")

    except AssertionError as ae:
        print(f"\n[ERROR DE ASERCIÓN]: {str(ae)}")
    except Exception as e:
        print(f"\n[ERROR INESPERADO]: {str(e)}")
    finally:
        # Siempre limpiar la base de datos de los datos de prueba
        print("\n[REVERSION] Limpiando datos de prueba...")
        try:
            # Eliminar movimientos simulados
            if 'cargo' in locals() and cargo is not None:
                db.query(MovimientoCargo).filter(
                    MovimientoCargo.cargo_id == cargo.id,
                    MovimientoCargo.tipo_movimiento.in_(["PAGO", "DESCUENTO"])
                ).delete(synchronize_session=False)
            
            # Eliminar descuento configurado
            if 'descuento_test' in locals() and descuento_test.id:
                db.query(DescuentoConfig).filter(DescuentoConfig.id == descuento_test.id).delete()
            
            db.commit()
            if 'cargo' in locals() and cargo is not None:
                db.refresh(cargo)
                print(f"[REVERSION] Saldo restablecido: {cargo.saldo_cobrar} BOB")
                print(f"[REVERSION] Estado restablecido: {cargo.estado}")
            print("\n====================================================")
            print("Proceso de validación de descuentos completado.")
            print("====================================================")
        except Exception as ex_limpiar:
            db.rollback()
            print(f"[ERROR CRÍTICO] No se pudo limpiar la base de datos en finally: {str(ex_limpiar)}")
        
        db.close()

if __name__ == "__main__":
    test_descuentos_reglas()
