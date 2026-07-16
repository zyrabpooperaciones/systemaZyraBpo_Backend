from pydantic import BaseModel, Field
from typing import List, Optional

# ============================================================================
# TRAMOS SCHEMAS
# ============================================================================

class TramoResponse(BaseModel):
    id: int
    nombre: str
    activo: bool

    class Config:
        from_attributes = True

class TramoUpdateEstado(BaseModel):
    activo: bool

# ============================================================================
# COLUMNAS SCHEMAS (DATOS Y MONTOS)
# ============================================================================

class MapeoColumnasTramoCreate(BaseModel):
    tipo_campo: str = Field(..., description="'DATO' o 'MONTO'")
    campo_sistema: str = Field(..., max_length=50)
    nombre_columna_excel: str = Field(..., max_length=100)
    es_obligatorio: bool = False
    activo: bool = True

class MapeoColumnasTramoResponse(BaseModel):
    id: int
    tramo_id: int
    tipo_campo: str
    campo_sistema: str
    nombre_columna_excel: str
    es_obligatorio: bool
    activo: bool

    class Config:
        from_attributes = True

# ============================================================================
# TELEFONOS SCHEMAS
# ============================================================================

class ConfiguracionPrioridadTelefonosCreate(BaseModel):
    id: Optional[int] = None
    nombre_columna_excel: str = Field(..., max_length=100)
    prioridad: int
    activo: bool = True

class ConfiguracionPrioridadTelefonosResponse(BaseModel):
    id: int
    tramo_id: int
    nombre_columna_excel: str
    prioridad: int
    activo: bool

    class Config:
        from_attributes = True

# ============================================================================
# PLANTILLAS SCHEMAS
# ============================================================================

class PlantillaMapeoCreate(BaseModel):
    nombre: str = Field(..., max_length=100)
    tipo_proceso: Optional[str] = Field("BASE_ORIGINAL", description="'BASE_ORIGINAL', 'BASE_ACTUALIZACION', 'BASE_SALDOS'")
    copiar_desde_plantilla_id: Optional[int] = None

class PlantillaMapeoResponse(BaseModel):
    id: int
    tramo_id: int
    nombre: str
    tipo_proceso: str
    activo: bool

    class Config:
        from_attributes = True

class PlantillaMapeoDetailResponse(BaseModel):
    id: int
    tramo_id: int
    nombre: str
    tipo_proceso: str
    activo: bool
    columnas: List[MapeoColumnasTramoResponse] = []
    telefonos: List[ConfiguracionPrioridadTelefonosResponse] = []

    class Config:
        from_attributes = True

class PlantillaAsociacionesUpdate(BaseModel):
    columnas_ids: List[int]
    telefonos_ids: List[int]
