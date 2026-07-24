from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, ForeignKey, SmallInteger, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Rol(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(String(255), nullable=False)

    usuarios = relationship("Usuario", back_populates="rol")

class Modulo(Base):
    __tablename__ = "modulos"

    id = Column(Integer, primary_key=True, index=True)
    nombre_interno = Column(String(50), unique=True, nullable=False)
    nombre_pantalla = Column(String(100), nullable=False)
    descripcion = Column(String(255), nullable=False)

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(BigInteger, primary_key=True, index=True)
    rol_id = Column(Integer, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    estado = Column(String(20), default="ACTIVO", nullable=False)
    intentos_fallidos = Column(Integer, default=0, nullable=False)
    bloqueado_hasta = Column(DateTime(timezone=True), nullable=True)
    recuperar_password_token_hash = Column(String(64), unique=True, nullable=True)
    recuperar_password_expira = Column(DateTime(timezone=True), nullable=True)

    rol = relationship("Rol", back_populates="usuarios")
    perfil = relationship("Perfil", back_populates="usuario", uselist=False)
    sesiones = relationship("Sesion", back_populates="usuario")

    @property
    def nombre_completo(self) -> str:
        if self.perfil and self.perfil.nombre:
            return f"{self.perfil.nombre} {self.perfil.apellido}".strip()
        return self.email

class Perfil(Base):
    __tablename__ = "perfiles"

    id = Column(BigInteger, primary_key=True, index=True)
    usuario_id = Column(BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True, nullable=False)
    ci = Column(String(30), unique=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    telefono = Column(String(20), nullable=True)
    cargo = Column(String(100), nullable=False)

    usuario = relationship("Usuario", back_populates="perfil")

class RolModuloNivel(Base):
    __tablename__ = "roles_modulos_niveles"
    
    rol_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    modulo_id = Column(Integer, ForeignKey("modulos.id", ondelete="RESTRICT"), primary_key=True)
    nivel_acceso = Column(SmallInteger, nullable=False)

class Sesion(Base):
    __tablename__ = "sesiones"

    id = Column(BigInteger, primary_key=True, index=True)
    usuario_id = Column(BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    token_sesion_hash = Column(String(64), unique=True, index=True, nullable=False)
    valida = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expira_en = Column(DateTime(timezone=True), nullable=False)
    
    usuario = relationship("Usuario", back_populates="sesiones")