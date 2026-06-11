from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RecuperarPasswordRequest(BaseModel):
    email: EmailStr

class RestablecerPasswordRequest(BaseModel):
    token: str
    nueva_password: str

class PerfilUpdateRequest(BaseModel):
    nombre: str
    apellido: str
    telefono: str | None = None

class CambiarPasswordRequest(BaseModel):
    password_actual: str
    nueva_password: str

# ============================================================================
# MODELOS DE RESPUESTA (PYDANTIC)
# ============================================================================

class UsuarioInfo(BaseModel):
    id: int
    email: EmailStr
    nombre: str
    apellido: str
    cargo: str
    ci: str
    telefono: str | None = None

    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    status: str = "success"
    mensaje: str
    access_token: str
    tipo_token: str = "bearer"
    usuario: UsuarioInfo

class MeDatosSeguros(BaseModel):
    usuario_id: int
    email: EmailStr
    rol: str
    nombre: str
    apellido: str

class MeResponse(BaseModel):
    status: str = "success"
    mensaje: str
    datos_seguros: MeDatosSeguros

class PerfilUpdateResponse(BaseModel):
    status: str = "success"
    mensaje: str
    usuario: UsuarioInfo

class SimpleResponse(BaseModel):
    status: str = "success"
    mensaje: str
