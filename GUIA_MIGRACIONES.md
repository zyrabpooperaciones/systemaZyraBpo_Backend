# Guía de Migraciones de Base de Datos con Alembic

Esta guía contiene los pasos y comandos necesarios para realizar modificaciones en la base de datos (añadir, modificar o eliminar tablas y columnas) utilizando **Alembic** sin perder la información que ya tienes almacenada.

---

## 📌 Requisito Previo
Antes de ejecutar cualquier comando de Alembic en la consola, **asegúrate siempre de tener tu entorno virtual activo**.

* En Windows (PowerShell / Terminal):
  ```powershell
  .\venv\Scripts\activate
  ```

---

## 🔄 Flujo de Trabajo Diario (Paso a Paso)

Cuando necesites realizar cambios en la estructura de tu base de datos, sigue este orden:

### Paso 1: Modifica tus Modelos de Python
Ve a tus modelos en [app/models/auth.py](file:///d:/Zyra%20BPO/Sistema%20Zyra%20BPO/web_backend/app/models/auth.py) (o crea nuevos archivos de modelos) y realiza el cambio en tus clases de SQLAlchemy.
* **Ejemplo de Adición:** Añadir `direccion = Column(String(200), nullable=True)` en la clase `Perfil`.
* **Ejemplo de Eliminación:** Borrar una columna de la clase en Python.

### Paso 2: Genera la Migración (Autodetectar Cambios)
Alembic comparará tus clases de Python con las tablas reales que tienes en PostgreSQL y generará un script de forma automática. Ejecuta en tu terminal:
```bash
python -m alembic revision --autogenerate -m "descripcion_de_los_cambios"
```
*Reemplaza `"descripcion_de_los_cambios"` por algo descriptivo (ej: `"agregar_direccion_a_perfil"`).*
* **¿Qué hace esto?** Crea un archivo script en Python dentro de la carpeta `alembic/versions/` detallando exactamente el cambio a nivel base de datos.

### Paso 3: Aplica los Cambios en Postgres (Upgrade)
Para enviar físicamente esos cambios a la base de datos de PostgreSQL local o de producción, ejecuta:
```bash
python -m alembic upgrade head
```
* **¿Qué hace esto?** Aplica la última migración disponible. **Tus datos existentes no se verán alterados ni borrados**, simplemente se adaptarán a la nueva estructura.

---

## 🛠️ Comandos Útiles de Respaldo

### ⏪ ¿Cometiste un error? (Deshacer el último cambio)
Si aplicaste una migración a la base de datos y te diste cuenta de que estaba mal estructurada, puedes volver exactamente un paso atrás en la base de datos:
```bash
python -m alembic downgrade -1
```
*(Luego puedes borrar el archivo creado en `alembic/versions` y corregir tu código).*

### 📜 Ver el historial de cambios de la base de datos
Para ver todas las migraciones que se han generado y cuáles están aplicadas:
```bash
python -m alembic history --verbose
```

### 📍 Ver en qué versión está la base de datos actualmente
Para saber cuál es la revisión actual que tiene estampada tu PostgreSQL:
```bash
python -m alembic current
```
