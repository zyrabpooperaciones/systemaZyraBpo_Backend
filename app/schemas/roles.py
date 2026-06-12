from pydantic import BaseModel, Field

class RolCreate(BaseModel):
    nombre: str = Field(..., max_length=50)
    descripcion: str = Field(..., max_length=255)

class RolUpdate(BaseModel):
    nombre: str = Field(..., max_length=50)
    descripcion: str = Field(..., max_length=255)

class RolResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str

    class Config:
        from_attributes = True

class ModuloResponse(BaseModel):
    id: int
    nombre_interno: str
    nombre_pantalla: str
    descripcion: str

    class Config:
        from_attributes = True

class PermisoResponse(BaseModel):
    modulo_id: int
    nombre_interno: str
    nombre_pantalla: str
    nivel_acceso: int

    class Config:
        from_attributes = True

class PermisoUpdate(BaseModel):
    modulo_id: int
    nivel_acceso: int = Field(..., ge=0, le=3)

class RolPermisosUpdate(BaseModel):
    permisos: list[PermisoUpdate]
