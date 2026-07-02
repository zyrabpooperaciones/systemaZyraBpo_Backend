from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 2. El motor que administra las conexiones físicas a Postgres usando la configuración centralizada
engine = create_engine(settings.DATABASE_URL)

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