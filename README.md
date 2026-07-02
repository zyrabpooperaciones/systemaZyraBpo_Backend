# Backend - Sistema Zyra BPO

Este es el backend del sistema Zyra BPO, desarrollado con **FastAPI** (Python) y **PostgreSQL** como base de datos. Utiliza **SQLAlchemy** como ORM y **Alembic** para el control de versiones y migraciones de la base de datos.

## Requisitos Previos

Antes de ejecutar este proyecto, asegúrate de tener instalado en tu sistema:

- **Python 3.8+** (Recomendado 3.10 o superior)
- **PostgreSQL** (Servidor de base de datos en ejecución)
- **Git** (Para clonar el repositorio)

---

## 🛠️ Instalación y Configuración Local

Sigue estos pasos para levantar el entorno de desarrollo en tu máquina local:

### 1. Clonar el repositorio

Abre tu terminal y ejecuta:

```bash
git clone <URL_DEL_REPOSITORIO>
cd web_backend
```

### 2. Crear y activar el entorno virtual

Es una buena práctica aislar las dependencias del proyecto usando un entorno virtual.

**En Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**En Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

*(Sabrás que está activado porque aparecerá `(venv)` al inicio de tu línea de comandos).*

### 3. Instalar las dependencias

Con el entorno virtual activado, instala todas las librerías necesarias:

```bash
pip install -r requirements.txt
```

### 4. Configurar las Variables de Entorno

El proyecto requiere ciertas configuraciones privadas (credenciales de base de datos, correos, etc.) que no se suben a Git por seguridad.

1. Crea un archivo llamado `.env` en la raíz del proyecto (al mismo nivel que `main.py`).
2. Copia el contenido del archivo de ejemplo llamado `.env.example` y pégalo dentro de tu nuevo `.env`.
3. Reemplaza los valores de ejemplo con tus credenciales reales (por ejemplo, tu contraseña de PostgreSQL).

**Ejemplo de cómo debe verse tu `.env`:**
```ini
DB_USER=postgres
DB_PASSWORD=tu_contraseña_real_aqui
DB_HOST=localhost
DB_PORT=5432
DB_NAME=zyra_bpo_db
...
```

### 5. Configurar la Base de Datos

Asegúrate de haber creado una base de datos vacía en PostgreSQL con el mismo nombre que pusiste en tu variable `DB_NAME` (por defecto `zyra_bpo_db`).

Luego, para crear todas las tablas, ejecuta las migraciones de Alembic:

```bash
alembic upgrade head
```
*(Para más información sobre migraciones, revisa el archivo `GUIA_MIGRACIONES.md`).*

---

## 🚀 Ejecutar el Servidor

Una vez completados los pasos anteriores, puedes iniciar el servidor de desarrollo ejecutando:

```bash
uvicorn main:app --reload
```

El servidor estará corriendo en: **`http://localhost:8000`**

### Documentación de la API (Swagger UI)

FastAPI genera documentación interactiva automáticamente. Mientras el servidor esté corriendo, puedes acceder a ella en tu navegador web:

- Swagger UI: **[http://localhost:8000/docs](http://localhost:8000/docs)**
- ReDoc: **[http://localhost:8000/redoc](http://localhost:8000/redoc)**

---

## 📂 Estructura del Proyecto

```text
web_backend/
│
├── alembic/                # Scripts de migración de la base de datos
├── app/                    # Código fuente principal de la aplicación
│   ├── core/               # Configuraciones generales (Base de datos, seguridad, etc.)
│   ├── models/             # Modelos de SQLAlchemy (Tablas de la BD)
│   ├── routes/             # Controladores/Endpoints de la API (Rutas)
│   └── services/           # Lógica de negocio
│
├── venv/                   # Entorno virtual (Ignorado por Git)
├── .env                    # Variables de entorno secretas (Ignorado por Git)
├── .env.example            # Plantilla de variables de entorno
├── .gitignore              # Archivos excluidos del control de versiones
├── alembic.ini             # Configuración de Alembic
├── main.py                 # Punto de entrada de la aplicación FastAPI
└── requirements.txt        # Lista de dependencias del proyecto
```

## 📝 Notas Adicionales

- Si agregas nuevas librerías al proyecto, recuerda actualizar el archivo de dependencias ejecutando: `pip freeze > requirements.txt`

venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000


