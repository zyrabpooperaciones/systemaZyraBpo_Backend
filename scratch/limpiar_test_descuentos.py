import sys
import os

# Añadir ruta del backend al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.auth import Usuario
from app.models.cobranzas import Cargo, MovimientoCargo, DescuentoConfig

def limpiar():
    db = SessionLocal()
    print("====================================================")
    print("LIMPIANDO REGISTROS DE PRUEBA COMPROMETIDOS")
    print("====================================================")

    try:
        # 1. Eliminar los descuentos de prueba
        num_deleted_desc = db.query(DescuentoConfig).filter(
            DescuentoConfig.nombre.like("%TEST DESC%")
        ).delete(synchronize_session=False)
        print(f"[OK] {num_deleted_desc} Campañas de descuento de prueba eliminadas.")

        # 2. Buscar el cargo específico del test
        cargo = db.query(Cargo).filter(Cargo.numero_cargo == "15157578").first()
        if cargo:
            print(f"[INFO] Cargo #{cargo.numero_cargo} encontrado.")
            # Borrar todos los pagos y descuentos asociados a este cargo para restaurar su saldo
            num_deleted_movs = db.query(MovimientoCargo).filter(
                MovimientoCargo.cargo_id == cargo.id,
                MovimientoCargo.tipo_movimiento.in_(["PAGO", "DESCUENTO"])
            ).delete(synchronize_session=False)
            print(f"[OK] {num_deleted_movs} movimientos (PAGO/DESCUENTO) eliminados para el cargo #{cargo.numero_cargo}.")

            db.commit()
            db.refresh(cargo)
            print(f"[INFO] Cargo #{cargo.numero_cargo} restaurado: Saldo={cargo.saldo_cobrar} BOB, Estado={cargo.estado}")
        else:
            print("[INFO] El cargo #15157578 no existe.")
            db.commit()

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error al limpiar: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    limpiar()
