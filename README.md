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

- Temporizador de 15 segundos por pregunta.
- Puntuación por dificultad y sistema de rachas.
- Feedback inmediato con explicación de la respuesta.
- Página de estadísticas con datos agregados desde Databricks por categoría y dificultad.
- Agente IA para crear partidas personalizadas por tema, dificultad y número de preguntas.
- Historial de las últimas partidas.

- Inicio de partidas con nombre del jugador.
- Selección del número de preguntas.
- Modo aleatorio que mezcla preguntas de diferentes categorías.
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
- `explicacion`

### quiz.resultados

- `partida_id`
- `jugador`
- `fecha`
- `puntuacion`
- `total_preguntas`
- `porcentaje`
- `categoria`
- `dificultad`

## Agente IA

El modo **Aleatorio** selecciona preguntas al azar entre las categorías disponibles y, cuando hay suficientes preguntas, alterna categorías para evitar que la partida se concentre en un único tema. También se puede mantener un filtro de dificultad.

El modo **Agente IA** permite seleccionar un tema (Historia, Cine, Ciencia, Deporte, Corazón, Naturaleza y otros), una dificultad y entre 1 y 20 preguntas. FastAPI envía la petición al modelo configurado mediante `OPENAI_API_KEY`, valida la respuesta estructurada y entrega las preguntas al frontend para iniciar la partida.

La clave de OpenAI permanece exclusivamente en el backend. Para habilitarlo localmente añade `OPENAI_API_KEY` y, opcionalmente, `OPENAI_MODEL` en `backend/.env`. En GitHub Actions, configura el secreto `OPENAI_API_KEY`.

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

## Estadísticas

La ruta `/estadisticas` muestra métricas calculadas en Databricks: partidas, jugadores, porcentaje medio, mejor puntuación, rendimiento por categoría y dificultad, y las últimas partidas.

## Endpoints de la API

### Obtener preguntas

~~~text
GET /api/questions?modo=aleatorio&dificultad=Medio&limit=10
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
  "porcentaje": 80,
  "categoria": "Programación",
  "dificultad": "Medio"
}
~~~

### Ranking

~~~text
GET /api/ranking
~~~

## Pruebas y CI

El workflow de GitHub Actions valida automáticamente el backend, ejecuta los tests, construye el frontend y comprueba la conexión con Databricks. También puede ejecutarse manualmente desde la pestaña Actions.

Para ejecutar los tests localmente desde la raíz:

~~~bash
pip install -r backend/requirements.txt
pytest -q backend/tests
~~~

## Seguridad

- Las credenciales de Databricks solo existen en el backend.
- `.env` está excluido de Git.
- Los filtros y valores de escritura se envían como parámetros SQL.
- Para producción, mantén las credenciales de Databricks exclusivamente en el backend.

## Configuración de GitHub Actions

Crea el secreto `DATABRICKS_TOKEN` en GitHub en **Settings → Secrets and variables → Actions**. El hostname y el HTTP path del Warehouse se mantienen en el workflow; el token nunca se guarda en el repositorio.

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

## Perfil, progreso y logros

La ruta `/perfil` muestra el progreso de un jugador a partir de las partidas almacenadas en Databricks. Incluye partidas jugadas, puntos acumulados, mejor puntuación, porcentaje medio, categorías exploradas e historial reciente.

También incorpora logros desbloqueables calculados a partir del historial:

- Primera partida.
- 5 y 10 partidas completadas.
- Una y tres partidas perfectas.
- 3 categorías diferentes.
- Una partida en dificultad difícil.

El nombre del jugador se conserva en el navegador para facilitar el acceso al perfil desde el menú **Mi progreso**. No hay cuentas ni inicio de sesión: el backend expone `GET /api/player/{jugador}/profile` y calcula los datos directamente sobre `workspace.quiz.resultados`.


## Banco de preguntas y anti-repetición

OneToFour dispone de 12 bancos independientes en `data/question_banks/`, uno por tema:

Historia, Cine, Ciencia, Deporte, Corazón, Naturaleza, Geografía, Tecnología, Música, Arte, Literatura y Cultura general.

El objetivo es mantener **1.200+ preguntas por categoría**. El agente IA puede completar el catálogo inicial y añadir 100 preguntas nuevas por categoría cada semana. El workflow `.github/workflows/weekly-question-banks.yml` se ejecuta semanalmente y también puede lanzarse manualmente desde GitHub Actions.

Las preguntas se sincronizan con `workspace.quiz.preguntas`. Además, `workspace.quiz.preguntas_usadas` registra las preguntas ya jugadas por cada jugador. El endpoint de preguntas excluye ese historial, por lo que un mismo jugador no vuelve a recibir una pregunta que ya haya completado.

Para inicializar el catálogo:

```bash
python scripts/generate_question_banks.py --target 1200 --batch-size 100
python scripts/sync_question_banks.py
```

Para una actualización semanal equivalente:

```bash
python scripts/generate_question_banks.py --target 1200 --new-per-topic 100 --batch-size 100
python scripts/sync_question_banks.py
```

La generación usa `OPENAI_API_KEY` y `OPENAI_MODEL`; nunca se deben guardar claves en los CSV ni en el repositorio.


## Despliegue del frontend

El frontend queda preparado para **GitHub Pages** mediante `.github/workflows/frontend-pages.yml`. Cada push a `main` que cambie `frontend/` genera y publica una nueva versión.

Para conectar Auth, partidas y Databricks desde la versión publicada, configura en **Settings → Secrets and variables → Actions → Variables** la variable:

`VITE_API_URL` = URL pública de la API FastAPI.

Si `VITE_API_URL` no está definida, el frontend funciona en modo demo y no puede realizar login real contra Databricks.

La URL prevista de GitHub Pages es:

`https://javigarzon1.github.io/OneToFour/`
