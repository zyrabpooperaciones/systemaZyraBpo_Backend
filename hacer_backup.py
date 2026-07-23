import os
import sys
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "zyra_bpo_db")

def crear_backup():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backup_dir = os.path.join(base_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"backup_zyra_{timestamp}.dump"
    filepath = os.path.join(backup_dir, filename)

    print("====================================================")
    print("INICIANDO RESPALDO DE BASE DE DATOS (BACKUP)")
    print("====================================================")
    print(f"Base de Datos: {DB_NAME}")
    print(f"Destino: {filepath}")

    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    cmd = [
        "pg_dump",
        "-U", DB_USER,
        "-h", DB_HOST,
        "-p", DB_PORT,
        "-d", DB_NAME,
        "-F", "c",
        "-b",
        "-v",
        "-f", filepath
    ]

    try:
        subprocess.run(cmd, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        size_bytes = os.path.getsize(filepath)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        print("\n====================================================")
        print("¡RESPALDO COMPLETADO CON ÉXITO!")
        print(f"Archivo: {filename}")
        print(f"Tamaño: {size_mb} MB")
        print("====================================================")
        return filepath
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Falló la creación del respaldo: {e.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    crear_backup()
