# OneToFour API

Backend FastAPI para conectar Vue 3 con Azure Databricks y Groq.

## Requisitos

- Python 3.10+
- SQL Warehouse de Azure Databricks
- Una clave de Groq para el agente IA

## Configuración

Copia `.env.example` a `.env` y define las variables de Databricks, Groq y `CORS_ORIGINS`.

~~~text
DATABRICKS_SERVER_HOSTNAME=...
DATABRICKS_HTTP_PATH=...
DATABRICKS_TOKEN=...
GROQ_API_KEY=...
GROQ_MODEL=qwen/qwen3.8-27b
CORS_ORIGINS=http://localhost:5173
~~~

No subas `.env` a GitHub.

La API usa Groq como proveedor de generación. La clave se queda en el backend y nunca se envía al navegador.

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
- `GET /api/health/ai`
- `GET /api/questions`
- `POST /api/games`
- `GET /api/ranking`
- `GET /api/stats`
- `GET /api/player/{jugador}/profile`
- `GET /api/agent/options`
- `POST /api/agent/generate`

El endpoint de generación devuelve exactamente 10 preguntas en JSON estructurado y mantiene el mismo contrato que consume Vue.

La API usa consultas parametrizadas para filtros y escrituras y valida la salida del agente con JSON Schema estricto.

Documentación interactiva: `/docs`.

## Comprobación del agente

~~~bash
curl http://localhost:8000/api/health/ai
~~~

Debe indicar `provider: Groq`, el modelo configurado y si `GROQ_API_KEY` está presente.
