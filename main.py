from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Lista de URLs permitidas (aquí va tu Frontend de Angular)
origins = [
    "http://localhost:4200",
]

# Le aplicamos el escudo de permisos a la aplicación
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Permite cualquier cabecera de datos
)

@app.get("/")
def leer_raiz():
    return {"mensaje": "¡Hola Jairo, el Backend de Zyra BPO está vivo y escuchando!"}