from app.core.database import SessionLocal
from app.models.auth import Rol, Usuario, Perfil, Modulo, RolModuloNivel
from app.services.security import SecurityService

def crear_usuario_administrador():
    print("====================================================")
    print("INICIANDO CREACIÓN SEGURA DE USUARIO ADMINISTRADOR")
    print("====================================================")
    
    db = SessionLocal()
    try:
        # 1. Asegurar la existencia del rol Administrador
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

        # 2. Verificar si el usuario administrador ya existe
        email_admin = "zyrabpooperaciones@gmail.com"
        password_plana = "jairozyra"
        
        usuario = db.query(Usuario).filter(Usuario.email == email_admin).first()
        if not usuario:
            # Encriptar la contraseña de forma segura
            password_encriptada = SecurityService.generar_hash(password_plana)
            
            nuevo_usuario = Usuario(
                rol_id=rol_admin.id,
                email=email_admin,
                password_hash=password_encriptada,
                estado="ACTIVO"
            )
            db.add(nuevo_usuario)
            db.flush()
            print(f"[USUARIO] Cuenta creada: {email_admin}")
            
            # Crear perfil humano asociado
            nuevo_perfil = Perfil(
                usuario_id=nuevo_usuario.id,
                ci="14411573",
                nombre="Jairo Lisandro",
                apellido="Camacho Jimenez",
                telefono="72601562",
                cargo=rol_admin.nombre
            )
            db.add(nuevo_perfil)
            print(f"[PERFIL] Perfil humano registrado para: {nuevo_perfil.nombre} {nuevo_perfil.apellido}")
        else:
            print(f"[EXISTE] El usuario '{email_admin}' ya se encuentra registrado en el sistema.")

        # 3. Asegurar permisos de Nivel 3 para el Administrador en todos los módulos existentes
        modulos = db.query(Modulo).all()
        for m in modulos:
            permiso = db.query(RolModuloNivel).filter(
                RolModuloNivel.rol_id == rol_admin.id,
                RolModuloNivel.modulo_id == m.id
            ).first()
            
            if not permiso:
                permiso = RolModuloNivel(
                    rol_id=rol_admin.id,
                    modulo_id=m.id,
                    nivel_acceso=3
                )
                db.add(permiso)
                print(f"[PERMISO] Nivel 3 asignado al Administrador en: {m.nombre_pantalla}")
            else:
                if permiso.nivel_acceso != 3:
                    permiso.nivel_acceso = 3
                    db.commit()
                    print(f"[PERMISO] Nivel actualizado a 3 para Administrador en: {m.nombre_pantalla}")
        
        db.commit()
        print("====================================================")
        print("¡Proceso de creación de Administrador completado!")
        print(f"Correo:      {email_admin}")
        print(f"Contraseña:  {password_plana}")
        print("====================================================")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Ocurrió un fallo al crear el Administrador: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    crear_usuario_administrador()
