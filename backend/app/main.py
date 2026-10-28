import json
import logging
import os
import re
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from .db import database_url, get_connection
from .game import (
    GameError,
    final_result,
    public_question,
    public_state,
    register_answer,
    stored_question,
)
from .limits import client_ip, env_int, rate_key, retry_after, window_start

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
GROQ_TIMEOUT_SECONDS = 45.0
QUESTIONS_PER_GAME = 10


class GenerateQuizRequest(BaseModel):
    numero_preguntas: int = Field(default=10, ge=10, le=10)
    tema: str = Field(min_length=2, max_length=80)
    dificultad: str = Field(pattern="^(Fácil|Medio|Difícil)$")
    jugador: str = Field(default="Jugador", min_length=1, max_length=30)


class StartGameRequest(BaseModel):
    jugador: str = Field(default="Jugador", min_length=1, max_length=30)
    categoria: str = Field(default="Todas", max_length=80)
    dificultad: str = Field(default="Todas", pattern="^(Todas|Fácil|Medio|Difícil)$")
    modo: str = Field(default="normal", pattern="^(normal|aleatorio)$")


class AnswerRequest(BaseModel):
    indice: int = Field(ge=0, le=QUESTIONS_PER_GAME - 1)
    # Una letra A-D, o cadena vacía si se agotó el tiempo.
    respuesta: str = Field(default="", pattern="^[A-D]?$")


app = FastAPI(title="OneToFour API", version="2.0.0")

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


@app.get("/api/health/db")
def database_health():
    configured = {"database_url": database_url() is not None}

    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok")
            row = cursor.fetchone()
            return {
                "status": "ok",
                "database": bool(row and row["ok"] == 1),
                "configured": configured,
            }
    except Exception as exc:
        logger.exception("Error conectando con la base de datos")
        message = str(exc).lower()
        if not all(configured.values()):
            category = "configuration_missing"
        elif "password authentication" in message or "authentication" in message:
            category = "authentication_or_authorization"
        elif isinstance(exc, TimeoutError) or "timeout" in message or "timed out" in message:
            category = "timeout"
        elif "does not exist" in message or "relation" in message:
            category = "schema_missing"
        else:
            category = "connection_error"

        raise HTTPException(
            503,
            {
                "status": "error",
                "database": False,
                "configured": configured,
                "error_category": category,
                "error_type": type(exc).__name__,
            },
        )


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


def normalize_generated_text(value):
    """Normaliza texto generado sin alterar su significado."""
    if not isinstance(value, str):
        raise ValueError("El agente devolvió un campo que no es texto.")

    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s+([,.;:?!])", r"\1", value)
    return value


def validate_generated_questions(questions, request):
    """Valida y limpia las preguntas antes de enviarlas al frontend."""
    if not isinstance(questions, list) or len(questions) != 10:
        raise ValueError("El agente no generó exactamente 10 preguntas.")

    expected_category = request.tema.split("—", 1)[0].strip()
    if expected_category not in AI_CATEGORIES:
        expected_category = request.tema.strip()

    required_fields = (
        "pregunta",
        "opcion_a",
        "opcion_b",
        "opcion_c",
        "opcion_d",
        "correcta",
        "categoria",
        "dificultad",
        "explicacion",
    )
    validated = []
    seen_questions = set()
    correct_distribution = {letter: 0 for letter in "ABCD"}

    for index, raw_question in enumerate(questions, start=1):
        if not isinstance(raw_question, dict):
            raise ValueError(f"La pregunta {index} no tiene un formato válido.")

        missing = [field for field in required_fields if field not in raw_question]
        if missing:
            raise ValueError(
                f"La pregunta {index} no contiene todos los campos requeridos."
            )

        question = {
            field: normalize_generated_text(raw_question[field])
            for field in required_fields
        }

        if any(not question[field] for field in required_fields if field != "correcta"):
            raise ValueError(f"La pregunta {index} contiene campos vacíos.")

        if len(question["pregunta"]) < 10:
            raise ValueError(f"La pregunta {index} es demasiado corta.")

        options = [
            question["opcion_a"],
            question["opcion_b"],
            question["opcion_c"],
            question["opcion_d"],
        ]
        normalized_options = [option.casefold() for option in options]
        if len(set(normalized_options)) != 4:
            raise ValueError(f"La pregunta {index} contiene opciones repetidas.")

        if question["correcta"] not in {"A", "B", "C", "D"}:
            raise ValueError(f"La pregunta {index} tiene una respuesta correcta inválida.")

        correct_index = "ABCD".index(question["correcta"])
        if not options[correct_index]:
            raise ValueError(f"La pregunta {index} no tiene una opción correcta válida.")

        if question["dificultad"] != request.dificultad:
            raise ValueError(
                f"La pregunta {index} no respeta la dificultad solicitada."
            )

        if question["categoria"] != expected_category:
            raise ValueError(
                f"La pregunta {index} no respeta la categoría solicitada."
            )

        question_key = re.sub(r"\W+", " ", question["pregunta"].casefold()).strip()
        if question_key in seen_questions:
            raise ValueError("El agente ha generado preguntas repetidas.")
        seen_questions.add(question_key)

        correct_distribution[question["correcta"]] += 1
        validated.append(question)

    if max(correct_distribution.values()) > 4:
        raise ValueError("La distribución de respuestas correctas es demasiado sesgada.")

    return validated


def enforce_agent_rate_limit(http_request: Request):
    """Limita las generaciones con IA por IP y en total al día.

    Los contadores están en la base de datos para que el límite sea común a
    todas las instancias de la función. Si se supera, responde 429.
    """
    per_ip_limit = env_int("AGENT_RATE_LIMIT", 5)
    window_seconds = env_int("AGENT_RATE_WINDOW_SECONDS", 600, minimum=10)
    daily_limit = env_int("AGENT_DAILY_LIMIT", 300)

    ip = client_ip(
        http_request.headers,
        http_request.client.host if http_request.client else None,
    )
    now = time.time()
    checks = [
        (rate_key(ip, "generate"), per_ip_limit, window_seconds),
        ("global:generate", daily_limit, 86400),
    ]

    exceeded = None
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            for key, limit, seconds in checks:
                cursor.execute(
                    "INSERT INTO quiz.limites_uso (clave, ventana, usos) "
                    "VALUES (%s, to_timestamp(%s), 1) "
                    "ON CONFLICT (clave, ventana) "
                    "DO UPDATE SET usos = quiz.limites_uso.usos + 1 "
                    "RETURNING usos",
                    [key, window_start(now, seconds)],
                )
                uses = cursor.fetchone()["usos"]
                if uses > limit and exceeded is None:
                    exceeded = (key, seconds)
    except Exception:
        logger.exception("Error comprobando el límite de uso")
        raise HTTPException(503, "No se pudo comprobar el límite de uso. Inténtalo de nuevo.")

    if exceeded:
        key, seconds = exceeded
        wait = retry_after(now, seconds)
        if key.startswith("global:"):
            message = "Se ha alcanzado el límite diario de partidas con IA. Vuelve mañana."
        else:
            message = (
                "Has generado muchas partidas seguidas. "
                f"Espera unos {max(1, round(wait / 60))} minuto(s) y vuelve a intentarlo."
            )
        raise HTTPException(429, message, headers={"Retry-After": str(wait)})


def create_game(cursor, jugador, origen, categoria, dificultad, questions):
    """Guarda una partida nueva en el servidor y devuelve su identificador."""
    game_id = uuid.uuid4()
    cursor.execute(
        "INSERT INTO quiz.partidas "
        "(partida_id, jugador, origen, categoria, dificultad, preguntas) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        [game_id, jugador.strip(), origen, categoria, dificultad, Jsonb(questions)],
    )
    # Limpieza oportunista de datos temporales.
    cursor.execute("DELETE FROM quiz.partidas WHERE creada_en < now() - interval '2 days'")
    cursor.execute("DELETE FROM quiz.limites_uso WHERE ventana < now() - interval '2 days'")
    return game_id


@app.post("/api/agent/generate")
def generate_quiz(request: GenerateQuizRequest, http_request: Request):
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(
            503,
            "El agente IA no está configurado. Añade GROQ_API_KEY al backend.",
        )

    enforce_agent_rate_limit(http_request)

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

    expected_category = request.tema.split("—", 1)[0].strip()
    if expected_category not in AI_CATEGORIES:
        expected_category = request.tema.strip()

    prompt = (
        f"Genera exactamente 10 preguntas exclusivamente sobre el tema: {request.tema}. "
        f"Dificultad exacta: {request.dificultad}. Escribe todo en español natural y correcto. "
        f"La propiedad categoria debe ser exactamente: {expected_category}. "
        f"La propiedad dificultad debe ser exactamente: {request.dificultad}. "
        "No uses preguntas de otros temas ni información tangencial. "
        "Si el tema contiene una época, periodo, saga, género, competición o subtema, "
        "todas las preguntas deben respetarlo. "
        "Cada pregunta debe tener cuatro opciones plausibles y una sola correcta. "
        "Usa preguntas y explicaciones concisas, factuales y distintas entre sí. "
        "Distribuye las respuestas correctas entre A, B, C y D y no hagas que una misma letra "
        "sea correcta más de 4 veces. "
        "Evita opiniones, rumores, ambigüedades, preguntas trampa y datos cuya respuesta "
        "dependa de acontecimientos futuros. "
        "Revisa nombres propios, fechas, unidades, porcentajes, escalas y relaciones causa-efecto. "
        "Usa formulaciones estándar y precisas. "
        "Mantén la pregunta y la explicación breves para evitar texto innecesario. "
        "No numeres las preguntas ni añadas comentarios fuera del JSON."
    )

    model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    try:
        client = Groq(
            api_key=os.environ["GROQ_API_KEY"],
            timeout=GROQ_TIMEOUT_SECONDS,
            max_retries=1,
        )
        last_validation_error = None

        for attempt in range(2):
            current_prompt = prompt
            if attempt == 1 and last_validation_error:
                current_prompt += (
                    "\n\nLa generación anterior no superó la validación de calidad. "
                    "Genera de nuevo las 10 preguntas desde cero y corrige especialmente: "
                    f"{last_validation_error}"
                )

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres el agente de preguntas de OneToFour. "
                            "Respeta estrictamente el tema, categoría y dificultad solicitados. "
                            "Genera contenido factual, claro y apto para público general. "
                            "Antes de responder, revisa internamente cada pregunta, opción, respuesta y explicación."
                        ),
                    },
                    {"role": "user", "content": current_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "onetoFour_quiz",
                        "strict": True,
                        "schema": schema,
                    },
                },
                temperature=0.45,
                reasoning_effort="low",
                max_completion_tokens=4500,
            )

            content = response.choices[0].message.content or "{}"

            try:
                data = json.loads(content)
                questions = validate_generated_questions(data.get("preguntas", []), request)
                break
            except (json.JSONDecodeError, ValueError) as exc:
                last_validation_error = str(exc)
                if attempt == 1:
                    raise
        else:
            raise ValueError("No se pudo validar la generación del agente.")

        stored = [stored_question(question) for question in questions]
        try:
            with get_connection() as connection, connection.cursor() as cursor:
                game_id = create_game(
                    cursor,
                    request.jugador,
                    "ia",
                    expected_category,
                    request.dificultad,
                    stored,
                )
        except Exception:
            logger.exception("Error guardando la partida generada")
            raise HTTPException(
                503,
                "Las preguntas se generaron, pero no se pudo guardar la partida. "
                "Inténtalo de nuevo.",
            )

        return {
            "partida_id": str(game_id),
            "preguntas": [public_question(question) for question in stored],
            "tema": request.tema,
            "dificultad": request.dificultad,
            "generado_por": f"Groq · {model}",
        }
    except HTTPException:
        raise
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



GAME_COLUMNS = (
    "partida_id, jugador, origen, categoria, dificultad, "
    "preguntas, respuestas, finalizada"
)


def load_game(cursor, game_id, lock=False):
    cursor.execute(
        f"SELECT {GAME_COLUMNS} FROM quiz.partidas WHERE partida_id = %s"
        + (" FOR UPDATE" if lock else ""),
        [game_id],
    )
    row = cursor.fetchone()
    if row is None:
        raise GameError(404, "No se encontró la partida. Puede haber caducado.")
    return row


def game_http_error(exc: GameError):
    return HTTPException(exc.status_code, exc.message)


@app.post("/api/games/start")
def start_game(payload: StartGameRequest):
    """Crea una partida con preguntas del banco y devuelve el estado inicial."""
    jugador = payload.jugador.strip() or "Jugador"
    random_mode = payload.modo == "aleatorio"

    filters = []
    filter_params = []
    if not random_mode and payload.categoria not in ("Todas", "Aleatorio", ""):
        filters.append("p.categoria = %s")
        filter_params.append(payload.categoria)
    if payload.dificultad != "Todas":
        filters.append("p.dificultad = %s")
        filter_params.append(payload.dificultad)
    where_clause = " AND ".join(filters) if filters else "TRUE"

    # Primero las preguntas que este jugador aún no ha visto. En modo aleatorio
    # se reparte además entre categorías (la 1.ª de cada categoría, luego la 2.ª...).
    order_by = "r.rn, random()" if random_mode else "r.usada, random()"
    query = (
        "SELECT r.id, r.pregunta, r.opcion_a, r.opcion_b, r.opcion_c, r.opcion_d, "
        "r.correcta, r.categoria, r.dificultad, r.explicacion "
        "FROM ("
        "SELECT q.*, row_number() OVER (PARTITION BY q.categoria "
        "ORDER BY q.usada, random()) AS rn "
        "FROM ("
        "SELECT p.*, EXISTS ("
        "SELECT 1 FROM quiz.preguntas_usadas u "
        "WHERE u.jugador = %s AND u.pregunta_id = p.id"
        ") AS usada "
        "FROM quiz.preguntas p WHERE " + where_clause + ""
        ") q"
        ") r "
        "ORDER BY " + order_by + " LIMIT %s"
    )
    params = [jugador, *filter_params, QUESTIONS_PER_GAME]

    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            if not rows:
                raise GameError(404, "No hay preguntas para estos filtros.")

            stored = [stored_question(row, row["id"]) for row in rows]
            categoria = "Mixto" if random_mode else payload.categoria or "Todas"
            game_id = create_game(
                cursor, jugador, "banco", categoria, payload.dificultad, stored
            )
            return public_state(
                {
                    "partida_id": game_id,
                    "jugador": jugador,
                    "origen": "banco",
                    "categoria": categoria,
                    "dificultad": payload.dificultad,
                    "preguntas": stored,
                    "respuestas": [],
                    "finalizada": False,
                }
            )
    except GameError as exc:
        raise game_http_error(exc)
    except Exception:
        logger.exception("Error creando la partida")
        raise HTTPException(503, "No se pudo crear la partida.")


@app.get("/api/games/{partida_id}")
def get_game(partida_id: uuid.UUID):
    """Estado de una partida (para retomarla si se recarga la página)."""
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            return public_state(load_game(cursor, partida_id))
    except GameError as exc:
        raise game_http_error(exc)
    except Exception:
        logger.exception("Error consultando la partida")
        raise HTTPException(503, "No se pudo consultar la partida.")


@app.post("/api/games/{partida_id}/answer")
def answer_game(partida_id: uuid.UUID, payload: AnswerRequest):
    """Corrige una respuesta y devuelve la solución de esa pregunta."""
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            game = load_game(cursor, partida_id, lock=True)
            if game["finalizada"]:
                raise GameError(409, "La partida ya ha terminado.")
            answers, feedback = register_answer(
                game["preguntas"], game["respuestas"], payload.indice, payload.respuesta
            )
            cursor.execute(
                "UPDATE quiz.partidas SET respuestas = %s WHERE partida_id = %s",
                [Jsonb(answers), partida_id],
            )
            return feedback
    except GameError as exc:
        raise game_http_error(exc)
    except Exception:
        logger.exception("Error registrando la respuesta")
        raise HTTPException(503, "No se pudo registrar la respuesta.")


@app.post("/api/games/{partida_id}/finish")
def finish_game(partida_id: uuid.UUID):
    """Cierra la partida: el servidor calcula la puntuación y la guarda."""
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            game = load_game(cursor, partida_id, lock=True)
            result = final_result(game)

            if not game["finalizada"]:
                cursor.execute(
                    "INSERT INTO quiz.resultados "
                    "(partida_id, jugador, fecha, puntuacion, total_preguntas, "
                    "porcentaje, racha, categoria, dificultad) "
                    "VALUES (%s, %s, now(), %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (partida_id) DO NOTHING",
                    [
                        partida_id,
                        game["jugador"],
                        result["puntuacion"],
                        result["total_preguntas"],
                        result["porcentaje"],
                        result["racha"],
                        game["categoria"],
                        game["dificultad"],
                    ],
                )
                used_ids = [
                    q["id"] for q in game["preguntas"] if q.get("id") is not None
                ]
                if used_ids:
                    cursor.execute(
                        "INSERT INTO quiz.preguntas_usadas "
                        "(jugador, pregunta_id, partida_id) "
                        "SELECT %s, unnest(%s::int[]), %s "
                        "ON CONFLICT (jugador, pregunta_id) DO NOTHING",
                        [game["jugador"], used_ids, partida_id],
                    )
                cursor.execute(
                    "UPDATE quiz.partidas SET finalizada = true WHERE partida_id = %s",
                    [partida_id],
                )
            return result
    except GameError as exc:
        raise game_http_error(exc)
    except Exception:
        logger.exception("Error guardando el resultado")
        raise HTTPException(503, "No se pudo guardar el resultado de la partida.")


@app.get("/api/ranking")
def get_ranking():
    # Una fila por jugador con su mejor partida (no mezcla máximos de partidas distintas).
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT jugador, puntuacion, porcentaje FROM ("
                "SELECT DISTINCT ON (jugador) jugador, puntuacion, porcentaje "
                "FROM quiz.resultados "
                "ORDER BY jugador, porcentaje DESC, puntuacion DESC"
                ") mejores "
                "ORDER BY porcentaje DESC, puntuacion DESC, jugador ASC LIMIT 20"
            )
            return cursor.fetchall()
    except Exception:
        logger.exception("Error consultando ranking")
        raise HTTPException(503, "No se pudo consultar el ranking.")


@app.get("/api/stats")
def get_stats():
    queries = {
        "summary": (
            "SELECT COUNT(*) AS partidas, COUNT(DISTINCT jugador) AS jugadores, "
            "COALESCE(ROUND(AVG(porcentaje)::numeric, 2), 0)::float8 AS porcentaje_medio, "
            "COALESCE(MAX(puntuacion), 0) AS mejor_puntuacion "
            "FROM quiz.resultados"
        ),
        "categories": (
            "SELECT categoria, COUNT(*) AS partidas, "
            "ROUND(AVG(porcentaje)::numeric, 2)::float8 AS porcentaje_medio, "
            "MAX(porcentaje) AS mejor_porcentaje "
            "FROM quiz.resultados "
            "WHERE categoria IS NOT NULL AND categoria <> 'Todas' "
            "GROUP BY categoria ORDER BY porcentaje_medio DESC, partidas DESC"
        ),
        "difficulties": (
            "SELECT dificultad, COUNT(*) AS partidas, "
            "ROUND(AVG(porcentaje)::numeric, 2)::float8 AS porcentaje_medio "
            "FROM quiz.resultados "
            "WHERE dificultad IS NOT NULL AND dificultad <> 'Todas' "
            "GROUP BY dificultad ORDER BY porcentaje_medio DESC"
        ),
        "recent": (
            "SELECT jugador, puntuacion, total_preguntas, porcentaje, "
            "categoria, dificultad, fecha "
            "FROM quiz.resultados ORDER BY fecha DESC LIMIT 10"
        ),
    }

    try:
        result = {}
        with get_connection() as connection, connection.cursor() as cursor:
            for name, query in queries.items():
                cursor.execute(query)
                result[name] = cursor.fetchall()
        return result
    except Exception:
        logger.exception("Error consultando estadísticas")
        raise HTTPException(503, "No se pudieron consultar las estadísticas.")


@app.get("/api/player/{jugador}/profile")
def get_player_profile(jugador: str):
    name = jugador.strip()
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS partidas, "
                "COALESCE(SUM(puntuacion), 0) AS puntos_totales, "
                "COALESCE(MAX(puntuacion), 0) AS mejor_puntuacion, "
                "COALESCE(MAX(porcentaje), 0) AS mejor_porcentaje, "
                "COALESCE(ROUND(AVG(porcentaje)::numeric, 2), 0)::float8 AS porcentaje_medio, "
                "COUNT(DISTINCT CASE WHEN categoria IS NOT NULL "
                "AND categoria <> 'Todas' THEN categoria END) AS categorias, "
                "COUNT(CASE WHEN porcentaje = 100 THEN 1 END) AS perfectas, "
                "COUNT(CASE WHEN dificultad = 'Difícil' THEN 1 END) AS dificiles "
                "FROM quiz.resultados WHERE jugador = %s",
                [name],
            )
            summary = cursor.fetchone()

            cursor.execute(
                "SELECT puntuacion, total_preguntas, porcentaje, categoria, "
                "dificultad, fecha FROM quiz.resultados "
                "WHERE jugador = %s ORDER BY fecha DESC LIMIT 8",
                [name],
            )
            recent = cursor.fetchall()

        return {
            "jugador": name,
            "summary": summary,
            "achievements": build_achievements(summary),
            "recent": recent,
        }
    except Exception:
        logger.exception("Error consultando perfil")
        raise HTTPException(503, "No se pudo consultar el perfil.")
