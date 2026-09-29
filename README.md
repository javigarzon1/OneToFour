# OneToFour

**Autor: Javi Garzón**

Juego de preguntas y respuestas con cuatro opciones, desarrollado con **Vue 3**, **FastAPI**, **Python**, **Azure Databricks** y **Delta Lake**.

## Arquitectura

~~~text
Vue 3 + Vite
      │
      │ HTTP/JSON
      ▼
FastAPI
      │
      │ Databricks SQL Connector
      ▼
Azure Databricks SQL Warehouse
      │
      ▼
Delta Lake
      ├── quiz.preguntas
      └── quiz.resultados
~~~

El navegador nunca recibe las credenciales de Databricks. El backend mantiene esas credenciales en variables de entorno y realiza las consultas contra el SQL Warehouse.

## Funcionalidades

- Inicio de partidas con nombre del jugador.
- Selección del número de preguntas.
- Filtros por categoría y dificultad.
- Cuatro respuestas por pregunta.
- Puntuación automática.
- Persistencia de cada partida en Delta Lake.
- Ranking de mejores resultados.
- API REST documentada automáticamente por FastAPI.
- Endpoint de comprobación de conexión con Databricks.
- Modo demo del frontend si `VITE_API_URL` está vacío.

## Estructura

~~~text
OneToFour/
├── backend/
│   ├── app/
│   │   └── main.py
│   ├── .env.example
│   ├── .gitignore
│   ├── README.md
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── router/
│   │   ├── services/
│   │   ├── views/
│   │   ├── App.vue
│   │   └── main.js
│   ├── .env.example
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── data/
│   └── preguntas.csv
├── notebooks/
│   └── OneToFour.py
├── sql/
│   └── 01_crear_tablas.sql
├── jobs/
│   └── one_to_four_job.json
└── requirements.txt
~~~

## 1. Preparar Azure Databricks

Ejecuta `sql/01_crear_tablas.sql` en un SQL Warehouse de Azure Databricks.

Después carga las preguntas de `data/preguntas.csv` en `quiz.preguntas`, o ejecuta el notebook `notebooks/OneToFour.py` para preparar el banco de preguntas.

Las tablas utilizadas son:

### quiz.preguntas

- `id`
- `pregunta`
- `opcion_a`
- `opcion_b`
- `opcion_c`
- `opcion_d`
- `correcta`
- `categoria`
- `dificultad`

### quiz.resultados

- `partida_id`
- `jugador`
- `fecha`
- `puntuacion`
- `total_preguntas`
- `porcentaje`

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
CORS_ORIGINS=http://localhost:5173
~~~

Arranca:

~~~bash
uvicorn app.main:app --reload --port 8000
~~~

Comprobaciones:

- `http://localhost:8000/health`
- `http://localhost:8000/api/health/databricks`
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

## Endpoints de la API

### Obtener preguntas

~~~text
GET /api/questions?categoria=Programación&dificultad=Medio&limit=10
~~~

### Guardar una partida

~~~text
POST /api/games
Content-Type: application/json
~~~

~~~json
{
  "jugador": "Javi",
  "puntuacion": 8,
  "total_preguntas": 10,
  "porcentaje": 80
}
~~~

### Ranking

~~~text
GET /api/ranking
~~~

## Seguridad

- Las credenciales de Databricks solo existen en el backend.
- `.env` está excluido de Git.
- Los filtros y valores de escritura se envían como parámetros SQL.
- Para producción, utiliza OAuth/M2M con un service principal en lugar de depender de un token personal.

## Tecnologías

- Vue 3
- Vite
- Vue Router
- FastAPI
- Python
- Databricks SQL Connector
- Azure Databricks
- SQL Warehouse
- Delta Lake
- PySpark
