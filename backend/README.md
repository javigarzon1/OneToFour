# OneToFour API

Backend FastAPI para conectar Vue 3 con Azure Databricks.

## Requisitos

- Python 3.10+
- SQL Warehouse de Azure Databricks
- Permisos para consultar `quiz.preguntas` y escribir en `quiz.resultados`

El conector SQL de Databricks usa el hostname, HTTP path y una credencial de acceso. Para producción se recomienda OAuth/M2M con un service principal.

## Configuración

Copia `.env.example` a `.env` y define las variables de Databricks y `CORS_ORIGINS`.

No subas `.env` a GitHub.

## Instalación

Desde `backend/`:

~~~bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
~~~

## Endpoints

- `GET /health`
- `GET /api/health/databricks`
- `GET /api/questions`
- `POST /api/games`
- `GET /api/ranking`

La API usa consultas parametrizadas para filtros y escrituras.

Documentación interactiva: `/docs`.
