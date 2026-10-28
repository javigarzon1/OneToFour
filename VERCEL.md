# Despliegue de OneToFour en Vercel + Neon

Frontend Vue/Vite y backend FastAPI se publican como dos servicios del mismo proyecto de Vercel (`vercel.json`). La base de datos es **PostgreSQL en Neon** (plan gratuito).

## 1. Crear la base de datos en Neon

1. Crea un proyecto en [neon.com](https://neon.com) (o usa el que ya tengas).
2. En **Connect**, copia la cadena de conexión **con pooler** (el host contiene `-pooler`) y con `sslmode=require`.
3. Aplica el esquema y el banco de preguntas (desde el SQL Editor de Neon, o con `psql`):

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/postgres/01_schema.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/postgres/02_seed_preguntas.sql
psql "$DATABASE_URL" -f sql/postgres/03_verificar.sql   # opcional: debe mostrar 130 preguntas
```

Los scripts son idempotentes: se pueden ejecutar varias veces.

## 2. Variables de entorno en Vercel

**Settings → Environment Variables** (Production y Preview):

```text
DATABASE_URL=<cadena de conexión de Neon con pooler>
GROQ_API_KEY=<clave de Groq>
GROQ_MODEL=qwen/qwen3.8-27b
```

La integración de Neon para Vercel crea `DATABASE_URL` y `POSTGRES_URL` automáticamente; el backend acepta cualquiera de las dos.

Opcionales, para el límite de uso del agente IA (valores por defecto entre paréntesis):

```text
AGENT_RATE_LIMIT=5              # generaciones por IP y ventana (5)
AGENT_RATE_WINDOW_SECONDS=600   # duración de la ventana en segundos (600)
AGENT_DAILY_LIMIT=300           # tope diario total (300)
RATE_LIMIT_SALT=<texto secreto> # sal para anonimizar las IP
```

Después de cambiar variables hay que crear un **nuevo despliegue**. No subas nunca estas credenciales a Git: `backend/.env` está en `.gitignore`.

`CORS_ORIGINS` no hace falta en Vercel porque frontend y backend comparten dominio.

## 3. Secretos de GitHub Actions

En **Settings → Secrets and variables → Actions**:

- `DATABASE_URL` (para sincronizar el banco de preguntas cada semana)
- `GROQ_API_KEY`
- Variable opcional `PRODUCTION_URL` (por defecto `https://onetofour.vercel.app`) para la comprobación periódica de producción.

## Arquitectura

- `frontend/`: Vue 3 + Vite (gestor de paquetes: **pnpm**).
- `backend/`: FastAPI. `app/main.py` (rutas), `app/game.py` (reglas), `app/db.py` (conexión), `app/limits.py` (límite de uso).
- `sql/postgres/`: esquema y banco inicial. `sql/legacy_databricks/`: versión antigua, sólo de referencia.
- `vercel.json`: envía `/api/*` y `/health` al backend y el resto al frontend.

## Cómo funciona una partida

El servidor guarda las preguntas (con su solución) y corrige cada respuesta; el navegador nunca recibe la respuesta correcta por adelantado ni envía su puntuación.

1. `POST /api/games/start` (banco) o `POST /api/agent/generate` (IA) crean la partida y devuelven `partida_id` y las preguntas **sin solución**.
2. `POST /api/games/{id}/answer` corrige una pregunta y devuelve la solución y la explicación.
3. `POST /api/games/{id}/finish` calcula la puntuación en el servidor y la guarda en el ranking.
4. `GET /api/games/{id}` permite retomar la partida si se recarga la página.

## Desarrollo local

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # rellena DATABASE_URL y GROQ_API_KEY
uvicorn app.main:app --port 8000
```

Frontend:

```bash
cd frontend
pnpm install
pnpm dev                    # el proxy de Vite reenvía /api al puerto 8000
```

Tests:

```bash
PYTHONPATH=. pytest -q backend/tests    # desde la raíz del repo
cd frontend && pnpm test
```

## Comprobaciones después del despliegue

Sustituye `TU_DOMINIO` por el dominio de Vercel:

```bash
curl -i https://TU_DOMINIO/health
curl -i https://TU_DOMINIO/api/health/db
curl -i https://TU_DOMINIO/api/health/ai
```

`/api/health/db` devuelve `"database": true` si todo va bien; si falla indica `error_category` (`configuration_missing`, `authentication_or_authorization`, `timeout`, `schema_missing` o `connection_error`).

Prueba una partida completa del banco:

```bash
curl -X POST https://TU_DOMINIO/api/games/start \
  -H "Content-Type: application/json" \
  -d '{"jugador":"JaviPrueba","categoria":"Historia","dificultad":"Todas"}'
```
