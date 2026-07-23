import sys
import os
from sqlalchemy import text

# Añadir ruta del backend al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal

def actualizar_trigger():
    db = SessionLocal()
    print("====================================================")
    print("ACTUALIZANDO TRIGGER EN POSTGRESQL")
    print("====================================================")

    sql_function = """
    CREATE OR REPLACE FUNCTION fn_actualizar_saldos_cargo()
    RETURNS TRIGGER AS $$
    DECLARE
        target_cargo_id BIGINT;
        calc_saldo NUMERIC(12, 2);
        calc_deuda NUMERIC(12, 2);
        v_fecha_cierre DATE;
    BEGIN
        IF TG_OP = 'DELETE' THEN
            target_cargo_id := OLD.cargo_id;
        ELSE
            target_cargo_id := NEW.cargo_id;
        END IF;

        -- 1. Actualizar sumas de movimientos
        UPDATE cargos
        SET 
            monto_inicial = COALESCE((SELECT SUM(monto) FROM movimientos_cargos WHERE cargo_id = target_cargo_id AND tipo_movimiento = 'INICIAL'), 0.00),
            monto_interes = COALESCE((SELECT SUM(monto) FROM movimientos_cargos WHERE cargo_id = target_cargo_id AND tipo_movimiento = 'INTERES'), 0.00),
            monto_gasto_adm = COALESCE((SELECT SUM(monto) FROM movimientos_cargos WHERE cargo_id = target_cargo_id AND tipo_movimiento = 'GASTO_ADM'), 0.00),
            monto_pagado = COALESCE((SELECT SUM(monto) FROM movimientos_cargos WHERE cargo_id = target_cargo_id AND tipo_movimiento = 'PAGO'), 0.00),
            monto_descontar = COALESCE((SELECT SUM(monto) FROM movimientos_cargos WHERE cargo_id = target_cargo_id AND tipo_movimiento = 'DESCUENTO'), 0.00)
        WHERE id = target_cargo_id;
        
        -- 2. Calcular saldos y fecha de cierre
        SELECT 
            (monto_inicial + monto_interes + monto_gasto_adm),
            ((monto_inicial + monto_interes + monto_gasto_adm) - monto_pagado - monto_descontar),
            fecha_cierre
        INTO calc_deuda, calc_saldo, v_fecha_cierre
        FROM cargos WHERE id = target_cargo_id;

        -- 3. Actualizar deuda, saldo y estado en un solo paso
        UPDATE cargos
        SET
            deuda_total = calc_deuda,
            saldo_cobrar = calc_saldo,
            estado = CASE
                WHEN calc_saldo <= 0.05 THEN 'PAGADO'
                WHEN v_fecha_cierre IS NOT NULL AND v_fecha_cierre < CURRENT_DATE THEN 'VENCIDO'
                ELSE 'ACTIVO'
            END
        WHERE id = target_cargo_id;

        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """

    try:
        db.execute(text(sql_function))
        db.commit()
        print("[OK] Función del trigger fn_actualizar_saldos_cargo actualizada correctamente.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] No se pudo actualizar el trigger: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    actualizar_trigger()
