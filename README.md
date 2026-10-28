# OneToFour

**Autor: Javi Garzón**

Juego de preguntas y respuestas con cuatro opciones, desarrollado con **Vue 3**, **FastAPI**, **Python**, **PostgreSQL (Neon)** y un agente IA sobre **Groq**.

## Arquitectura

~~~text
Vue 3 + Vite
      │
      │ HTTP/JSON
      ▼
FastAPI
  ┌───┴─────────────────────┐
  │                         │
  │ Groq API                │ PostgreSQL (Neon)
  ▼                         ▼
Agente IA                 quiz.preguntas
                          quiz.partidas
                          quiz.resultados
                          quiz.preguntas_usadas
                          quiz.limites_uso
~~~

El navegador nunca recibe las credenciales de Groq ni de la base de datos. El backend mantiene esas claves en variables de entorno.

## Funcionalidades

- Temporizador de 15 segundos por pregunta.
- Puntuación por dificultad y sistema de rachas.
- Feedback inmediato con explicación de la respuesta.
- Estadísticas agregadas por categoría y dificultad.
- Agente IA con Groq para crear partidas personalizadas por tema y dificultad.
- Generación de exactamente 10 preguntas por partida IA.
- Temas de videojuegos con selección de periodo, incluido **Años 90**.
- Historial de las últimas partidas.
- Inicio de partidas con nombre del jugador.
- Modo aleatorio que mezcla preguntas de diferentes categorías.
- Filtros por categoría y dificultad.
- La puntuación la calcula el servidor: el navegador no recibe las soluciones por adelantado ni envía su propio resultado.
- Límite de uso del agente IA por IP y por día.
- Persistencia de cada partida en PostgreSQL.
- Anti-repetición de preguntas del banco por jugador.
- Ranking de mejores resultados.
- Logros calculados desde el historial del jugador.
- API REST documentada automáticamente por FastAPI.

## Agente IA con Groq

El modo **Agente IA** llama desde FastAPI a Groq y mantiene un contrato estable para Vue. Cada solicitud genera exactamente 10 preguntas en español y la respuesta se valida con JSON Schema estricto.

El modelo por defecto es `qwen/qwen3.8-27b`, que Groq documenta como compatible con Structured Outputs en modo estricto. El nivel gratuito de Groq está sujeto a límites de solicitudes y tokens; no es ilimitado.

Configura en `backend/.env`:

~~~text
GROQ_API_KEY=tu_clave_de_groq
GROQ_MODEL=qwen/qwen3.8-27b
~~~

La clave permanece exclusivamente en el backend.

Documentación oficial:
- https://console.groq.com/docs/quickstart
- https://console.groq.com/docs/structured-outputs
- https://console.groq.com/docs/rate-limits

### Endpoints del agente

~~~text
GET  /api/health/ai
GET  /api/agent/options
POST /api/agent/generate
~~~

Ejemplo:

~~~json
{
  "numero_preguntas": 10,
  "tema": "Videojuegos — Años 90",
  "dificultad": "Medio"
}
~~~

Las preguntas generadas se guardan temporalmente en el navegador para iniciar la partida sin exponer la clave de Groq.

## 1. Preparar la base de datos (Neon)

Crea un proyecto en Neon y ejecuta, en este orden, `sql/postgres/01_schema.sql` y `sql/postgres/02_seed_preguntas.sql`. Son idempotentes. La guía completa está en [VERCEL.md](VERCEL.md).

## 2. Arrancar la API

Desde `backend/`:

~~~bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
~~~

Copia `.env.example` a `.env` y completa:

~~~text
DATABASE_URL=postgresql://usuario:contrasena@ep-xxxx-pooler.region.aws.neon.tech/neondb?sslmode=require
GROQ_API_KEY=...
GROQ_MODEL=qwen/qwen3.8-27b
CORS_ORIGINS=http://localhost:5173
~~~

Arranca:

~~~bash
uvicorn app.main:app --reload --port 8000
~~~

Comprobaciones:

- `http://localhost:8000/health`
- `http://localhost:8000/api/health/db`: si la base de datos falla, indica la categoría del fallo (sin mostrar credenciales).
- `http://localhost:8000/api/health/ai`
- `http://localhost:8000/docs`

## 3. Arrancar Vue 3

Desde `frontend/`:

~~~bash
npm install
~~~

Copia `.env.example` a `.env`:

~~~text
VITE_API_URL=http://localhost:8000
~~~

Y ejecuta:

~~~bash
npm run dev
~~~

Abre el frontend en `http://localhost:5173`.

## Producción en Vercel

El proyecto usa Vercel Services para publicar Vue y FastAPI en un único despliegue, con la base de datos en Neon. Variables de entorno, secretos y comprobaciones: [VERCEL.md](VERCEL.md).

## Banco de preguntas y anti-repetición

OneToFour dispone de bancos independientes en `data/question_banks/`.

Para generar o ampliar bancos con Groq:

~~~bash
python scripts/generate_question_banks.py --target 1200 --batch-size 20
~~~

Para añadir preguntas nuevas:

~~~bash
python scripts/generate_question_banks.py --new-per-topic 100 --batch-size 20
python scripts/sync_question_banks.py
~~~

El workflow `.github/workflows/weekly-question-banks.yml` utiliza los secretos `GROQ_API_KEY` y `DATABASE_URL` y lotes pequeños para respetar los límites del proveedor.

## Perfil, estadísticas y logros

La ruta `/estadisticas` muestra métricas calculadas en la base de datos.

La ruta `/perfil` muestra partidas, puntos acumulados, mejores resultados, historial y logros desbloqueables.

No hay cuentas ni inicio de sesión. El nombre del jugador se conserva en el navegador.

## Pruebas y CI

`.github/workflows/ci.yml` ejecuta los tests del backend, valida el esquema SQL contra un PostgreSQL real, ejecuta los tests del frontend y construye la web. `.github/workflows/health-check.yml` comprueba cada 6 horas que producción responde.

Para ejecutar los tests localmente:

~~~bash
pip install -r backend/requirements.txt
PYTHONPATH=. pytest -q backend/tests
cd frontend && pnpm test
~~~

## Configuración de GitHub Actions

Crea estos secretos:

- `DATABASE_URL`
- `GROQ_API_KEY`

Las claves nunca se guardan en el repositorio.

## Seguridad

- Las credenciales de la base de datos y de Groq solo existen en el backend o en secretos de GitHub Actions.
- `.env` está excluido de Git.
- Las consultas SQL usan parámetros.
- La puntuación se calcula en el servidor y las IP del límite de uso se guardan con hash.
- La salida del agente IA se valida con JSON Schema estricto.
- Los errores del proveedor se transforman en mensajes seguros para el frontend.

## Tecnologías

- Vue 3
- Vite
- Vue Router
- FastAPI
- Python
- Groq API
- Groq Python SDK
- PostgreSQL (Neon)
- psycopg 3

## Estructura

~~~text
OneToFour/
├── backend/
│   ├── app/ (main.py, game.py, db.py, limits.py)
│   ├── tests/
│   ├── .env.example
│   ├── README.md
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── .env.example
│   └── package.json
├── data/
│   ├── preguntas.csv
│   └── question_banks/
├── sql/postgres/          # esquema y banco inicial (PostgreSQL)
├── sql/legacy_databricks/ # versión antigua, sólo de referencia
├── notebooks/, jobs/      # versión antigua de Databricks (ya no se usa)
└── scripts/
    ├── generate_question_banks.py
    ├── sync_question_banks.py
    └── validate_question_banks.py
~~~
