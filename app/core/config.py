from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr, Field

class Settings(BaseSettings):
    # Base de Datos
    DB_USER: str = Field(..., description="Usuario de la base de datos PostgreSQL")
    DB_PASSWORD: str = Field(..., description="Contraseña de la base de datos")
    DB_HOST: str = Field("localhost", description="Host de la base de datos")
    DB_PORT: str = Field("5432", description="Puerto de la base de datos")
    DB_NAME: str = Field(..., description="Nombre de la base de datos")

    # Email
    EMAIL_EMISOR: EmailStr = Field(..., description="Correo electrónico emisor (Gmail)")
    EMAIL_PASSWORD: str = Field(..., description="Contraseña de aplicación del correo emisor")
    FRONTEND_URL: str = Field("http://localhost:4200", description="URL del frontend para los enlaces de recuperación")
    
    # Configuración general
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore" # Ignore extra fields in .env
    )
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()
