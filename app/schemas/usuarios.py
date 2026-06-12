from pydantic import BaseModel, EmailStr, Field

class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    rol_id: int
    ci: str = Field(..., max_length=30)
    nombre: str = Field(..., max_length=100)
    apellido: str = Field(..., max_length=100)
    telefono: str | None = Field(None, max_length=20)
    cargo: str | None = Field(None, max_length=100)

class UsuarioUpdate(BaseModel):
    email: EmailStr
    rol_id: int
    estado: str = Field(..., max_length=20)  # ACTIVO, INACTIVO, BLOQUEADO
    ci: str = Field(..., max_length=30)
    nombre: str = Field(..., max_length=100)
    apellido: str = Field(..., max_length=100)
    telefono: str | None = Field(None, max_length=20)
    cargo: str | None = Field(None, max_length=100)

class UsuarioResponse(BaseModel):
    id: int
    email: EmailStr
    estado: str
    rol_id: int
    rol_nombre: str
    nombre: str
    apellido: str
    cargo: str
    ci: str
    telefono: str | None = None

    class Config:
        from_attributes = True
