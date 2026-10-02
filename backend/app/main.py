import json
import logging
import os
import uuid
from pathlib import Path
from contextlib import closing

from databricks import sql
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from pydantic import BaseModel, Field

logger = logging.getLogger("onetoFour")

# Carga automáticamente backend/.env en desarrollo local/Codespaces.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

AI_CATEGORIES = [
    "Historia",
    "Cine",
    "Ciencia",
    "Deporte",
    "Corazón",
    "Naturaleza",
    "Geografía",
    "Tecnología",
    "Música",
    "Arte",
    "Literatura",
    "Cultura general",
    "Videojuegos",
]
AI_DIFFICULTIES = ["Fácil", "Medio", "Difícil"]
DEFAULT_GROQ_MODEL = "qwen/qwen3.8-27b"


class GenerateQuizRequest(BaseModel):
    numero_preguntas: int = Field(default=10, ge=10, le=10)
    tema: str = Field(min_length=2, max_length=80)
    dificultad: str = Field(pattern="^(Fácil|Medio|Difícil)$")


class GameCreate(BaseModel):
    jugador: str = Field(min_length=1, max_length=30)
    puntuacion: int = Field(ge=0)
    total_preguntas: int = Field(gt=0, le=10)
    porcentaje: float = Field(ge=0, le=100)
    categoria: str = "Todas"
    dificultad: str = "Todas"
    preguntas_ids: list[int] = Field(default_factory=list, max_length=10)


app = FastAPI(title="OneToFour API", version="1.1.0")

allowed_origins = [
    item.strip()
    for item in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if item.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.app\.github\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_connection():
    required = [
        "DATABRICKS_SERVER_HOSTNAME",
        "DATABRICKS_HTTP_PATH",
        "DATABRICKS_TOKEN",
    ]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Faltan variables de entorno de Databricks: " + ", ".join(missing)
        )

    token = os.environ["DATABRICKS_TOKEN"].strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    return sql.connect(
        server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"].strip(),
        http_path=os.environ["DATABRICKS_HTTP_PATH"].strip(),
        access_token=token,
        autocommit=True,
    )


def rows_as_dicts(cursor):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def build_achievements(summary):
    partidas = int(summary.get("partidas") or 0)
    perfectas = int(summary.get("perfectas") or 0)
    categorias = int(summary.get("categorias") or 0)
    dificiles = int(summary.get("dificiles") or 0)

    return [
        {
            "id": "primera",
            "icono": "🎮",
            "titulo": "Primera partida",
            "descripcion": "Completa tu primera partida.",
            "desbloqueado": partidas >= 1,
        },
        {
            "id": "cinco",
            "icono": "🔥",
            "titulo": "En racha",
            "descripcion": "Completa 5 partidas.",
            "desbloqueado": partidas >= 5,
        },
        {
            "id": "diez",
            "icono": "🏆",
            "titulo": "Veterano",
            "descripcion": "Completa 10 partidas.",
            "desbloqueado": partidas >= 10,
        },
        {
            "id": "perfecta",
            "icono": "💯",
            "titulo": "Partida perfecta",
            "descripcion": "Consigue el 100% en una partida.",
            "desbloqueado": perfectas >= 1,
        },
        {
            "id": "perfectas_tres",
            "icono": "⭐",
            "titulo": "Tres perfectas",
            "descripcion": "Consigue 3 partidas con el 100%.",
            "desbloqueado": perfectas >= 3,
        },
        {
            "id": "categorias_tres",
            "icono": "🧠",
            "titulo": "Explorador",
            "descripcion": "Juega en 3 categorías diferentes.",
            "desbloqueado": categorias >= 3,
        },
        {
            "id": "dificil",
            "icono": "⚡",
            "titulo": "Sin miedo",
            "descripcion": "Completa una partida en dificultad difícil.",
            "desbloqueado": dificiles >= 1,
        },
    ]


@app.get("/health")
def health():
    return {"status": "ok", "service": "onetoFour-api"}


@app.get("/api/health/databricks")
def databricks_health():
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("SELECT 1 AS ok")
                return {"status": "ok", "databricks": cursor.fetchone()[0] == 1}
    except Exception:
        logger.exception("Error conectando con Databricks")
        raise HTTPException(503, "Databricks no disponible.")


@app.get("/api/health/ai")
def ai_health():
    return {
        "status": "ok" if bool(os.getenv("GROQ_API_KEY")) else "missing_configuration",
        "provider": "Groq",
        "model": os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL),
        "configured": bool(os.getenv("GROQ_API_KEY")),
    }


@app.get("/api/agent/options")
def agent_options():
    return {
        "categorias": AI_CATEGORIES,
        "dificultades": AI_DIFFICULTIES,
        "max_preguntas": 10,
        "proveedor": "Groq",
        "modelo": os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL),
    }


@app.post("/api/agent/generate")
def generate_quiz(request: GenerateQuizRequest):
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(
            503,
            "El agente IA no está configurado. Añade GROQ_API_KEY al backend.",
        )

    schema = {
        "type": "object",
        "properties": {
            "preguntas": {
                "type": "array",
                "minItems": 10,
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "properties": {
                        "pregunta": {"type": "string"},
                        "opcion_a": {"type": "string"},
                        "opcion_b": {"type": "string"},
                        "opcion_c": {"type": "string"},
                        "opcion_d": {"type": "string"},
                        "correcta": {
                            "type": "string",
                            "enum": ["A", "B", "C", "D"],
                        },
                        "categoria": {"type": "string"},
                        "dificultad": {
                            "type": "string",
                            "enum": AI_DIFFICULTIES,
                        },
                        "explicacion": {"type": "string"},
                    },
                    "required": [
                        "pregunta",
                        "opcion_a",
                        "opcion_b",
                        "opcion_c",
                        "opcion_d",
                        "correcta",
                        "categoria",
                        "dificultad",
                        "explicacion",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["preguntas"],
        "additionalProperties": False,
    }

    prompt = (
        f"Genera exactamente 10 preguntas exclusivamente sobre el tema: {request.tema}. "
        f"Dificultad exacta: {request.dificultad}. Escribe todo en español. "
        "No uses preguntas de otros temas. "
        "Si el tema contiene una época, periodo, saga, género, competición o subtema, "
        "todas las preguntas deben respetarlo. "
        "Cada pregunta debe tener cuatro opciones plausibles, una sola correcta "
        "y una explicación factual breve. Todas deben ser distintas. "
        "La propiedad categoria debe corresponder al tema principal y la propiedad "
        "dificultad debe ser exactamente la solicitada. "
        "Evita opiniones, rumores, ambigüedades y datos cuya respuesta dependa de "
        "acontecimientos futuros."
    )

    model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    try:
        client = Groq(api_key=os.environ["GROQ_API_KEY"])
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres el agente de preguntas de OneToFour. "
                        "Respeta estrictamente el tema y la dificultad solicitados. "
                        "Genera contenido factual y apto para público general."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "onetoFour_quiz",
                    "strict": True,
                    "schema": schema,
                },
            },
            temperature=0.7,
            reasoning_effort="low",
            max_completion_tokens=6000,
        )

        content = response.choices[0].message.content or "{}"
        data = json.loads(content)

        questions = data.get("preguntas", [])
        if len(questions) != 10:
            raise ValueError("El agente no generó exactamente 10 preguntas.")

        return {
            "preguntas": questions,
            "tema": request.tema,
            "dificultad": request.dificultad,
            "generado_por": f"Groq · {model}",
        }
    except Exception as exc:
        status_code = getattr(exc, "status_code", None)

        if status_code in {401, 403}:
            logger.warning("Credenciales Groq rechazadas (modelo=%s)", model)
            raise HTTPException(
                503,
                "La clave de Groq no es válida o no tiene acceso al servicio.",
            )

        if status_code == 429:
            logger.warning("Límite de Groq alcanzado (modelo=%s)", model)
            raise HTTPException(
                429,
                "Groq ha alcanzado temporalmente el límite de uso. "
                "Espera unos segundos y vuelve a intentarlo.",
            )

        logger.exception("Error generando preguntas con Groq (modelo=%s)", model)
        raise HTTPException(
            502,
            "No se pudieron generar las preguntas con el agente IA. "
            "Revisa la configuración de Groq o inténtalo de nuevo.",
        )


@app.get("/api/questions")
def get_questions(
    categoria: str | None = Query(None, max_length=80),
    dificultad: str | None = Query(None, max_length=30),
    modo: str = Query("normal", pattern="^(normal|aleatorio)$"),
    limit: int = Query(10, ge=1, le=10),
    jugador: str | None = Query(None, max_length=30),
):
    filters = []
    params = []

    if modo == "normal" and categoria and categoria not in ("Todas", "Aleatorio"):
        filters.append("p.categoria = ?")
        params.append(categoria)

    if dificultad and dificultad != "Todas":
        filters.append("p.dificultad = ?")
        params.append(dificultad)

    filters.append(
        "NOT EXISTS ("
        "SELECT 1 FROM workspace.quiz.preguntas_usadas u "
        "WHERE u.jugador = ? AND u.pregunta_id = p.id"
        ")"
    )
    params.append((jugador or "Jugador").strip())

    query = (
        "SELECT p.id,p.pregunta,p.opcion_a,p.opcion_b,p.opcion_c,p.opcion_d,"
        "p.correcta,p.categoria,p.dificultad,p.explicacion "
        "FROM workspace.quiz.preguntas p WHERE "
        + " AND ".join(filters)
        + " ORDER BY rand() LIMIT ?"
    )
    params.append(limit)

    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(query, params)
                return rows_as_dicts(cursor)
    except Exception:
        logger.exception("Error consultando preguntas")
        raise HTTPException(503, "No se pudieron consultar las preguntas.")


@app.post("/api/games")
def save_game(game: GameCreate):
    partida_id = str(uuid.uuid4())

    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    "INSERT INTO workspace.quiz.resultados "
                    "(partida_id,jugador,fecha,puntuacion,total_preguntas,porcentaje,categoria,dificultad) "
                    "VALUES (?, ?, current_timestamp(), ?, ?, ?, ?, ?)",
                    [
                        partida_id,
                        game.jugador.strip(),
                        game.puntuacion,
                        game.total_preguntas,
                        game.porcentaje,
                        game.categoria.strip(),
                        game.dificultad.strip(),
                    ],
                )

                for question_id in dict.fromkeys(game.preguntas_ids):
                    cursor.execute(
                        "INSERT INTO workspace.quiz.preguntas_usadas "
                        "(jugador,pregunta_id,partida_id,fecha_uso) "
                        "VALUES (?, ?, ?, current_timestamp())",
                        [
                            game.jugador.strip(),
                            question_id,
                            partida_id,
                        ],
                    )

        return {
            "partida_id": partida_id,
            "jugador": game.jugador.strip(),
            "puntuacion": game.puntuacion,
            "total_preguntas": game.total_preguntas,
            "porcentaje": game.porcentaje,
            "categoria": game.categoria,
            "dificultad": game.dificultad,
        }
    except Exception as exc:
        logger.exception("Error guardando partida")
        status_code = getattr(exc, "status_code", None)
        if status_code in {401, 403} or "access token" in str(exc).lower() or "credential" in str(exc).lower():
            raise HTTPException(
                503,
                "No se pudo guardar la partida porque las credenciales de Databricks no son válidas o no son compatibles con este conector.",
            )
        raise HTTPException(503, "No se pudo guardar la partida en Databricks.")


@app.get("/api/ranking")
def get_ranking():
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    "SELECT jugador,MAX(puntuacion) AS puntuacion,"
                    "MAX(porcentaje) AS porcentaje "
                    "FROM workspace.quiz.resultados "
                    "GROUP BY jugador "
                    "ORDER BY porcentaje DESC,puntuacion DESC,jugador ASC LIMIT 20"
                )
                return rows_as_dicts(cursor)
    except Exception:
        logger.exception("Error consultando ranking")
        raise HTTPException(503, "No se pudo consultar el ranking.")


@app.get("/api/stats")
def get_stats():
    queries = {
        "summary": (
            "SELECT COUNT(*) AS partidas,COUNT(DISTINCT jugador) AS jugadores,"
            "ROUND(AVG(porcentaje),2) AS porcentaje_medio,"
            "MAX(puntuacion) AS mejor_puntuacion "
            "FROM workspace.quiz.resultados"
        ),
        "categories": (
            "SELECT categoria,COUNT(*) AS partidas,"
            "ROUND(AVG(porcentaje),2) AS porcentaje_medio,"
            "MAX(porcentaje) AS mejor_porcentaje "
            "FROM workspace.quiz.resultados "
            "WHERE categoria IS NOT NULL AND categoria <> 'Todas' "
            "GROUP BY categoria ORDER BY porcentaje_medio DESC,partidas DESC"
        ),
        "difficulties": (
            "SELECT dificultad,COUNT(*) AS partidas,"
            "ROUND(AVG(porcentaje),2) AS porcentaje_medio "
            "FROM workspace.quiz.resultados "
            "WHERE dificultad IS NOT NULL AND dificultad <> 'Todas' "
            "GROUP BY dificultad ORDER BY porcentaje_medio DESC"
        ),
        "recent": (
            "SELECT jugador,puntuacion,total_preguntas,porcentaje,"
            "categoria,dificultad,fecha "
            "FROM workspace.quiz.resultados ORDER BY fecha DESC LIMIT 10"
        ),
    }

    try:
        with closing(get_connection()) as connection:
            result = {}

            for name, query in queries.items():
                with closing(connection.cursor()) as cursor:
                    cursor.execute(query)
                    result[name] = rows_as_dicts(cursor)

        return result
    except Exception:
        logger.exception("Error consultando estadísticas")
        raise HTTPException(503, "No se pudieron consultar las estadísticas.")


@app.get("/api/player/{jugador}/profile")
def get_player_profile(jugador: str):
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    "SELECT COUNT(*) AS partidas,"
                    "COALESCE(SUM(puntuacion),0) AS puntos_totales,"
                    "COALESCE(MAX(puntuacion),0) AS mejor_puntuacion,"
                    "COALESCE(MAX(porcentaje),0) AS mejor_porcentaje,"
                    "COALESCE(ROUND(AVG(porcentaje),2),0) AS porcentaje_medio,"
                    "COUNT(DISTINCT CASE WHEN categoria IS NOT NULL "
                    "AND categoria <> 'Todas' THEN categoria END) AS categorias,"
                    "COUNT(CASE WHEN porcentaje=100 THEN 1 END) AS perfectas,"
                    "COUNT(CASE WHEN dificultad='Difícil' THEN 1 END) AS dificiles "
                    "FROM workspace.quiz.resultados WHERE jugador=?",
                    [jugador.strip()],
                )
                summary = rows_as_dicts(cursor)[0]

            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    "SELECT puntuacion,total_preguntas,porcentaje,categoria,"
                    "dificultad,fecha FROM workspace.quiz.resultados "
                    "WHERE jugador=? ORDER BY fecha DESC LIMIT 8",
                    [jugador.strip()],
                )
                recent = rows_as_dicts(cursor)

        return {
            "jugador": jugador.strip(),
            "summary": summary,
            "achievements": build_achievements(summary),
            "recent": recent,
        }
    except Exception:
        logger.exception("Error consultando perfil")
        raise HTTPException(503, "No se pudo consultar el perfil.")
