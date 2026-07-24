from fastapi import APIRouter
from app.routes import auth, roles, usuarios, volcados, tramos, importacion, clientes, descuentos, metricas

router = APIRouter()

# Registrar todos los sub-enrutadores
router.include_router(auth.router)
router.include_router(roles.router)
router.include_router(usuarios.router)
router.include_router(volcados.router)
router.include_router(tramos.router)
router.include_router(importacion.router)
router.include_router(clientes.router)
router.include_router(descuentos.router)
router.include_router(metricas.router)

# Aquí agregaremos las nuevas rutas en el futuro, por ejemplo:
# router.include_router(campañas.router)
# router.include_router(asistencia.router)
