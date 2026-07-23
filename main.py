from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import api
import os
import logging
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import asyncio
from app.core.database import SessionLocal
from sqlalchemy import text

load_dotenv()

# Configuración básica de logs para el sistema
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zyra_bpo_backend")

def actualizar_cargos_vencidos_db():
    db = SessionLocal()
    try:
        sql = """
        UPDATE cargos
        SET estado = 'VENCIDO'
        WHERE estado = 'ACTIVO'
          AND fecha_cierre IS NOT NULL
          AND fecha_cierre < CURRENT_DATE;
        """
        result = db.execute(text(sql))
        db.commit()
        if result.rowcount > 0:
            logger.info(f"Actualización automática de cargos vencidos completada. Filas afectadas: {result.rowcount}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error en la actualización automática de cargos vencidos: {e}", exc_info=True)
    finally:
        db.close()

async def scheduler_cargos_vencidos():
    while True:
        try:
            actualizar_cargos_vencidos_db()
        except Exception as e:
            logger.error(f"Error en scheduler_cargos_vencidos: {e}")
        # Esperar 1 hora (3600 segundos) antes de volver a verificar
        await asyncio.sleep(3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando planificador de cargos vencidos...")
    task = asyncio.create_task(scheduler_cargos_vencidos())
    yield
    logger.info("Cancelando planificador de cargos vencidos...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="Zyra BPO - API", lifespan=lifespan)

# Escudo de permisos para Angular y otros orígenes permitidos
cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:4200")
origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router)