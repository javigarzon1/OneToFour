# Despliegue de OneToFour en Vercel

El repositorio está preparado para desplegar el frontend Vue/Vite y el backend FastAPI como dos servicios dentro del mismo proyecto de Vercel.

## Variables de entorno del backend

Configúralas en Vercel en **Settings → Environment Variables** para Production, Preview y Development según corresponda:

```text
GROQ_API_KEY=<clave de Groq>
GROQ_MODEL=qwen/qwen3.8-27b
DATABRICKS_SERVER_HOSTNAME=dbc-9ebf13e1-da41.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/7bf58be4bdba98ad
DATABRICKS_TOKEN=<Personal Access Token de Databricks>
```

No subas nunca estas credenciales a Git. `backend/.env` está ignorado por `.gitignore`.

`CORS_ORIGINS` no es necesario para las peticiones normales de la aplicación en Vercel porque frontend y backend se publican bajo el mismo dominio. Si se necesita acceso desde otro dominio, añádelo como variable de entorno.

## Arquitectura

- `frontend/`: aplicación Vue/Vite.
- `backend/`: FastAPI.
- `vercel.json`: configura ambos servicios y envía `/api/*` y `/health` al backend.
- El frontend usa rutas relativas en producción, por lo que no depende de una URL de Codespaces.

## Desarrollo local

Backend:

```bash
cd /workspaces/OneToFour
source .venv/bin/activate
set -a
source backend/.env
set +a
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd /workspaces/OneToFour/frontend
npm install
npm run dev
```

En local `frontend/.env` puede contener `VITE_API_URL=http://localhost:8000`.

## Vercel

Desde la raíz del repositorio:

```bash
npm install -g vercel@latest
vercel login
vercel deploy --prod
```

También se puede importar directamente el repositorio desde el panel de Vercel. El `vercel.json` de la raíz ya define frontend y backend.

## Comprobaciones después del despliegue

Sustituye `TU_DOMINIO` por el dominio asignado por Vercel:

```bash
curl -i https://TU_DOMINIO/health
curl -i https://TU_DOMINIO/api/health/ai
curl -i https://TU_DOMINIO/api/health/databricks
```

Después prueba la generación:

```bash
curl -X POST https://TU_DOMINIO/api/agent/generate \
  -H "Content-Type: application/json" \
  -d '{"numero_preguntas":10,"tema":"Naturaleza","dificultad":"Medio"}'
```

Y finalmente guarda una partida:

```bash
curl -X POST https://TU_DOMINIO/api/games \
  -H "Content-Type: application/json" \
  -d '{"jugador":"JaviPrueba","puntuacion":4,"total_preguntas":2,"porcentaje":100,"categoria":"Naturaleza","dificultad":"Medio","preguntas_ids":[]}'
```
