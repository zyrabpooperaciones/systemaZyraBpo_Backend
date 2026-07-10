from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import obtener_db
from app.models.auth import Usuario, Sesion, Modulo, RolModuloNivel
from datetime import datetime, timezone
import hashlib

# Activamos el receptor de tokens Bearer
seguridad_bearer = HTTPBearer()

def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(seguridad_bearer),
    db: Session = Depends(obtener_db)
) -> Usuario:
    
    # 1. Extraer el token y limpiarlo de comillas molestas (como en el logout)
    token_cliente = credenciales.credentials.strip('"').strip()
    
    # 2. Convertirlo a SHA-256 para buscarlo en la base de datos
    token_hasheado = hashlib.sha256(token_cliente.encode('utf-8')).hexdigest()
    
    # 3. Buscar la sesión en Postgres que sea VÁLIDA
    sesion = db.query(Sesion).filter(
        Sesion.token_sesion_hash == token_hasheado,
        Sesion.valida == True
    ).first()
    
    # Si la sesión no existe o ya fue cerrada (False), rebote inmediato
    if not sesion:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida, inexistente o ya cerrada. Inicie sesión de nuevo."
        )
    
    # 4. Verificar si el token ya caducó por tiempo (24 horas)
    ahora = datetime.now(timezone.utc)
    if ahora > sesion.expira_en:
        # Aprovechamos de marcarla como inválida en la BD para que no estorbe
        sesion.valida = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Su sesión ha expirado por límite de tiempo. Inicie sesión de nuevo."
        )
        
    # 5. Buscar el usuario dueño de esa sesión
    usuario = db.query(Usuario).filter(Usuario.id == sesion.usuario_id).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado en el sistema."
        )
        
    # 6. Verificar que el usuario no esté suspendido o inactivo administrativamente
    if usuario.estado != "ACTIVO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acceso denegado. Su usuario se encuentra: {usuario.estado}."
        )
        
    # ¡Luz verde! El guardián abre la puerta y le entrega el usuario a la ruta
    return usuario

def verificar_permiso(modulo_interno: str, nivel_requerido: int):
    
    def dependencia(
        usuario_actual: Usuario = Depends(obtener_usuario_actual),
        db: Session = Depends(obtener_db)
    ) -> Usuario:
        # Buscar el modulo por su nombre interno
        modulo = db.query(Modulo).filter(Modulo.nombre_interno == modulo_interno).first()
        if not modulo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El modulo '{modulo_interno}' no existe en el sistema."
            )
            
        # Buscar si el rol del usuario tiene el modulo asignado
        permiso = db.query(RolModuloNivel).filter(
            RolModuloNivel.rol_id == usuario_actual.rol_id,
            RolModuloNivel.modulo_id == modulo.id
        ).first()
        
        # Si no hay registro o el nivel es inferior al requerido
        if not permiso or permiso.nivel_acceso < nivel_requerido:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos suficientes para realizar esta accion."
            )
            
        return usuario_actual
    return dependencia