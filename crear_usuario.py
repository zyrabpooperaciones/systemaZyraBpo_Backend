from app.core.database import SessionLocal
from app.models.auth import Usuario, Perfil, Rol
from app.services.security import SecurityService

def sembrar_primer_usuario():
    # 1. Abrimos la sesión con la base de datos
    db = SessionLocal()
    try:
        # 2. Buscamos el ID del rol 'Administrador' que sembramos en pgAdmin
        rol_admin = db.query(Rol).filter(Rol.nombre == "Administrador").first()
        if not rol_admin:
            print("❌ Error: No se encontró el rol 'Administrador' en la base de datos. ¿Ejecutaste la data semilla?")
            return

        # 3. Verificamos si el usuario ya existe para no duplicarlo
        email_test = "jairo@zyrabpo.com"
        usuario_existe = db.query(Usuario).filter(Usuario.email == email_test).first()
        if usuario_existe:
            print(f"⚠️ El usuario {email_test} ya existe en el sistema.")
            return

        # 4. Encriptamos la contraseña usando nuestro servicio seguro
        password_plana = "zyra2026"  # Esta será tu clave de acceso temporal
        password_encriptada = SecurityService.generar_hash(password_plana)

        # 5. Creamos el objeto del Usuario (Capa de Autenticación)
        nuevo_usuario = Usuario(
            rol_id=rol_admin.id,
            email=email_test,
            password_hash=password_encriptada,
            estado="ACTIVO"
        )
        db.add(nuevo_usuario)
        db.flush() # Guardamos momentáneamente para obtener el ID generado

        # 6. Creamos el Perfil Humano asociado a ese usuario
        nuevo_perfil = Perfil(
            usuario_id=nuevo_usuario.id,
            ci="14411573",
            nombre="Jairo Lisandro",
            apellido="Camacho Jimenez",
            telefono="72601562",
            cargo=rol_admin.nombre
        )
        db.add(nuevo_perfil)
        
        # 7. Sellar la transacción en Postgres
        db.commit()
        print("====================================================")
        print("🚀 ¡Usuario Administrador creado con éxito absoluto!")
        print(f"📧 Correo: {email_test}")
        print(f"🔑 Contraseña: {password_plana}")
        print("====================================================")

    except Exception as e:
        db.rollback() # Si algo falla, deshacemos los cambios para no romper la BD
        print(f"❌ Ocurrió un error al crear el usuario: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    sembrar_primer_usuario()