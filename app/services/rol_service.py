from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.auth import Rol, Modulo, RolModuloNivel, Perfil, Usuario
from app.schemas.roles import RolCreate, RolUpdate, RolPermisosUpdate

class RolService:

    @staticmethod
    def listar_roles(db: Session) -> list[Rol]:
        return db.query(Rol).order_by(Rol.id).all()

    @staticmethod
    def crear_rol(db: Session, datos: RolCreate) -> Rol:
        # Verificar si ya existe un rol con el mismo nombre
        rol_existente = db.query(Rol).filter(Rol.nombre == datos.nombre).first()
        if rol_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un rol con el nombre '{datos.nombre}'."
            )
        
        nuevo_rol = Rol(nombre=datos.nombre, descripcion=datos.descripcion)
        db.add(nuevo_rol)
        db.commit()
        db.refresh(nuevo_rol)
        return nuevo_rol

    @staticmethod
    def actualizar_rol(db: Session, rol_id: int, datos: RolUpdate) -> Rol:
        rol = db.query(Rol).filter(Rol.id == rol_id).first()
        if not rol:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rol no encontrado."
            )
        
        # Verificar si intenta cambiar el nombre a uno ya existente
        rol_nombre = db.query(Rol).filter(Rol.nombre == datos.nombre, Rol.id != rol_id).first()
        if rol_nombre:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe otro rol con el nombre '{datos.nombre}'."
            )

        rol.nombre = datos.nombre
        rol.descripcion = datos.descripcion
        
        # Actualizar cargos de todos los perfiles de usuario que tengan este rol
        db.query(Perfil).filter(
            Perfil.usuario_id.in_(
                db.query(Usuario.id).filter(Usuario.rol_id == rol_id)
            )
        ).update({Perfil.cargo: datos.nombre}, synchronize_session=False)

        db.commit()
        db.refresh(rol)
        return rol

    @staticmethod
    def eliminar_rol(db: Session, rol_id: int) -> dict:
        rol = db.query(Rol).filter(Rol.id == rol_id).first()
        if not rol:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rol no encontrado."
            )
        
        # Evitar eliminar el rol Administrador del sistema por seguridad
        if rol.nombre == "Administrador":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rol 'Administrador' es del sistema y no puede ser eliminado."
            )

        try:
            db.delete(rol)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar el rol porque tiene usuarios asociados."
            )
        
        return {
            "status": "success",
            "mensaje": "Rol eliminado correctamente 🎉"
        }

    @staticmethod
    def listar_modulos(db: Session) -> list[Modulo]:
        return db.query(Modulo).order_by(Modulo.id).all()

    @staticmethod
    def obtener_permisos_rol(db: Session, rol_id: int) -> list[dict]:
        rol = db.query(Rol).filter(Rol.id == rol_id).first()
        if not rol:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rol no encontrado."
            )

        modulos = db.query(Modulo).order_by(Modulo.id).all()
        permisos = db.query(RolModuloNivel).filter(RolModuloNivel.rol_id == rol_id).all()
        
        permisos_map = {p.modulo_id: p.nivel_acceso for p in permisos}

        resultado = []
        for m in modulos:
            resultado.append({
                "modulo_id": m.id,
                "nombre_interno": m.nombre_interno,
                "nombre_pantalla": m.nombre_pantalla,
                "nivel_acceso": permisos_map.get(m.id, 0) # Si no hay permiso asignado, el nivel es 0
            })
        
        return resultado

    @staticmethod
    def actualizar_permisos_rol(db: Session, rol_id: int, datos_permisos: RolPermisosUpdate) -> dict:
        rol = db.query(Rol).filter(Rol.id == rol_id).first()
        if not rol:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rol no encontrado."
            )

        for p_update in datos_permisos.permisos:
            modulo = db.query(Modulo).filter(Modulo.id == p_update.modulo_id).first()
            if not modulo:
                continue

            permiso = db.query(RolModuloNivel).filter(
                RolModuloNivel.rol_id == rol_id,
                RolModuloNivel.modulo_id == p_update.modulo_id
            ).first()

            if p_update.nivel_acceso == 0:
                # Nivel 0 significa eliminar el permiso de la base de datos (sin acceso)
                if permiso:
                    db.delete(permiso)
            else:
                # Niveles 1, 2 y 3 crean o actualizan el registro
                if permiso:
                    permiso.nivel_acceso = p_update.nivel_acceso
                else:
                    nuevo_permiso = RolModuloNivel(
                        rol_id=rol_id,
                        modulo_id=p_update.modulo_id,
                        nivel_acceso=p_update.nivel_acceso
                    )
                    db.add(nuevo_permiso)
        
        db.commit()
        return {
            "status": "success",
            "mensaje": "Permisos actualizados correctamente 🎉"
        }
