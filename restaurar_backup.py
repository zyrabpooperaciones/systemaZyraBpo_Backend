import os
import sys
import subprocess
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "zyra_bpo_db")

def restaurar_backup(filepath=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backup_dir = os.path.join(base_dir, "backups")

    if not filepath:
        if not os.path.exists(backup_dir):
            print("[ERROR] No existe la carpeta de respaldos.")
            return
        files = [f for f in os.listdir(backup_dir) if f.endswith(".dump") or f.endswith(".sql")]
        if not files:
            print("[ERROR] No hay archivos de respaldo en la carpeta backups/.")
            return
        files.sort(reverse=True)
        filename = files[0]
        filepath = os.path.join(backup_dir, filename)

    print("====================================================")
    print("INICIANDO RESTAURACIÓN DE BASE DE DATOS")
    print("====================================================")
    print(f"Restaurando desde: {filepath}")

    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    cmd = [
        "pg_restore",
        "-U", DB_USER,
        "-h", DB_HOST,
        "-p", DB_PORT,
        "-d", DB_NAME,
        "--clean",
        "--if-exists",
        "-v",
        filepath
    ]

    try:
        subprocess.run(cmd, env=env, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("\n====================================================")
        print("¡RESTAURACIÓN COMPLETADA CON ÉXITO!")
        print("====================================================")
    except Exception as e:
        print(f"\n[ERROR] Error al restaurar: {str(e)}")

if __name__ == "__main__":
    restaurar_backup()
