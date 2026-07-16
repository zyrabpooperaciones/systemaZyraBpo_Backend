from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.cobranzas import (
    Tramo, MapeoColumnasTramo, ConfiguracionPrioridadTelefonos, PlantillaMapeo
)
from app.schemas.tramos import (
    MapeoColumnasTramoCreate,
    ConfiguracionPrioridadTelefonosCreate,
    PlantillaMapeoCreate,
    PlantillaAsociacionesUpdate
)

class TramoService:

    @staticmethod
    def listar_tramos(db: Session, ver_inactivos: bool = False) -> list[Tramo]:
        query = db.query(Tramo)
        if not ver_inactivos:
            query = query.filter(Tramo.activo == True)
        else:
            query = query.filter(Tramo.activo == False)
        return query.order_by(Tramo.nombre).all()

    @staticmethod
    def obtener_tramo(db: Session, tramo_id: int) -> Tramo:
        tramo = db.query(Tramo).filter(Tramo.id == tramo_id).first()
        if not tramo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tramo no encontrado."
            )
        return tramo

    @staticmethod
    def actualizar_estado_tramo(db: Session, tramo_id: int, activo: bool) -> Tramo:
        tramo = db.query(Tramo).filter(Tramo.id == tramo_id).first()
        if not tramo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tramo no encontrado."
            )
        tramo.activo = activo
        db.commit()
        db.refresh(tramo)
        return tramo

    @staticmethod
    def obtener_columnas_tramo(db: Session, tramo_id: int) -> list[MapeoColumnasTramo]:
        # Verificar existencia del tramo
        tramo = db.query(Tramo).filter(Tramo.id == tramo_id).first()
        if not tramo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tramo no encontrado."
            )
        return db.query(MapeoColumnasTramo).filter(MapeoColumnasTramo.tramo_id == tramo_id).all()

    @staticmethod
    def guardar_columnas_tramo(db: Session, tramo_id: int, columnas: list[MapeoColumnasTramoCreate]) -> list[MapeoColumnasTramo]:
        tramo = db.query(Tramo).filter(Tramo.id == tramo_id).first()
        if not tramo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tramo no encontrado."
            )

        resultado = []
        for col_info in columnas:
            columna = db.query(MapeoColumnasTramo).filter(
                MapeoColumnasTramo.tramo_id == tramo_id,
                MapeoColumnasTramo.campo_sistema == col_info.campo_sistema
            ).first()

            if columna:
                columna.nombre_columna_excel = col_info.nombre_columna_excel
                columna.es_obligatorio = col_info.es_obligatorio
                columna.activo = col_info.activo
            else:
                columna = MapeoColumnasTramo(
                    tramo_id=tramo_id,
                    tipo_campo=col_info.tipo_campo,
                    campo_sistema=col_info.campo_sistema,
                    nombre_columna_excel=col_info.nombre_columna_excel,
                    es_obligatorio=col_info.es_obligatorio,
                    activo=col_info.activo
                )
                db.add(columna)
            
            resultado.append(columna)

        db.commit()
        # Refrescar los objetos guardados
        for r in resultado:
            db.refresh(r)
        return resultado

    @staticmethod
    def obtener_telefonos_tramo(db: Session, tramo_id: int) -> list[ConfiguracionPrioridadTelefonos]:
        tramo = db.query(Tramo).filter(Tramo.id == tramo_id).first()
        if not tramo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tramo no encontrado."
            )
        return db.query(ConfiguracionPrioridadTelefonos).filter(
            ConfiguracionPrioridadTelefonos.tramo_id == tramo_id
        ).order_by(ConfiguracionPrioridadTelefonos.prioridad).all()

    @staticmethod
    def guardar_telefonos_tramo(db: Session, tramo_id: int, telefonos: list[ConfiguracionPrioridadTelefonosCreate]) -> list[ConfiguracionPrioridadTelefonos]:
        tramo = db.query(Tramo).filter(Tramo.id == tramo_id).first()
        if not tramo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tramo no encontrado."
            )

        resultado = []
        for tel_info in telefonos:
            telefono = None
            if tel_info.id:
                telefono = db.query(ConfiguracionPrioridadTelefonos).filter(
                    ConfiguracionPrioridadTelefonos.id == tel_info.id,
                    ConfiguracionPrioridadTelefonos.tramo_id == tramo_id
                ).first()
            
            if not telefono:
                # Buscar por nombre original si no hay ID o no se encontró por ID (ej. nuevo registro)
                telefono = db.query(ConfiguracionPrioridadTelefonos).filter(
                    ConfiguracionPrioridadTelefonos.tramo_id == tramo_id,
                    ConfiguracionPrioridadTelefonos.nombre_columna_excel == tel_info.nombre_columna_excel
                ).first()

            if telefono:
                telefono.nombre_columna_excel = tel_info.nombre_columna_excel
                telefono.prioridad = tel_info.prioridad
                telefono.activo = tel_info.activo
            else:
                telefono = ConfiguracionPrioridadTelefonos(
                    tramo_id=tramo_id,
                    nombre_columna_excel=tel_info.nombre_columna_excel,
                    prioridad=tel_info.prioridad,
                    activo=tel_info.activo
                )
                db.add(telefono)
            
            resultado.append(telefono)

        db.commit()
        for r in resultado:
            db.refresh(r)
        return resultado

    @staticmethod
    def listar_plantillas_tramo(db: Session, tramo_id: int) -> list[PlantillaMapeo]:
        tramo = db.query(Tramo).filter(Tramo.id == tramo_id).first()
        if not tramo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tramo no encontrado."
            )
        return db.query(PlantillaMapeo).filter(PlantillaMapeo.tramo_id == tramo_id).order_by(PlantillaMapeo.id).all()

    @staticmethod
    def crear_plantilla_tramo(db: Session, tramo_id: int, datos: PlantillaMapeoCreate) -> PlantillaMapeo:
        tramo = db.query(Tramo).filter(Tramo.id == tramo_id).first()
        if not tramo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tramo no encontrado."
            )

        # Verificar duplicidad de nombre
        plantilla_existente = db.query(PlantillaMapeo).filter(
            PlantillaMapeo.tramo_id == tramo_id,
            PlantillaMapeo.nombre == datos.nombre
        ).first()

        if plantilla_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una plantilla llamada '{datos.nombre}' para este tramo."
            )

        nueva_plantilla = PlantillaMapeo(
            tramo_id=tramo_id,
            nombre=datos.nombre,
            tipo_proceso=datos.tipo_proceso or "BASE_ORIGINAL",
            activo=True
        )
        db.add(nueva_plantilla)
        db.flush()

        # Si se especifica clonar, copiamos las asociaciones
        if datos.copiar_desde_plantilla_id:
            plantilla_origen = db.query(PlantillaMapeo).filter(
                PlantillaMapeo.id == datos.copiar_desde_plantilla_id,
                PlantillaMapeo.tramo_id == tramo_id
            ).first()

            if not plantilla_origen:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="La plantilla de origen a copiar no existe o pertenece a otro tramo."
                )

            # Duplicar relaciones Many-to-Many
            nueva_plantilla.columnas = list(plantilla_origen.columnas)
            nueva_plantilla.telefonos = list(plantilla_origen.telefonos)

        db.commit()
        db.refresh(nueva_plantilla)
        return nueva_plantilla

    @staticmethod
    def obtener_plantilla_mapeo(db: Session, plantilla_id: int) -> PlantillaMapeo:
        plantilla = db.query(PlantillaMapeo).filter(PlantillaMapeo.id == plantilla_id).first()
        if not plantilla:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plantilla no encontrada."
            )
        return plantilla

    @staticmethod
    def actualizar_asociaciones_plantilla(db: Session, plantilla_id: int, asociaciones: PlantillaAsociacionesUpdate) -> PlantillaMapeo:
        plantilla = db.query(PlantillaMapeo).filter(PlantillaMapeo.id == plantilla_id).first()
        if not plantilla:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plantilla no encontrada."
            )

        # 1. Asociar Columnas (Validando que pertenezcan al mismo tramo)
        columnas_db = db.query(MapeoColumnasTramo).filter(
            MapeoColumnasTramo.id.in_(asociaciones.columnas_ids),
            MapeoColumnasTramo.tramo_id == plantilla.tramo_id
        ).all()
        
        # Limpiar y sobreescribir la relación Muchos a Muchos
        plantilla.columnas = columnas_db

        # 2. Asociar Teléfonos (Validando que pertenezcan al mismo tramo)
        telefonos_db = db.query(ConfiguracionPrioridadTelefonos).filter(
            ConfiguracionPrioridadTelefonos.id.in_(asociaciones.telefonos_ids),
            ConfiguracionPrioridadTelefonos.tramo_id == plantilla.tramo_id
        ).all()
        
        plantilla.telefonos = telefonos_db

        db.commit()
        db.refresh(plantilla)
        return plantilla

    @staticmethod
    def eliminar_plantilla(db: Session, plantilla_id: int) -> dict:
        plantilla = db.query(PlantillaMapeo).filter(PlantillaMapeo.id == plantilla_id).first()
        if not plantilla:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plantilla no encontrada."
            )
        
        db.delete(plantilla)
        db.commit()
        return {
            "status": "success",
            "mensaje": "Plantilla eliminada correctamente 🎉"
        }
