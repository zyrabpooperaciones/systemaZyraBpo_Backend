from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import obtener_db
from fastapi.middleware.cors import CORSMiddleware
from app.routes import api
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configuración básica de logs para el sistema
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zyra_bpo_backend")

app = FastAPI(title="Zyra BPO - API")

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

@app.get("/")
def leer_raiz():
    return {"mensaje": "¡Hola Jairo, el Backend de Zyra BPO está vivo y escuchando!"}

@app.get("/test-db")
def probar_conexion_db(db: Session = Depends(obtener_db)):
    try:
        resultado = db.execute(text("SELECT 1 + 1")).scalar()
        return {
            "status": "ok", 
            "conexion_postgres": "¡Exitosa y blindada! 🚀", 
            "prueba_calculo": f"Postgres dice que 1 + 1 es {resultado}"
        }
    except Exception as e:
        logger.error(f"Error crítico de conexión a la base de datos: {e}", exc_info=True)
        return {"status": "error", "detalle": "No se pudo conectar a la base de datos interna."}