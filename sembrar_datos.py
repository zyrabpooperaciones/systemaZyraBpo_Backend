from app.core.database import SessionLocal
from app.models.auth import Rol, Modulo, RolModuloNivel
from app.models.cobranzas import (
    Tramo, MapeoColumnasTramo, ConfiguracionPrioridadTelefonos
)

def sembrar_tramos_y_mapeos(db):
    print("====================================================")
    print("INICIANDO SEMBRADO DE TRAMOS Y CONFIGURACIONES")
    print("====================================================")
    
    # 1. Sembrar el tramo CE1 únicamente
    nombre_tramo = "CE1"
    tramo = db.query(Tramo).filter(Tramo.nombre == nombre_tramo).first()
    if not tramo:
        tramo = Tramo(nombre=nombre_tramo, activo=True)
        db.add(tramo)
        db.flush()
        print(f"[SEMILLA] Tramo '{nombre_tramo}' creado.")
    else:
        print(f"[EXISTE] El tramo '{nombre_tramo}' ya está registrado.")

    # 2. Sembrar catálogo de columnas y teléfonos para CE1
    columnas_ce1 = [
        # Grupo 1: Datos
        {"tipo_campo": "DATO", "campo_sistema": "codigo_cliente", "nombre_columna_excel": "Codigo Cliente", "es_obligatorio": True},
        {"tipo_campo": "DATO", "campo_sistema": "numero_cargo", "nombre_columna_excel": "Numero de Cargo", "es_obligatorio": True},
        {"tipo_campo": "DATO", "campo_sistema": "nombre_completo", "nombre_columna_excel": "Nombre completo", "es_obligatorio": True},
        {"tipo_campo": "DATO", "campo_sistema": "departamento", "nombre_columna_excel": "Departamento", "es_obligatorio": False},
        {"tipo_campo": "DATO", "campo_sistema": "seccion", "nombre_columna_excel": "Seccion", "es_obligatorio": False},
        {"tipo_campo": "DATO", "campo_sistema": "perfil_riesgo", "nombre_columna_excel": "Perfil Riesgo", "es_obligatorio": False},
        {"tipo_campo": "DATO", "campo_sistema": "segmento_rolling", "nombre_columna_excel": "Segmento Rolling", "es_obligatorio": False},
        {"tipo_campo": "DATO", "campo_sistema": "fecha_cierre", "nombre_columna_excel": "Fecha Cierre", "es_obligatorio": False},
        {"tipo_campo": "DATO", "campo_sistema": "numero_documento", "nombre_columna_excel": "Numero Documento", "es_obligatorio": False},
        {"tipo_campo": "DATO", "campo_sistema": "dias_atraso", "nombre_columna_excel": "Dias de Atraso", "es_obligatorio": False},
        {"tipo_campo": "DATO", "campo_sistema": "correo_electronico", "nombre_columna_excel": "Correo Electronico", "es_obligatorio": False},
        {"tipo_campo": "DATO", "campo_sistema": "campana", "nombre_columna_excel": "Campana", "es_obligatorio": True},
        {"tipo_campo": "DATO", "campo_sistema": "observacion", "nombre_columna_excel": "Observacion", "es_obligatorio": False},
        {"tipo_campo": "DATO", "campo_sistema": "fecha_pago", "nombre_columna_excel": "Fecha Pago", "es_obligatorio": False},
        # Grupo 2: Montos
        {"tipo_campo": "MONTO", "campo_sistema": "INICIAL", "nombre_columna_excel": "Importe deuda asignada", "es_obligatorio": True},
        {"tipo_campo": "MONTO", "campo_sistema": "INTERES", "nombre_columna_excel": "Interes", "es_obligatorio": False},
        {"tipo_campo": "MONTO", "campo_sistema": "GASTO_ADM", "nombre_columna_excel": "Gasto Administrativo", "es_obligatorio": False},
        {"tipo_campo": "MONTO", "campo_sistema": "PAGO", "nombre_columna_excel": "Importe de Abonos anteriores", "es_obligatorio": False},
    ]

    telefonos_ce1 = [
        {"nombre_columna_excel": "Telefono Movil", "prioridad": 1},
        {"nombre_columna_excel": "Telefono Fijo", "prioridad": 2},
        {"nombre_columna_excel": "Telefono Trabajo", "prioridad": 3},
        {"nombre_columna_excel": "Telefono Movil Cobranzas", "prioridad": 4},
        {"nombre_columna_excel": "Telefono Fijo Cobranzas", "prioridad": 5},
        {"nombre_columna_excel": "Telefono Trabajo Cobranzas", "prioridad": 6},
        {"nombre_columna_excel": "Telefono Ref. Fam.", "prioridad": 7},
        {"nombre_columna_excel": "Telefono Ref. No Fam.", "prioridad": 8},
        {"nombre_columna_excel": "Telefono Ref. Aval", "prioridad": 9},
        {"nombre_columna_excel": "Telf. Casa Recomendante", "prioridad": 10},
        {"nombre_columna_excel": "Telf. Celular Recomendante", "prioridad": 11},
        {"nombre_columna_excel": "Telf. Trabajo Recomendante", "prioridad": 12},
    ]

    for col_info in columnas_ce1:
        columna = db.query(MapeoColumnasTramo).filter(
            MapeoColumnasTramo.tramo_id == tramo.id,
            MapeoColumnasTramo.campo_sistema == col_info["campo_sistema"]
        ).first()
        if not columna:
            columna = MapeoColumnasTramo(
                tramo_id=tramo.id,
                tipo_campo=col_info["tipo_campo"],
                campo_sistema=col_info["campo_sistema"],
                nombre_columna_excel=col_info["nombre_columna_excel"],
                es_obligatorio=col_info["es_obligatorio"],
                activo=True
            )
            db.add(columna)
            db.flush()
            print(f"[SEMILLA] Columna '{col_info['campo_sistema']}' creada para CE1.")
        else:
            if columna.es_obligatorio != col_info["es_obligatorio"]:
                columna.es_obligatorio = col_info["es_obligatorio"]
                print(f"[SEMILLA] Columna '{col_info['campo_sistema']}' actualizada a es_obligatorio={col_info['es_obligatorio']}.")
            else:
                print(f"[EXISTE] La columna '{col_info['campo_sistema']}' ya existe para CE1.")

    for tel_info in telefonos_ce1:
        telefono = db.query(ConfiguracionPrioridadTelefonos).filter(
            ConfiguracionPrioridadTelefonos.tramo_id == tramo.id,
            ConfiguracionPrioridadTelefonos.nombre_columna_excel == tel_info["nombre_columna_excel"]
        ).first()
        if not telefono:
            telefono = ConfiguracionPrioridadTelefonos(
                tramo_id=tramo.id,
                nombre_columna_excel=tel_info["nombre_columna_excel"],
                prioridad=tel_info["prioridad"],
                activo=True
            )
            db.add(telefono)
            db.flush()
            print(f"[SEMILLA] Teléfono '{tel_info['nombre_columna_excel']}' creado para CE1.")
        else:
            print(f"[EXISTE] El teléfono '{tel_info['nombre_columna_excel']}' ya existe para CE1.")


def sembrar_datos_produccion():
    print("====================================================")
    print("INICIANDO SEMBRADO SEGURO DE DATOS (PRODUCCIÓN)")
    print("====================================================")
    
    db = SessionLocal()
    try:
        # 1. Sembrar/Verificar Rol Administrador
        rol_admin = db.query(Rol).filter(Rol.nombre == "Administrador").first()
        if not rol_admin:
            rol_admin = Rol(
                nombre="Administrador", 
                descripcion="Acceso total y configuración de seguridad."
            )
            db.add(rol_admin)
            db.flush()
            print(f"[SEMILLA] Rol '{rol_admin.nombre}' creado.")
        else:
            print(f"[EXISTE] El rol '{rol_admin.nombre}' ya está registrado.")

        # 2. Módulos oficiales a verificar/crear
        modulos_a_verificar = [
            {
                "nombre_interno": "usuarios",
                "nombre_pantalla": "Gestionar Usuarios",
                "descripcion": "Administración de cuentas de usuario y perfiles del personal."
            },
            {
                "nombre_interno": "roles",
                "nombre_pantalla": "Gestionar Roles",
                "descripcion": "Configuración de roles y asignación de permisos de acceso."
            },
            {
                "nombre_interno": "volcados",
                "nombre_pantalla": "Generar Volcados",
                "descripcion": "Generación, visualización y descarga de volcados de datos."
            },
            {
                "nombre_interno": "configuracion_tramos",
                "nombre_pantalla": "Configurar Tramos",
                "descripcion": "Gestión de tramos, catálogo de columnas e inventario de prioridades de teléfonos."
            },
            {
                "nombre_interno": "importacion",
                "nombre_pantalla": "Subida de Bases",
                "descripcion": "Carga inicial, actualización y saldos de carteras mediante archivos Excel."
            },
            {
                "nombre_interno": "descuentos",
                "nombre_pantalla": "Campañas de Descuentos",
                "descripcion": "Gestión de descuentos temporales condonados por tramo y filtros de segmentación."
            }
        ]

        # 3. Crear módulos nuevos o actualizar existentes
        modulos_db = []
        for m_info in modulos_a_verificar:
            modulo = db.query(Modulo).filter(Modulo.nombre_interno == m_info["nombre_interno"]).first()
            if not modulo:
                modulo = Modulo(
                    nombre_interno=m_info["nombre_interno"],
                    nombre_pantalla=m_info["nombre_pantalla"],
                    descripcion=m_info["descripcion"]
                )
                db.add(modulo)
                db.flush()
                print(f"[SEMILLA] Módulo nuevo creado: {modulo.nombre_pantalla}")
            else:
                if modulo.nombre_pantalla != m_info["nombre_pantalla"] or modulo.descripcion != m_info["descripcion"]:
                    modulo.nombre_pantalla = m_info["nombre_pantalla"]
                    modulo.descripcion = m_info["descripcion"]
                    print(f"[SEMILLA] Módulo '{modulo.nombre_interno}' actualizado a '{modulo.nombre_pantalla}'.")
                else:
                    print(f"[EXISTE] El módulo '{modulo.nombre_pantalla}' ya está registrado.")
            modulos_db.append(modulo)

        # 4. Asegurar permisos Nivel 3 para el Administrador en todos estos módulos
        for modulo in modulos_db:
            permiso = db.query(RolModuloNivel).filter(
                RolModuloNivel.rol_id == rol_admin.id,
                RolModuloNivel.modulo_id == modulo.id
            ).first()

            if not permiso:
                permiso = RolModuloNivel(
                    rol_id=rol_admin.id,
                    modulo_id=modulo.id,
                    nivel_acceso=3  # Nivel 3: Acceso total
                )
                db.add(permiso)
                print(f"[PERMISO] Nivel 3 asignado al Administrador en: {modulo.nombre_pantalla}")
            else:
                if permiso.nivel_acceso != 3:
                    permiso.nivel_acceso = 3
                    print(f"[PERMISO] Nivel de acceso actualizado a 3 para Administrador en: {modulo.nombre_pantalla}")
                else:
                    print(f"[PERMISO] El Administrador ya cuenta con Nivel 3 en: {modulo.nombre_pantalla}")

        # 5. Sembrar tramos, catálogo de columnas y teléfonos (solo CE1 sin plantillas de mapeo)
        sembrar_tramos_y_mapeos(db)

        db.commit()
        print("====================================================")
        print("¡Proceso de sembrado seguro completado con éxito!")
        print("====================================================")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Ocurrió un fallo al sembrar los datos: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    sembrar_datos_produccion()
