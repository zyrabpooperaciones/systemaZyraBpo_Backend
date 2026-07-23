from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date

class TelefonoClienteDetalle(BaseModel):
    id: int
    numero: str
    tipo: str
    prioridad: float
    estado: str
    fecha_cambio: datetime

    class Config:
        from_attributes = True

class CargoClienteDetalle(BaseModel):
    id: int
    numero_cargo: str
    campana_nombre: str
    dias_atraso: int
    fecha_cierre: Optional[date] = None
    monto_inicial: float
    monto_interes: float
    monto_gasto_adm: float
    monto_pagado: float
    saldo_cobrar: float
    descuento_aplicable: float = 0.0
    monto_para_liquidar: float = 0.0
    estado: str
    observacion: Optional[str] = None

    class Config:
        from_attributes = True

class MovimientoCargoDetalle(BaseModel):
    id: int
    numero_cargo: str
    tipo_movimiento: str
    monto: float
    fecha_movimiento: datetime

    class Config:
        from_attributes = True

class DetalleCliente360Response(BaseModel):
    id: int
    codigo_cliente_belcor: str
    nombre_completo: str
    numero_documento: Optional[str] = None
    correo_electronico: Optional[str] = None
    departamento: Optional[str] = None
    seccion: Optional[str] = None
    perfil_riesgo: Optional[str] = None
    segmento_rolling: Optional[str] = None
    telefonos: List[TelefonoClienteDetalle]
    cargos: List[CargoClienteDetalle]
    movimientos: List[MovimientoCargoDetalle]

    class Config:
        from_attributes = True

class ClienteSearchItem(BaseModel):
    id: int
    codigo_cliente_belcor: str
    nombre_completo: str
    numero_documento: Optional[str] = None
    cantidad_cargos: int
    saldo_total_pendiente: float
    saldo_neto_pendiente: float = 0.0
    telefono_principal: Optional[str] = None
    campanas_activas: List[str]
    estado_general: str

    class Config:
        from_attributes = True

class PaginatedClientesResponse(BaseModel):
    total: int
    items: List[ClienteSearchItem]
