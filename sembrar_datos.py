from app.core.database import SessionLocal
from app.models.auth import Rol, Modulo, RolModuloNivel

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
            }
        ]

        # 3. Crear módulos nuevos (sin borrar los existentes)
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
