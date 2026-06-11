from fastapi import APIRouter
from app.routes import auth

router = APIRouter()

# Incluimos los módulos de rutas
router.include_router(auth.router)

# Aquí agregaremos las nuevas rutas en el futuro, por ejemplo:
# router.include_router(campañas.router)
# router.include_router(asistencia.router)
