from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import obtener_db
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth

app = FastAPI(title="Zyra BPO - API")

# Escudo de permisos para Angular
origins = [
    "http://localhost:4200",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

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
        return {"status": "error", "detalle": str(e)}