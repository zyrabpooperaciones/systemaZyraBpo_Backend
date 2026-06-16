from fastapi import APIRouter
from app.routes import auth, roles, usuarios, volcados

router = APIRouter()

# Registrar todos los sub-enrutadores
router.include_router(auth.router)
router.include_router(roles.router)
router.include_router(usuarios.router)
router.include_router(volcados.router)

# Aquí agregaremos las nuevas rutas en el futuro, por ejemplo:
# router.include_router(campañas.router)
# router.include_router(asistencia.router)
