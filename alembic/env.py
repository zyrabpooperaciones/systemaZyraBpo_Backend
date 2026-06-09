from logging.config import fileConfig
import sys
import os
from dotenv import load_dotenv

# Agregamos la raíz del proyecto al PYTHONPATH para resolver las importaciones de 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Cargamos las variables de entorno desde el archivo .env
load_dotenv()

# Construimos la URL de conexión a la base de datos de forma dinámica
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

if not all([DB_USER, DB_PASSWORD, DB_NAME]):
    raise ValueError("Faltan variables de entorno esenciales (DB_USER, DB_PASSWORD, DB_NAME) en tu archivo .env")

URL_BASE_DATOS = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Sobrescribimos la URL de conexión en la configuración con nuestra URL dinámica
config.set_main_option("sqlalchemy.url", URL_BASE_DATOS)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Importamos Base y los modelos de la base de datos para que Alembic reconozca la estructura de las tablas
from app.core.database import Base
from app.models.auth import Rol, Modulo, Usuario, Perfil, RolModuloNivel, Sesion

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
