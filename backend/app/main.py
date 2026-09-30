import logging
import os
import uuid
import json
from contextlib import closing

from databricks import sql
from openai import OpenAI
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger("onetoFour")
AI_CATEGORIES = ["Historia", "Cine", "Ciencia", "Deporte", "Corazón", "Naturaleza", "Geografía", "Tecnología", "Música", "Arte", "Literatura", "Cultura general"]
AI_DIFFICULTIES = ["Fácil", "Medio", "Difícil"]

class GeneratedQuestion(BaseModel):
    pregunta: str = Field(min_length=10, max_length=500)
    opcion_a: str = Field(min_length=1, max_length=200)
    opcion_b: str = Field(min_length=1, max_length=200)
    opcion_c: str = Field(min_length=1, max_length=200)
    opcion_d: str = Field(min_length=1, max_length=200)
    correcta: str = Field(pattern="^[ABCD]$")
    categoria: str = Field(min_length=1, max_length=50)
    dificultad: str = Field(pattern="^(Fácil|Medio|Difícil)$")
    explicacion: str = Field(min_length=1, max_length=500)

class GenerateQuizRequest(BaseModel):
    numero_preguntas: int = Field(ge=1, le=20)
    tema: str = Field(min_length=2, max_length=80)
    dificultad: str = Field(pattern="^(Fácil|Medio|Difícil)$")

class GenerateQuizResponse(BaseModel):
    preguntas: list[GeneratedQuestion]
    tema: str
    dificultad: str
    generado_por: str


app = FastAPI(title="OneToFour API", version="1.0.0", description="API de OneToFour conectada a Azure Databricks.")

allowed_origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class GameCreate(BaseModel):
    jugador: str = Field(min_length=1, max_length=30)
    puntuacion: int = Field(ge=0)
    total_preguntas: int = Field(gt=0, le=100)
    porcentaje: float = Field(ge=0, le=100)
    categoria: str = Field(default="Todas", max_length=50)
    dificultad: str = Field(default="Todas", max_length=30)
    preguntas_ids: list[int] = Field(default_factory=list, max_length=100)

def get_connection():
    required = ["DATABRICKS_SERVER_HOSTNAME", "DATABRICKS_HTTP_PATH", "DATABRICKS_TOKEN"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError("Faltan variables de entorno de Databricks: " + ", ".join(missing))
    return sql.connect(
        server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )

def rows_as_dicts(cursor):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

@app.get("/health")
def health():
    return {"status": "ok", "service": "onetoFour-api"}

@app.get("/api/health/databricks")
def databricks_health():
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("SELECT 1 AS ok")
                row = cursor.fetchone()
        return {"status": "ok", "databricks": row[0] == 1}
    except Exception:
        logger.exception("Error conectando con Databricks")
        raise HTTPException(status_code=503, detail="Databricks no disponible.")

@app.get("/api/agent/options")
def agent_options():
    return {"categorias": AI_CATEGORIES, "dificultades": AI_DIFFICULTIES, "max_preguntas": 20}

@app.post("/api/agent/generate", response_model=GenerateQuizResponse)
def generate_quiz(request: GenerateQuizRequest):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="El agente IA no está configurado. Añade OPENAI_API_KEY al backend.")
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    schema = {
        "type": "object",
        "properties": {
            "preguntas": {
                "type": "array",
                "minItems": request.numero_preguntas,
                "maxItems": request.numero_preguntas,
                "items": {
                    "type": "object",
                    "properties": {
                        "pregunta": {"type": "string"},
                        "opcion_a": {"type": "string"},
                        "opcion_b": {"type": "string"},
                        "opcion_c": {"type": "string"},
                        "opcion_d": {"type": "string"},
                        "correcta": {"type": "string", "enum": ["A", "B", "C", "D"]},
                        "categoria": {"type": "string"},
                        "dificultad": {"type": "string", "enum": AI_DIFFICULTIES},
                        "explicacion": {"type": "string"}
                    },
                    "required": ["pregunta", "opcion_a", "opcion_b", "opcion_c", "opcion_d", "correcta", "categoria", "dificultad", "explicacion"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["preguntas"],
        "additionalProperties": False
    }
    prompt = (
        f"Genera exactamente {request.numero_preguntas} preguntas de un juego de cultura general. "
        f"Tema solicitado: {request.tema}. Dificultad solicitada: {request.dificultad}. "
        f"Escribe todo en español. Cada pregunta debe tener exactamente cuatro opciones plausibles y solo una correcta. "
        f"La dificultad de todas las preguntas debe ser exactamente {request.dificultad}. "
        "Evita preguntas ambiguas, opiniones, contenido difamatorio o afirmaciones no verificables. "
        "Incluye una explicación breve y factual. No repitas preguntas."
    )
    try:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": "Eres el agente generador de preguntas de OneToFour. Produce preguntas claras, verificables y jugables."},
                {"role": "user", "content": prompt}
            ],
            text={"format": {"type": "json_schema", "name": "onetoFour_quiz", "strict": True, "schema": schema}}
        )
        data = json.loads(response.output_text)
        validated = [GeneratedQuestion.model_validate(q) for q in data["preguntas"]]
        if len(validated) != request.numero_preguntas:
            raise ValueError("Número de preguntas incorrecto")
        return {"preguntas": validated, "tema": request.tema, "dificultad": request.dificultad, "generado_por": model}
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        logger.exception("Respuesta inválida del agente")
        raise HTTPException(status_code=502, detail="El agente generó una respuesta que no se pudo validar.") from exc
    except Exception as exc:
        logger.exception("Error generando preguntas con el agente")
        raise HTTPException(status_code=502, detail="No se pudieron generar las preguntas con el agente.") from exc

@app.get("/api/questions")
def get_questions(
    categoria: str | None = Query(default=None, max_length=50),
    dificultad: str | None = Query(default=None, max_length=30),
    modo: str = Query(default="normal", pattern="^(normal|aleatorio)$"),
    limit: int = Query(default=20, ge=1, le=100),
    jugador: str | None = Query(default=None, max_length=30),
):
    filters = []
    params = []
    if modo == "normal" and categoria and categoria not in ("Todas", "Aleatorio"):
        filters.append("p.categoria = ?")
        params.append(categoria)
    if dificultad and dificultad != "Todas":
        filters.append("p.dificultad = ?")
        params.append(dificultad)
    if jugador and jugador.strip():
        filters.append("""
            NOT EXISTS (
                SELECT 1
                FROM workspace.quiz.preguntas_usadas u
                WHERE LOWER(u.jugador) = LOWER(?)
                  AND u.pregunta_id = p.id
            )
        """)
        params.append(jugador.strip())
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    query = f"""
        SELECT p.id, p.pregunta, p.opcion_a, p.opcion_b, p.opcion_c, p.opcion_d,
               p.correcta, p.categoria, p.dificultad, p.explicacion
        FROM workspace.quiz.preguntas p
        {where}
        ORDER BY rand()
        LIMIT ?
    """
    params.append(limit)
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(query, params)
                return rows_as_dicts(cursor)
    except Exception:
        logger.exception("Error consultando preguntas")
        raise HTTPException(status_code=503, detail="No se pudieron consultar las preguntas.")

@app.post("/api/games")
def save_game(game: GameCreate):
    partida_id = str(uuid.uuid4())
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    """
                    INSERT INTO workspace.quiz.resultados
                    (partida_id, jugador, fecha, puntuacion, total_preguntas, porcentaje, categoria, dificultad)
                    VALUES (?, ?, current_timestamp(), ?, ?, ?, ?, ?)
                    """,
                    [partida_id, game.jugador.strip(), game.puntuacion, game.total_preguntas, game.porcentaje, game.categoria.strip(), game.dificultad.strip()],
                )
        return {"partida_id": partida_id, "jugador": game.jugador.strip(), "puntuacion": game.puntuacion, "total_preguntas": game.total_preguntas, "porcentaje": game.porcentaje, "categoria": game.categoria, "dificultad": game.dificultad}
    except Exception:
        logger.exception("Error guardando partida")
        raise HTTPException(status_code=503, detail="No se pudo guardar la partida.")

@app.get("/api/ranking")
def get_ranking():
    query = """
        SELECT jugador, MAX(puntuacion) AS puntuacion, MAX(porcentaje) AS porcentaje
        FROM workspace.quiz.resultados
        GROUP BY jugador
        ORDER BY porcentaje DESC, puntuacion DESC, jugador ASC
        LIMIT 20
    """
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(query)
                return rows_as_dicts(cursor)
    except Exception:
        logger.exception("Error consultando ranking")
        raise HTTPException(status_code=503, detail="No se pudo consultar el ranking.")

@app.get("/api/stats")
def get_stats():
    queries = {
        "summary": """
            SELECT COUNT(*) AS partidas,
                   COUNT(DISTINCT jugador) AS jugadores,
                   ROUND(AVG(porcentaje), 2) AS porcentaje_medio,
                   MAX(puntuacion) AS mejor_puntuacion
            FROM workspace.quiz.resultados
        """,
        "categories": """
            SELECT categoria, COUNT(*) AS partidas,
                   ROUND(AVG(porcentaje), 2) AS porcentaje_medio,
                   MAX(porcentaje) AS mejor_porcentaje
            FROM workspace.quiz.resultados
            WHERE categoria IS NOT NULL AND categoria <> 'Todas'
            GROUP BY categoria
            ORDER BY porcentaje_medio DESC, partidas DESC
        """,
        "difficulties": """
            SELECT dificultad, COUNT(*) AS partidas,
                   ROUND(AVG(porcentaje), 2) AS porcentaje_medio
            FROM workspace.quiz.resultados
            WHERE dificultad IS NOT NULL AND dificultad <> 'Todas'
            GROUP BY dificultad
            ORDER BY porcentaje_medio DESC
        """,
        "recent": """
            SELECT jugador, puntuacion, total_preguntas, porcentaje, categoria, dificultad, fecha
            FROM workspace.quiz.resultados
            ORDER BY fecha DESC
            LIMIT 10
        """
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
        raise HTTPException(status_code=503, detail="No se pudieron consultar las estadísticas.")
