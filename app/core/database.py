from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Cargamos las variables de entorno desde el archivo .env
load_dotenv()

# 1. Parámetros de conexión de base de datos (PostgreSQL 17)
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

# Validamos que los parámetros obligatorios existan para evitar errores de conexión crípticos
if not all([DB_USER, DB_PASSWORD, DB_NAME]):
    missing = [name for name, val in [("DB_USER", DB_USER), ("DB_PASSWORD", DB_PASSWORD), ("DB_NAME", DB_NAME)] if not val]
    raise ValueError(
        f"Faltan variables de entorno esenciales para conectar con la base de datos: {', '.join(missing)}. "
        f"Por favor verifica la configuración de tu archivo .env"
    )

URL_BASE_DATOS = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 2. El motor que administra las conexiones físicas a Postgres
engine = create_engine(URL_BASE_DATOS)

# 3. La fábrica que creará las sesiones para hacer consultas de forma segura
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. La clase base de la cual heredarán todos nuestros futuros modelos de tablas
Base = declarative_base()

# 5. Función auxiliar (Dependencia) para abrir y cerrar la base de datos en cada petición
def obtener_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # Cerramos la conexión de inmediato para no saturar a Postgres