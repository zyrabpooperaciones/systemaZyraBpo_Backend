from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ValidationErrorDetail(BaseModel):
    fila: int
    columna: str
    mensaje: str

class ImportSummaryResponse(BaseModel):
    clientes_nuevos: int
    clientes_actualizados: int
    cargos_nuevos: int
    cargos_actualizados: int
    telefonos_nuevos: int
    telefono_uso_actualizados: int
    movimientos_financieros_creados: int
    monto_deuda_inicial_total: float
    monto_interes_total: float
    monto_gasto_adm_total: float
    total_filas_procesadas: int
    duracion_segundos: float

class ValidationResponse(BaseModel):
    es_valido: bool
    errores: List[ValidationErrorDetail] = []

class TramoActivoResponse(BaseModel):
    id: int
    nombre: str
    activo: bool

    class Config:
        from_attributes = True

class HistorialImportacionResponse(BaseModel):
    id: int
    tramo_id: int
    nombre_archivo: str
    hash_archivo: str
    tipo_subida: str
    fecha_importacion: datetime
    usuario_id: int
    usuario_nombre: str
    registros_procesados: int
    clientes_nuevos: int
    clientes_actualizados: int
    cargos_nuevos: int
    cargos_actualizados: int
    telefonos_nuevos: int
    telefono_uso_actualizados: int
    movimientos_financieros_creados: int
    monto_deuda_inicial_total: float
    monto_interes_total: float
    monto_gasto_adm_total: float
    duracion_segundos: float

    class Config:
        from_attributes = True
