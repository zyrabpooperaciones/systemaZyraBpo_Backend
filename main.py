from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import api
import os
import logging
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from sembrar_datos import sembrar_datos_produccion
from crear_admin import crear_usuario_administrador

load_dotenv()

# Configuración básica de logs para el sistema
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zyra_bpo_backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando sembrado seguro de base de datos...")
    try:
        sembrar_datos_produccion()
        crear_usuario_administrador()
    except Exception as e:
        logger.error(f"Error en el sembrado automático de inicio: {e}", exc_info=True)
    yield

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