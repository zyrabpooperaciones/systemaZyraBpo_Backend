from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, ForeignKey, Numeric, Date, UniqueConstraint, Table, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base

# ============================================================================
# TABLAS PUENTE (Muchos a Muchos)
# ============================================================================

plantillas_columnas = Table(
    "plantillas_columnas",
    Base.metadata,
    Column("plantilla_id", Integer, ForeignKey("plantillas_mapeo.id", ondelete="CASCADE"), primary_key=True),
    Column("columna_id", Integer, ForeignKey("mapeo_columnas_tramo.id", ondelete="CASCADE"), primary_key=True)
)

plantillas_telefonos = Table(
    "plantillas_telefonos",
    Base.metadata,
    Column("plantilla_id", Integer, ForeignKey("plantillas_mapeo.id", ondelete="CASCADE"), primary_key=True),
    Column("telefono_id", Integer, ForeignKey("configuracion_prioridad_telefonos.id", ondelete="CASCADE"), primary_key=True)
)

# ============================================================================
# BLOQUE 2: CLIENTES Y CONFIGURACIÓN DE TELÉFONOS (BELCOR)
# ============================================================================

class Departamento(Base):
    __tablename__ = "departamentos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)

    clientes = relationship("Cliente", back_populates="departamento")

class Seccion(Base):
    __tablename__ = "secciones"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    departamento_id = Column(Integer, ForeignKey("departamentos.id", ondelete="RESTRICT"), nullable=False)

    clientes = relationship("Cliente", back_populates="seccion")

class PerfilRiesgo(Base):
    __tablename__ = "perfiles_riesgo"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)

    clientes = relationship("Cliente", back_populates="perfil_riesgo")

class SegmentoRolling(Base):
    __tablename__ = "segmentos_rolling"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)

    clientes = relationship("Cliente", back_populates="segmento_rolling")

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(BigInteger, primary_key=True, index=True)
    codigo_cliente_belcor = Column(String(100), unique=True, index=True, nullable=False)
    nombre_completo = Column(String(255), nullable=False)
    numero_documento = Column(String(50), nullable=True)
    correo_electronico = Column(String(150), nullable=True)
    departamento_id = Column(Integer, ForeignKey("departamentos.id", ondelete="RESTRICT"), nullable=True)
    seccion_id = Column(Integer, ForeignKey("secciones.id", ondelete="RESTRICT"), nullable=True)
    perfil_riesgo_id = Column(Integer, ForeignKey("perfiles_riesgo.id", ondelete="RESTRICT"), nullable=True)
    segmento_rolling_id = Column(Integer, ForeignKey("segmentos_rolling.id", ondelete="RESTRICT"), nullable=True)
    
    # Marcado rápido
    telefono_uso = Column(String(20), nullable=True)
    observacion_telefono = Column(String(255), nullable=True)

    # Relaciones
    departamento = relationship("Departamento", back_populates="clientes")
    seccion = relationship("Seccion", back_populates="clientes")
    perfil_riesgo = relationship("PerfilRiesgo", back_populates="clientes")
    segmento_rolling = relationship("SegmentoRolling", back_populates="clientes")
    telefonos = relationship("TelefonoCliente", back_populates="cliente", cascade="all, delete-orphan")
    cargos = relationship("Cargo", back_populates="cliente", cascade="all, delete-orphan")

class TelefonoCliente(Base):
    __tablename__ = "telefonos_clientes"

    id = Column(BigInteger, primary_key=True, index=True)
    cliente_id = Column(BigInteger, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)
    numero = Column(String(20), nullable=False)
    tipo = Column(String(100), nullable=False)
    prioridad = Column(Numeric(5, 2), nullable=False)
    estado = Column(String(20), default="ACTIVO", nullable=False)
    motivo_cambio = Column(String(255), nullable=True)
    fecha_cambio = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cliente = relationship("Cliente", back_populates="telefonos")

class Tramo(Base):
    __tablename__ = "tramos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(10), unique=True, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

    columnas = relationship("MapeoColumnasTramo", back_populates="tramo", cascade="all, delete-orphan")
    telefonos_config = relationship("ConfiguracionPrioridadTelefonos", back_populates="tramo", cascade="all, delete-orphan")
    plantillas = relationship("PlantillaMapeo", back_populates="tramo", cascade="all, delete-orphan")
    cargos = relationship("Cargo", back_populates="tramo")

class MapeoColumnasTramo(Base):
    __tablename__ = "mapeo_columnas_tramo"

    id = Column(Integer, primary_key=True, index=True)
    tramo_id = Column(Integer, ForeignKey("tramos.id", ondelete="CASCADE"), nullable=False)
    tipo_campo = Column(String(20), nullable=False)  # 'DATO' o 'MONTO'
    campo_sistema = Column(String(50), nullable=False)
    nombre_columna_excel = Column(String(100), nullable=False)
    es_obligatorio = Column(Boolean, default=False, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

    tramo = relationship("Tramo", back_populates="columnas")

    __table_args__ = (
        UniqueConstraint("tramo_id", "nombre_columna_excel", name="uq_tramo_columna_excel"),
        UniqueConstraint("tramo_id", "campo_sistema", name="uq_tramo_campo_sistema"),
    )

class ConfiguracionPrioridadTelefonos(Base):
    __tablename__ = "configuracion_prioridad_telefonos"

    id = Column(Integer, primary_key=True, index=True)
    tramo_id = Column(Integer, ForeignKey("tramos.id", ondelete="CASCADE"), nullable=False)
    nombre_columna_excel = Column(String(100), nullable=False)
    prioridad = Column(Integer, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

    tramo = relationship("Tramo", back_populates="telefonos_config")

    __table_args__ = (
        UniqueConstraint("tramo_id", "nombre_columna_excel", name="uq_tramo_telefono_excel"),
    )

class PlantillaMapeo(Base):
    __tablename__ = "plantillas_mapeo"

    id = Column(Integer, primary_key=True, index=True)
    tramo_id = Column(Integer, ForeignKey("tramos.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(100), nullable=False)
    tipo_proceso = Column(String(50), default="BASE_ORIGINAL", nullable=False)  # 'BASE_ORIGINAL', 'BASE_ACTUALIZACION', 'BASE_SALDOS', 'EXPORTACION'
    activo = Column(Boolean, default=True, nullable=False)

    tramo = relationship("Tramo", back_populates="plantillas")
    columnas = relationship("MapeoColumnasTramo", secondary=plantillas_columnas, backref="plantillas")
    telefonos = relationship("ConfiguracionPrioridadTelefonos", secondary=plantillas_telefonos, backref="plantillas")

    __table_args__ = (
        UniqueConstraint("tramo_id", "nombre", name="uq_tramo_nombre_plantilla"),
    )


# ============================================================================
# BLOQUE 3: CARGOS Y DEUDAS (Estructura de Cobranza)
# ============================================================================

class Campana(Base):
    __tablename__ = "campanas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)

    cargos = relationship("Cargo", back_populates="campana")

class Cargo(Base):
    __tablename__ = "cargos"

    id = Column(BigInteger, primary_key=True, index=True)
    cliente_id = Column(BigInteger, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)
    numero_cargo = Column(String(100), nullable=False)
    tramo_id = Column(Integer, ForeignKey("tramos.id", ondelete="RESTRICT"), nullable=False)
    campana_id = Column(Integer, ForeignKey("campanas.id", ondelete="RESTRICT"), nullable=False)
    dias_atraso = Column(Integer, default=0, nullable=False)
    fecha_cierre = Column(Date, nullable=True)
    estado = Column(String(50), default="ACTIVO", nullable=False)
    observacion = Column(String, nullable=True)

    # Campos financieros de control desglosado
    monto_inicial = Column(Numeric(10, 2), default=0.00, nullable=False)
    monto_interes = Column(Numeric(10, 2), default=0.00, nullable=False)
    monto_gasto_adm = Column(Numeric(10, 2), default=0.00, nullable=False)
    monto_pagado = Column(Numeric(10, 2), default=0.00, nullable=False)
    monto_descontar = Column(Numeric(10, 2), default=0.00, nullable=False)

    # Campos totales calculados
    deuda_total = Column(Numeric(10, 2), default=0.00, nullable=False)
    saldo_cobrar = Column(Numeric(10, 2), default=0.00, nullable=False)

    # Relaciones
    cliente = relationship("Cliente", back_populates="cargos")
    tramo = relationship("Tramo", back_populates="cargos")
    campana = relationship("Campana", back_populates="cargos")
    movimientos = relationship("MovimientoCargo", back_populates="cargo", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("cliente_id", "numero_cargo", "tramo_id", "campana_id", name="uq_cliente_cargo_tramo_campana"),
    )

class MovimientoCargo(Base):
    __tablename__ = "movimientos_cargos"

    id = Column(BigInteger, primary_key=True, index=True)
    cargo_id = Column(BigInteger, ForeignKey("cargos.id", ondelete="CASCADE"), nullable=False)
    tipo_movimiento = Column(String(30), nullable=False)  # 'INICIAL', 'PAGO', 'INTERES', 'GASTO_ADM', 'DESCUENTO'
    monto = Column(Numeric(10, 2), nullable=False)
    fecha_movimiento = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cargo = relationship("Cargo", back_populates="movimientos")

class HistorialImportacion(Base):
    __tablename__ = "historial_importaciones"

    id = Column(Integer, primary_key=True, index=True)
    tramo_id = Column(Integer, ForeignKey("tramos.id", ondelete="CASCADE"), nullable=False)
    nombre_archivo = Column(String(255), nullable=False)
    hash_archivo = Column(String(64), unique=True, index=True, nullable=False)
    tipo_subida = Column(String(50), nullable=False)  # 'BASE_ORIGINAL', 'BASE_ACTUALIZACION', 'BASE_SALDOS'
    fecha_importacion = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    usuario_id = Column(BigInteger, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    registros_procesados = Column(Integer, default=0, nullable=False)

    # Contadores de auditoría y montos financieros de la carga
    clientes_nuevos = Column(Integer, default=0, nullable=False)
    clientes_actualizados = Column(Integer, default=0, nullable=False)
    cargos_nuevos = Column(Integer, default=0, nullable=False)
    cargos_actualizados = Column(Integer, default=0, nullable=False)
    telefonos_nuevos = Column(Integer, default=0, nullable=False)
    telefono_uso_actualizados = Column(Integer, default=0, nullable=False)
    movimientos_financieros_creados = Column(Integer, default=0, nullable=False)
    monto_deuda_inicial_total = Column(Numeric(12, 2), default=0.0, nullable=False)
    monto_interes_total = Column(Numeric(12, 2), default=0.0, nullable=False)
    monto_gasto_adm_total = Column(Numeric(12, 2), default=0.0, nullable=False)
    monto_pagos_total = Column(Numeric(12, 2), default=0.0, nullable=False)
    duracion_segundos = Column(Numeric(8, 2), default=0.0, nullable=False)

    tramo = relationship("Tramo")
    usuario = relationship("Usuario")

class DescuentoConfig(Base):
    __tablename__ = "descuentos_config"

    id = Column(Integer, primary_key=True, index=True)
    tramo_id = Column(Integer, ForeignKey("tramos.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(150), nullable=False)
    
    # Configuración de Montos (Variables o Fijo)
    descuento_monto_fijo = Column(Numeric(10, 2), default=0.00, nullable=False)
    pct_descuento_capital = Column(Numeric(5, 2), default=0.00, nullable=False)
    pct_descuento_interes = Column(Numeric(5, 2), default=0.00, nullable=False)
    pct_descuento_gasto = Column(Numeric(5, 2), default=0.00, nullable=False)
    
    # Filtros de Segmentación (Almacenados como listas JSONB)
    campanas = Column(JSONB, default=list, nullable=False)
    departamentos = Column(JSONB, default=list, nullable=False)
    perfiles_riesgo = Column(JSONB, default=list, nullable=False)
    segmentos_rolling = Column(JSONB, default=list, nullable=False)
    
    # Estado de Control
    activo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relación
    tramo = relationship("Tramo", backref="descuentos")
