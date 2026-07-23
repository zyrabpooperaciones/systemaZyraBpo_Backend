import io
from typing import List
import pandas as pd
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import obtener_db
from app.core.dependencies import verificar_permiso
from app.models.auth import Usuario, Perfil
from app.models.cobranzas import PlantillaMapeo, Tramo, HistorialImportacion
from app.services.importacion_service import ImportacionService
from app.schemas.importacion import (
    ImportSummaryResponse, ValidationResponse,
    TramoActivoResponse, HistorialImportacionResponse
)

router = APIRouter(prefix="/importacion", tags=["Modulo de Importacion"])

@router.post("/validar", response_model=ValidationResponse)
async def validar_archivo_importacion(
    tramo_id: int = Form(...),
    plantilla_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(obtener_db),
    _usuario_valido: Usuario = Depends(verificar_permiso(modulo_interno="importacion", nivel_requerido=1))
):
    """
    Simula de forma estricta (Dry-Run) la carga de un archivo Excel de deudas (Requiere Permiso: importacion - Nivel 1).
    Valida:
    - Firmas duplicadas (Hash SHA-256)
    - Estructura de cabeceras requeridas
    - Tipos de datos, importes numéricos y fechas fila por fila.
    """
    # 1. Verificar existencia de la plantilla y correspondencia con el tramo
    plantilla = db.query(PlantillaMapeo).filter(
        PlantillaMapeo.id == plantilla_id,
        PlantillaMapeo.tramo_id == tramo_id
    ).first()

    if not plantilla:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La plantilla de mapeo especificada no existe o no pertenece al tramo seleccionado."
        )

    # 2. Leer archivo en bytes y verificar duplicado
    file_bytes = await file.read()
    file_hash = ImportacionService.calcular_hash_archivo(file_bytes)

    if ImportacionService.verificar_duplicado(db, file_hash):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "es_valido": False,
                "errores": [{
                    "fila": 1,
                    "columna": "Firma del Archivo (Hash)",
                    "mensaje": "Este archivo Excel ya fue importado y procesado previamente en el sistema (evitando duplicados)."
                }]
            }
        )

    # 3. Decodificar archivo Excel con Pandas
    try:
        file_df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "es_valido": False,
                "errores": [{
                    "fila": 1,
                    "columna": "Archivo",
                    "mensaje": f"No se pudo procesar el archivo Excel. Verifique que el archivo no esté dañado. Detalle: {str(e)}"
                }]
            }
        )

    # 4. Validar que las columnas obligatorias mapeadas en la plantilla existan en las cabeceras del Excel
    mapeo_columnas, _, errores_cabeceras = ImportacionService.validar_y_mapear_columnas(file_df, plantilla)
    if errores_cabeceras:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "es_valido": False,
                "errores": [err.model_dump() for err in errores_cabeceras]
            }
        )

    # 5. Ejecutar simulación Dry-Run fila por fila de tipos de datos e identificadores requeridos
    errores_filas = ImportacionService.simular_dry_run(file_df, mapeo_columnas, plantilla.tipo_proceso, db)
    if errores_filas:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "es_valido": False,
                "errores": [err.model_dump() for err in errores_filas]
            }
        )

    return {
        "es_valido": True,
        "errores": []
    }


@router.post("/procesar", response_model=ImportSummaryResponse)
async def procesar_archivo_importacion(
    tramo_id: int = Form(...),
    plantilla_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(obtener_db),
    usuario_actual: Usuario = Depends(verificar_permiso(modulo_interno="importacion", nivel_requerido=2))
):
    """
    Ejecuta el procesamiento real e ingesta en lotes de la base de deudas (Requiere Permiso: importacion - Nivel 2).
    Realiza una validación completa previa antes de escribir transaccionalmente.
    """
    # 1. Verificar existencia de la plantilla y correspondencia con el tramo
    plantilla = db.query(PlantillaMapeo).filter(
        PlantillaMapeo.id == plantilla_id,
        PlantillaMapeo.tramo_id == tramo_id
    ).first()

    if not plantilla:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La plantilla de mapeo especificada no existe o no pertenece al tramo seleccionado."
        )

    # 2. Leer archivo en bytes y verificar duplicado
    file_bytes = await file.read()
    file_hash = ImportacionService.calcular_hash_archivo(file_bytes)

    if ImportacionService.verificar_duplicado(db, file_hash):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "es_valido": False,
                "errores": [{
                    "fila": 1,
                    "columna": "Firma del Archivo (Hash)",
                    "mensaje": "Este archivo Excel ya fue importado y procesado previamente en el sistema (evitando duplicados)."
                }]
            }
        )

    # 3. Decodificar archivo Excel con Pandas
    try:
        file_df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "es_valido": False,
                "errores": [{
                    "fila": 1,
                    "columna": "Archivo",
                    "mensaje": f"No se pudo procesar el archivo Excel. Detalle: {str(e)}"
                }]
            }
        )

    # 4. Validar cabeceras mapeadas
    mapeo_columnas, telefonos_prioridad, errores_cabeceras = ImportacionService.validar_y_mapear_columnas(file_df, plantilla)
    if errores_cabeceras:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "es_valido": False,
                "errores": [err.model_dump() for err in errores_cabeceras]
            }
        )

    # 5. Ejecutar simulación Dry-Run fila por fila
    errores_filas = ImportacionService.simular_dry_run(file_df, mapeo_columnas, plantilla.tipo_proceso, db)
    if errores_filas:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "es_valido": False,
                "errores": [err.model_dump() for err in errores_filas]
            }
        )

    # 6. Proceder con el guardado en lotes transaccional (All-or-Nothing)
    try:
        resumen = ImportacionService.procesar_carga_base_original(
            db=db,
            file_df=file_df,
            tramo_id=tramo_id,
            plantilla=plantilla,
            mapeo_columnas=mapeo_columnas,
            telefonos_prioridad=telefonos_prioridad,
            usuario_id=usuario_actual.id,
            nombre_archivo=file.filename,
            hash_archivo=file_hash
        )
        return resumen
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error inesperado al procesar la ingesta en la base de datos: {str(e)}"
        )


@router.get("/tramos", response_model=List[TramoActivoResponse])
def listar_tramos_activos(
    db: Session = Depends(obtener_db),
    _usuario: Usuario = Depends(verificar_permiso(modulo_interno="importacion", nivel_requerido=1))
):
    """
    Lista todos los tramos que están en estado activo (Requiere Permiso: importacion - Nivel 1).
    """
    tramos = db.query(Tramo).filter(Tramo.activo == True).order_by(Tramo.nombre).all()
    return tramos


@router.get("/historial/{tramo_id}", response_model=List[HistorialImportacionResponse])
def listar_historial_importacion(
    tramo_id: int,
    db: Session = Depends(obtener_db),
    _usuario: Usuario = Depends(verificar_permiso(modulo_interno="importacion", nivel_requerido=1))
):
    """
    Retorna el historial completo de importaciones de un tramo específico ordenado por fecha de importación descendente (Requiere Permiso: importacion - Nivel 1).
    """
    registros = db.query(
        HistorialImportacion.id,
        HistorialImportacion.tramo_id,
        HistorialImportacion.nombre_archivo,
        HistorialImportacion.hash_archivo,
        HistorialImportacion.tipo_subida,
        HistorialImportacion.fecha_importacion,
        HistorialImportacion.usuario_id,
        func.concat(Perfil.nombre, ' ', Perfil.apellido).label("usuario_nombre"),
        HistorialImportacion.registros_procesados,
        HistorialImportacion.clientes_nuevos,
        HistorialImportacion.clientes_actualizados,
        HistorialImportacion.cargos_nuevos,
        HistorialImportacion.cargos_actualizados,
        HistorialImportacion.telefonos_nuevos,
        HistorialImportacion.telefono_uso_actualizados,
        HistorialImportacion.movimientos_financieros_creados,
        HistorialImportacion.monto_deuda_inicial_total,
        HistorialImportacion.monto_interes_total,
        HistorialImportacion.monto_gasto_adm_total,
        HistorialImportacion.monto_pagos_total,
        HistorialImportacion.duracion_segundos
    ).join(
        Usuario, HistorialImportacion.usuario_id == Usuario.id
    ).join(
        Perfil, Usuario.id == Perfil.usuario_id
    ).filter(
        HistorialImportacion.tramo_id == tramo_id
    ).order_by(
        HistorialImportacion.fecha_importacion.desc()
    ).all()

    return registros
