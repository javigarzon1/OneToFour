# OneToFour API

Backend FastAPI para conectar Vue 3 con PostgreSQL (Neon) y Groq.

## Requisitos

- Python 3.12
- Una base de datos PostgreSQL (Neon, plan gratuito)
- Una clave de Groq para el agente IA

## Configuración

Copia `.env.example` a `.env`:

~~~text
DATABASE_URL=postgresql://usuario:contrasena@ep-xxxx-pooler.region.aws.neon.tech/neondb?sslmode=require
GROQ_API_KEY=...
GROQ_MODEL=qwen/qwen3.8-27b
CORS_ORIGINS=http://localhost:5173
~~~

No subas `.env` a GitHub. Las claves se quedan en el backend y nunca se envían al navegador.

Crea las tablas con `sql/postgres/01_schema.sql` y carga el banco con `sql/postgres/02_seed_preguntas.sql`.

## Instalación

Desde `backend/`:

~~~bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
~~~

## Estructura

- `app/main.py`: rutas.
- `app/game.py`: reglas del juego (puntos, corrección, resultado). Sin base de datos.
- `app/db.py`: conexión a PostgreSQL.
- `app/limits.py`: utilidades del límite de uso.

## Endpoints

- `GET /health`
- `GET /api/health/db`
- `GET /api/health/ai`
- `POST /api/games/start`: crea una partida con preguntas del banco.
- `GET /api/games/{id}`: estado de la partida (para retomarla).
- `POST /api/games/{id}/answer`: corrige una respuesta.
- `POST /api/games/{id}/finish`: cierra la partida; la puntuación la calcula el servidor.
- `GET /api/ranking`: mejor partida de cada jugador.
- `GET /api/stats`
- `GET /api/player/{jugador}/profile`
- `GET /api/agent/options`
- `POST /api/agent/generate`: genera 10 preguntas con Groq y crea la partida. Limitado por IP y por día.

Las consultas usan parámetros (`%s`). La salida del agente se valida antes de guardarse.

Documentación interactiva: `/docs`.

## Tests

Desde la raíz del repositorio:

~~~bash
pip install -r backend/requirements.txt
PYTHONPATH=. pytest -q backend/tests
~~~
