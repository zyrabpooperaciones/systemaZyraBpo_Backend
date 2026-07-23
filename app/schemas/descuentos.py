from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

class DescuentoConfigBase(BaseModel):
    nombre: str = Field(..., max_length=150)
    descuento_monto_fijo: Decimal = Field(default=Decimal("0.00"))
    pct_descuento_capital: Decimal = Field(default=Decimal("0.00"))
    pct_descuento_interes: Decimal = Field(default=Decimal("0.00"))
    pct_descuento_gasto: Decimal = Field(default=Decimal("0.00"))
    campanas: List[str] = Field(default_factory=list)
    departamentos: List[str] = Field(default_factory=list)
    perfiles_riesgo: List[str] = Field(default_factory=list)
    segmentos_rolling: List[str] = Field(default_factory=list)
    activo: bool = True

class DescuentoConfigCreate(DescuentoConfigBase):
    tramo_id: int

class DescuentoConfigResponse(DescuentoConfigBase):
    id: int
    tramo_id: int
    created_at: datetime

    class Config:
        from_attributes = True
