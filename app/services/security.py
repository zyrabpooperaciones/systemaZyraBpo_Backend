import bcrypt

class SecurityService:
    
    @staticmethod
    def generar_hash(password_plana: str) -> str:
        """
        Toma una contraseña en texto plano (ej: '123456') 
        y la transforma en un hash seguro e indescifrable.
        """
        # Convertimos el texto a bytes
        password_bytes = password_plana.encode('utf-8')
        # Generamos la 'sal' (un extra de seguridad aleatorio)
        sal = bcrypt.gensalt()
        # Encriptamos
        hash_bytes = bcrypt.hashpw(password_bytes, sal)
        # Regresamos el hash como texto (string) listo para guardar en Postgres
        return hash_bytes.decode('utf-8')

    @staticmethod
    def verificar_password(password_plana: str, password_hash: str) -> bool:
        """
        Compara una contraseña escrita por el usuario con el hash guardado 
        en la base de datos. Devuelve True si coinciden o False si no.
        """
        try:
            return bcrypt.checkpw(
                password_plana.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except Exception:
            return False