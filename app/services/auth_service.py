from datetime import datetime, timezone, timedelta
import secrets
import hashlib
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.auth import Usuario, Perfil, Sesion
from app.services.security import SecurityService
from app.services.email_service import EmailService
from app.schemas.auth import (
    LoginRequest,
    RecuperarPasswordRequest,
    RestablecerPasswordRequest,
    PerfilUpdateRequest,
    CambiarPasswordRequest
)

class AuthService:
    
    @staticmethod
    def iniciar_sesion(db: Session, datos: LoginRequest) -> dict:
        usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Correo o contraseña incorrectos"
            )
        if usuario.estado != "ACTIVO":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"El usuario se encuentra {usuario.estado}."
            )
        
        ahora = datetime.now(timezone.utc)
        if usuario.bloqueado_hasta:
            if ahora < usuario.bloqueado_hasta:
                tiempo_restante = usuario.bloqueado_hasta - ahora
                minutos_restantes = int(tiempo_restante.total_seconds() / 60) + 1
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail=f"Cuenta bloqueada. Intente en {minutos_restantes} min."
                )
            else:
                usuario.intentos_fallidos = 0
                usuario.bloqueado_hasta = None
                db.commit()

        password_valida = SecurityService.verificar_password(datos.password, usuario.password_hash)
        if not password_valida:
            usuario.intentos_fallidos += 1
            if usuario.intentos_fallidos >= 5:
                usuario.bloqueado_hasta = ahora + timedelta(minutes=15)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Demasiados intentos. Bloqueado por 15 minutos."
                )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Correo o contraseña incorrectos"
            )

        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None

        token_original = secrets.token_hex(32)
        token_hasheado = hashlib.sha256(token_original.encode('utf-8')).hexdigest()
        tiempo_expiracion = ahora + timedelta(hours=12) 
        
        nueva_sesion = Sesion(
            usuario_id=usuario.id, 
            token_sesion_hash=token_hasheado, 
            valida=True, 
            expira_en=tiempo_expiracion
        )
        db.add(nueva_sesion)
        db.commit() 

        return {
            "status": "success",
            "mensaje": "¡Inicio de sesión exitoso! 🎉",
            "access_token": token_original,
            "tipo_token": "bearer",
            "usuario": {
                "id": usuario.id,
                "email": usuario.email,
                "nombre": usuario.perfil.nombre,
                "apellido": usuario.perfil.apellido,
                "cargo": usuario.perfil.cargo,
                "ci": usuario.perfil.ci,
                "telefono": usuario.perfil.telefono
            }
        }

    @staticmethod
    def cerrar_sesion(db: Session, token_cliente: str) -> dict:
        token_hasheado = hashlib.sha256(token_cliente.encode('utf-8')).hexdigest()
        sesion_activa = db.query(Sesion).filter(Sesion.token_sesion_hash == token_hasheado).first()
        
        if not sesion_activa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión invalida o no encontrada"
            )
        
        sesion_activa.valida = False
        db.commit() 
        
        return {
            "status": "success",
            "mensaje": "Sesión cerrada correctamente. ¡El token ha muerto con éxito! 💀"
        }

    @staticmethod
    def obtener_perfil(usuario_actual: Usuario) -> dict:
        return {
            "status": "success",
            "mensaje": "¡Acceso concedido por el Guardián!",
            "datos_seguros": {
                "usuario_id": usuario_actual.id,
                "email": usuario_actual.email,
                "rol": usuario_actual.rol.nombre,
                "nombre": usuario_actual.perfil.nombre,
                "apellido": usuario_actual.perfil.apellido
            }
        }

    @staticmethod
    def actualizar_perfil(db: Session, usuario_actual: Usuario, datos: PerfilUpdateRequest) -> dict:
        if not usuario_actual.perfil:
            usuario_actual.perfil = Perfil(
                usuario_id=usuario_actual.id,
                ci="000000",
                nombre=datos.nombre,
                apellido=datos.apellido,
                telefono=datos.telefono,
                cargo="Operaciones"
            )
        else:
            usuario_actual.perfil.nombre = datos.nombre
            usuario_actual.perfil.apellido = datos.apellido
            usuario_actual.perfil.telefono = datos.telefono
        
        db.commit()
        db.refresh(usuario_actual.perfil)

        return {
            "status": "success",
            "mensaje": "Perfil actualizado correctamente 🎉",
            "usuario": {
                "id": usuario_actual.id,
                "email": usuario_actual.email,
                "nombre": usuario_actual.perfil.nombre,
                "apellido": usuario_actual.perfil.apellido,
                "cargo": usuario_actual.perfil.cargo,
                "ci": usuario_actual.perfil.ci,
                "telefono": usuario_actual.perfil.telefono
            }
        }

    @staticmethod
    def cambiar_password(db: Session, usuario_actual: Usuario, datos: CambiarPasswordRequest) -> dict:
        password_valida = SecurityService.verificar_password(datos.password_actual, usuario_actual.password_hash)
        if not password_valida:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña actual es incorrecta."
            )
        
        usuario_actual.password_hash = SecurityService.generar_hash(datos.nueva_password)
        db.commit()
        
        return {
            "status": "success",
            "mensaje": "Contraseña actualizada correctamente 🎉"
        }

    @staticmethod
    def solicitar_recuperacion(db: Session, datos: RecuperarPasswordRequest) -> dict:
        usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
        
        if not usuario:
            return {
                "status": "success",
                "mensaje": "Si el correo electrónico institucional existe, se han generado las instrucciones."
            }
            
        ahora = datetime.now(timezone.utc)
        token_original = secrets.token_hex(32)
        token_hasheado = hashlib.sha256(token_original.encode('utf-8')).hexdigest()
        tiempo_expiracion = ahora + timedelta(minutes=15)
        
        usuario.recuperar_password_token_hash = token_hasheado
        usuario.recuperar_password_expira = tiempo_expiracion
        db.commit()
        
        correo_enviado = EmailService.enviar_correo_recuperacion(usuario.email, token_original)
        
        if not correo_enviado:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="El token se generó, pero el servidor de correos falló al enviarlo."
            )
        
        return {
            "status": "success",
            "mensaje": "Las instrucciones de recuperación han sido enviadas a tu correo electrónico institucional. Revisa tu bandeja de entrada."
        }

    @staticmethod
    def restablecer_password(db: Session, datos: RestablecerPasswordRequest) -> dict:
        token_cliente_hash = hashlib.sha256(datos.token.encode('utf-8')).hexdigest()
        usuario = db.query(Usuario).filter(Usuario.recuperar_password_token_hash == token_cliente_hash).first()
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="El enlace de recuperación es inválido o ya fue utilizado."
            )
            
        ahora = datetime.now(timezone.utc)
        if ahora > usuario.recuperar_password_expira:
            usuario.recuperar_password_token_hash = None
            usuario.recuperar_password_expira = None
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="El enlace de recuperación ha expirado (Límite: 15 minutos)."
            )
            
        nueva_password_cifrada = SecurityService.generar_hash(datos.nueva_password)
        
        usuario.password_hash = nueva_password_cifrada
        usuario.recuperar_password_token_hash = None
        usuario.recuperar_password_expira = None
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        
        db.commit()
        
        return {
            "status": "success",
            "mensaje": "¡Contraseña actualizada con éxito! 🎉 Ya puedes iniciar sesión con tus nuevas credenciales."
        }
