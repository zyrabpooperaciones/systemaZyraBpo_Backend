from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.auth import Usuario, Perfil, Rol
from app.services.security import SecurityService
from app.schemas.usuarios import UsuarioCreate, UsuarioUpdate

class UsuarioService:

    @staticmethod
    def listar_usuarios(db: Session) -> list[dict]:
        usuarios_db = db.query(Usuario).join(Rol).outerjoin(Perfil).order_by(Usuario.id).all()
        
        resultado = []
        for u in usuarios_db:
            resultado.append({
                "id": u.id,
                "email": u.email,
                "estado": u.estado,
                "rol_id": u.rol_id,
                "rol_nombre": u.rol.nombre,
                "nombre": u.perfil.nombre if u.perfil else "",
                "apellido": u.perfil.apellido if u.perfil else "",
                "ci": u.perfil.ci if u.perfil else "",
                "telefono": u.perfil.telefono if u.perfil else None,
                "cargo": u.perfil.cargo if u.perfil else ""
            })
        return resultado

    @staticmethod
    def crear_usuario(db: Session, datos: UsuarioCreate) -> dict:
        # 1. Verificar si el email ya existe
        email_existe = db.query(Usuario).filter(Usuario.email == datos.email).first()
        if email_existe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electronico ya esta registrado."
            )
        
        # 2. Verificar si el rol existe
        rol = db.query(Rol).filter(Rol.id == datos.rol_id).first()
        if not rol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rol especificado no existe."
            )
        
        # 3. Verificar si el CI ya existe
        ci_existe = db.query(Perfil).filter(Perfil.ci == datos.ci).first()
        if ci_existe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La cedula de identidad (CI) ya esta registrada."
            )
        
        # 4. Encriptar contraseña
        password_cifrada = SecurityService.generar_hash(datos.password)
        
        nuevo_usuario = Usuario(
            rol_id=datos.rol_id,
            email=datos.email,
            password_hash=password_cifrada,
            estado="ACTIVO"
        )
        db.add(nuevo_usuario)
        db.flush()  # Para obtener el id generado antes de asociar el perfil
        
        nuevo_perfil = Perfil(
            usuario_id=nuevo_usuario.id,
            ci=datos.ci,
            nombre=datos.nombre,
            apellido=datos.apellido,
            telefono=datos.telefono,
            cargo=rol.nombre
        )
        db.add(nuevo_perfil)
        db.commit()
        
        return {
            "id": nuevo_usuario.id,
            "email": nuevo_usuario.email,
            "estado": nuevo_usuario.estado,
            "rol_id": nuevo_usuario.rol_id,
            "rol_nombre": rol.nombre,
            "nombre": nuevo_perfil.nombre,
            "apellido": nuevo_perfil.apellido,
            "ci": nuevo_perfil.ci,
            "telefono": nuevo_perfil.telefono,
            "cargo": nuevo_perfil.cargo
        }

    @staticmethod
    def actualizar_usuario(db: Session, usuario_id: int, datos: UsuarioUpdate) -> dict:
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado."
            )
        
        # Verificar email duplicado
        email_duplicado = db.query(Usuario).filter(Usuario.email == datos.email, Usuario.id != usuario_id).first()
        if email_duplicado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electronico ya esta registrado por otro usuario."
            )
        
        # Verificar rol
        rol = db.query(Rol).filter(Rol.id == datos.rol_id).first()
        if not rol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rol especificado no existe."
            )
        
        # Verificar CI duplicado
        ci_duplicado = db.query(Perfil).filter(Perfil.ci == datos.ci, Perfil.usuario_id != usuario_id).first()
        if ci_duplicado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La cedula de identidad (CI) ya esta registrada por otro usuario."
            )
        
        # Actualizar campos
        usuario.email = datos.email
        usuario.rol_id = datos.rol_id
        usuario.estado = datos.estado
        
        if not usuario.perfil:
            usuario.perfil = Perfil(
                usuario_id=usuario_id,
                ci=datos.ci,
                nombre=datos.nombre,
                apellido=datos.apellido,
                telefono=datos.telefono,
                cargo=rol.nombre
            )
            db.add(usuario.perfil)
        else:
            usuario.perfil.ci = datos.ci
            usuario.perfil.nombre = datos.nombre
            usuario.perfil.apellido = datos.apellido
            usuario.perfil.telefono = datos.telefono
            usuario.perfil.cargo = rol.nombre
            
        db.commit()
        db.refresh(usuario)
        
        return {
            "id": usuario.id,
            "email": usuario.email,
            "estado": usuario.estado,
            "rol_id": usuario.rol_id,
            "rol_nombre": rol.nombre,
            "nombre": usuario.perfil.nombre,
            "apellido": usuario.perfil.apellido,
            "ci": usuario.perfil.ci,
            "telefono": usuario.perfil.telefono,
            "cargo": usuario.perfil.cargo
        }

    @staticmethod
    def eliminar_usuario(db: Session, usuario_id: int, usuario_actual_id: int) -> dict:
        if usuario_id == usuario_actual_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puede eliminarse a si mismo del sistema."
            )
            
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado."
            )
            
        usuario.estado = "INACTIVO"
        db.commit()
        return {
            "status": "success",
            "mensaje": "Usuario desactivado correctamente 🎉"
        }
