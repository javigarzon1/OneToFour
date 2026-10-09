# OneToFour

**Autor: Javi Garzón**

Juego de preguntas y respuestas con cuatro opciones, desarrollado con **Vue 3**, **FastAPI**, **Python**, **Azure Databricks**, **Delta Lake** y un agente IA sobre **Groq**.

## Arquitectura

~~~text
Vue 3 + Vite
      │
      │ HTTP/JSON
      ▼
FastAPI
  ┌───┴─────────────────────┐
  │                         │
  │ Groq API                │ Databricks SQL
  ▼                         ▼
Agente IA                 SQL Warehouse
                              │
                              ▼
                          Delta Lake
                           ├── quiz.preguntas
                           ├── quiz.resultados
                           └── quiz.preguntas_usadas
~~~

El navegador nunca recibe las credenciales de Groq ni de Databricks. El backend mantiene esas claves en variables de entorno.

## Funcionalidades

- Temporizador de 15 segundos por pregunta.
- Puntuación por dificultad y sistema de rachas.
- Feedback inmediato con explicación de la respuesta.
- Estadísticas agregadas desde Databricks por categoría y dificultad.
- Agente IA con Groq para crear partidas personalizadas por tema y dificultad.
- Generación de exactamente 10 preguntas por partida IA.
- Temas de videojuegos con selección de periodo, incluido **Años 90**.
- Historial de las últimas partidas.
- Inicio de partidas con nombre del jugador.
- Modo aleatorio que mezcla preguntas de diferentes categorías.
- Filtros por categoría y dificultad.
- Persistencia de cada partida en Delta Lake.
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

## 1. Preparar Azure Databricks

Ejecuta `sql/01_crear_tablas.sql` en un SQL Warehouse de Azure Databricks.

La tabla principal de preguntas es `workspace.quiz.preguntas`. Las partidas se guardan en `workspace.quiz.resultados` y el historial de anti-repetición en `workspace.quiz.preguntas_usadas`.

## 2. Arrancar la API

Desde `backend/`:

~~~bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
~~~

Copia `.env.example` a `.env` y completa:

~~~text
DATABRICKS_SERVER_HOSTNAME=...
DATABRICKS_HTTP_PATH=...
DATABRICKS_TOKEN=...
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
- En `/api/health/databricks`, si Databricks falla, la API indica la categoría del fallo y si falta alguna variable (sin mostrar credenciales).
- `http://localhost:8000/api/health/databricks`
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

El proyecto usa Vercel Services para publicar Vue y FastAPI en un único despliegue.

Las variables de producción de Databricks deben ser exactamente:

~~~text
DATABRICKS_SERVER_HOSTNAME=dbc-9ebf13e1-da41.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/7bf58be4bdba98ad
DATABRICKS_TOKEN=<token>
~~~

`DATABRICKS_SERVER_HOSTNAME` es solo el hostname del workspace. No debe contener el HTTP path del Warehouse. `DATABRICKS_HTTP_PATH` contiene exclusivamente la ruta `/sql/1.0/warehouses/...`.

Después de modificar variables de entorno en Vercel hay que crear un nuevo despliegue para que las funciones de FastAPI reciban los valores actualizados.

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

El workflow `.github/workflows/weekly-question-banks.yml` utiliza el secreto `GROQ_API_KEY` y lotes pequeños para respetar los límites del proveedor.

## Perfil, estadísticas y logros

La ruta `/estadisticas` muestra métricas calculadas en Databricks.

La ruta `/perfil` muestra partidas, puntos acumulados, mejores resultados, historial y logros desbloqueables.

No hay cuentas ni inicio de sesión. El nombre del jugador se conserva en el navegador.

## Pruebas y CI

El workflow de GitHub Actions compila el backend, ejecuta los tests, construye el frontend y comprueba la conexión con Databricks.

Para ejecutar los tests localmente:

~~~bash
pip install -r backend/requirements.txt
pytest -q backend/tests
~~~

## Configuración de GitHub Actions

Crea estos secretos:

- `DATABRICKS_TOKEN`
- `GROQ_API_KEY`

El hostname y el HTTP path del Warehouse se mantienen en los workflows. Las claves nunca se guardan en el repositorio.

## Seguridad

- Las credenciales de Databricks y Groq solo existen en el backend o en secretos de GitHub Actions.
- `.env` está excluido de Git.
- Las consultas SQL usan parámetros.
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
- Azure Databricks
- Databricks SQL Warehouse
- Delta Lake
- PySpark

## Estructura

~~~text
OneToFour/
├── backend/
│   ├── app/main.py
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
├── notebooks/OneToFour.py
├── sql/01_crear_tablas.sql
├── jobs/one_to_four_job.json
└── scripts/
    ├── generate_question_banks.py
    ├── sync_question_banks.py
    └── validate_question_banks.py
~~~
