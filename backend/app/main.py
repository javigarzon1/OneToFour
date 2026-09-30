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
from .auth import JWT_TTL_SECONDS, create_access_token, current_user, password_hash, password_verify

logger = logging.getLogger("onetoFour")
AI_CATEGORIES = ["Historia", "Cine", "Ciencia", "Deporte", "Corazón", "Naturaleza", "Geografía", "Tecnología", "Música", "Arte", "Literatura", "Cultura general"]
AI_DIFFICULTIES = ["Fácil", "Medio", "Difícil"]


class AuthCredentials(BaseModel):
    usuario: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    usuario: str
    usuario_id: str
    expires_in: int

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


@app.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def register(credentials: AuthCredentials):
    usuario = credentials.usuario.strip()
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("SELECT id FROM workspace.quiz.usuarios WHERE LOWER(usuario)=LOWER(?) LIMIT 1", [usuario])
                if cursor.fetchone():
                    raise HTTPException(status_code=409, detail="Ese nombre de usuario ya está registrado.")
                usuario_id = str(uuid.uuid4())
                cursor.execute("INSERT INTO workspace.quiz.usuarios (id, usuario, password_hash, creado_en, ultimo_login, activo) VALUES (?, ?, ?, current_timestamp(), current_timestamp(), true)", [usuario_id, usuario, password_hash(credentials.password)])
        return {"access_token": create_access_token(usuario_id, usuario), "token_type": "bearer", "usuario": usuario, "usuario_id": usuario_id, "expires_in": JWT_TTL_SECONDS}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error registrando usuario")
        raise HTTPException(status_code=503, detail="No se pudo crear la cuenta.")

@app.post("/api/auth/login", response_model=AuthResponse)
def login(credentials: AuthCredentials):
    usuario = credentials.usuario.strip()
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("SELECT id, usuario, password_hash, activo FROM workspace.quiz.usuarios WHERE LOWER(usuario)=LOWER(?) LIMIT 1", [usuario])
                row = cursor.fetchone()
                if not row or not row[3] or not password_verify(credentials.password, row[2]):
                    raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
                cursor.execute("UPDATE workspace.quiz.usuarios SET ultimo_login=current_timestamp() WHERE id=?", [row[0]])
        return {"access_token": create_access_token(row[0], row[1]), "token_type": "bearer", "usuario": row[1], "usuario_id": row[0], "expires_in": JWT_TTL_SECONDS}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error iniciando sesión")
        raise HTTPException(status_code=503, detail="No se pudo iniciar sesión.")

@app.get("/api/auth/me")
def auth_me(user=Depends(current_user)):
    return {"usuario": user["usuario"], "usuario_id": user["sub"]}

@app.post("/api/auth/logout")
def logout(user=Depends(current_user)):
    return {"ok": True, "usuario": user["usuario"]}

@app.get("/api/agent/options")
def agent_options(user=Depends(current_user)):
    return {"categorias": AI_CATEGORIES, "dificultades": AI_DIFFICULTIES, "max_preguntas": 20}

@app.post("/api/agent/generate", response_model=GenerateQuizResponse)
def generate_quiz(request: GenerateQuizRequest, user=Depends(current_user)):
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
    user=Depends(current_user),
):
    filters = []
    params = []
    if modo == "normal" and categoria and categoria not in ("Todas", "Aleatorio"):
        filters.append("p.categoria = ?")
        params.append(categoria)
    if dificultad and dificultad != "Todas":
        filters.append("p.dificultad = ?")
        params.append(dificultad)
    filters.append("""
        NOT EXISTS (
            SELECT 1
            FROM workspace.quiz.preguntas_usadas u
            WHERE u.usuario_id = ?
              AND u.pregunta_id = p.id
        )
    """)
    params.append(user["sub"])
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
def save_game(game: GameCreate, user=Depends(current_user)):
    partida_id = str(uuid.uuid4())
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    """
                    INSERT INTO workspace.quiz.resultados
                    (partida_id, usuario_id, jugador, fecha, puntuacion, total_preguntas, porcentaje, categoria, dificultad)
                    VALUES (?, ?, ?, current_timestamp(), ?, ?, ?, ?, ?)
                    """,
                    [partida_id, user["sub"], user["usuario"], game.puntuacion, game.total_preguntas, game.porcentaje, game.categoria.strip(), game.dificultad.strip()],
                )
                for question_id in dict.fromkeys(game.preguntas_ids):
                    cursor.execute("INSERT INTO workspace.quiz.preguntas_usadas (usuario_id, jugador, pregunta_id, partida_id, fecha_uso) VALUES (?, ?, ?, ?, current_timestamp())", [user["sub"], user["usuario"], question_id, partida_id])
        return {"partida_id": partida_id, "jugador": user["usuario"], "puntuacion": game.puntuacion, "total_preguntas": game.total_preguntas, "porcentaje": game.porcentaje, "categoria": game.categoria, "dificultad": game.dificultad}
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

@app.get("/api/player/me/profile")
def get_my_profile(user=Depends(current_user)):
    summary_query = """SELECT COUNT(*) AS partidas, COALESCE(SUM(puntuacion),0) AS puntos_totales, COALESCE(MAX(puntuacion),0) AS mejor_puntuacion, COALESCE(MAX(porcentaje),0) AS mejor_porcentaje, COALESCE(ROUND(AVG(porcentaje),2),0) AS porcentaje_medio, COUNT(DISTINCT CASE WHEN categoria IS NOT NULL AND categoria <> 'Todas' THEN categoria END) AS categorias, COUNT(CASE WHEN porcentaje=100 THEN 1 END) AS perfectas, COUNT(CASE WHEN dificultad='Difícil' THEN 1 END) AS dificiles FROM workspace.quiz.resultados WHERE usuario_id=?"""
    recent_query = "SELECT puntuacion,total_preguntas,porcentaje,categoria,dificultad,fecha FROM workspace.quiz.resultados WHERE usuario_id=? ORDER BY fecha DESC LIMIT 8"
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(summary_query,[user["sub"]]); summary=rows_as_dicts(cursor)[0]
            with closing(connection.cursor()) as cursor:
                cursor.execute(recent_query,[user["sub"]]); recent=rows_as_dicts(cursor)
        partidas=int(summary.get("partidas") or 0); perfectas=int(summary.get("perfectas") or 0); categorias=int(summary.get("categorias") or 0); dificiles=int(summary.get("dificiles") or 0)
        achievements=[
            {"id":"primera","titulo":"Primera partida","descripcion":"Completa tu primera partida.","icono":"🎮","desbloqueado":partidas>=1},
            {"id":"cinco","titulo":"En marcha","descripcion":"Completa 5 partidas.","icono":"🚀","desbloqueado":partidas>=5},
            {"id":"diez","titulo":"Constante","descripcion":"Completa 10 partidas.","icono":"📚","desbloqueado":partidas>=10},
            {"id":"perfecta","titulo":"Perfeccionista","descripcion":"Consigue una partida perfecta.","icono":"💯","desbloqueado":perfectas>=1},
            {"id":"imparable","titulo":"Imparable","descripcion":"Consigue 3 partidas perfectas.","icono":"🔥","desbloqueado":perfectas>=3},
            {"id":"explorador","titulo":"Explorador","descripcion":"Juega en 3 categorías diferentes.","icono":"🧭","desbloqueado":categorias>=3},
            {"id":"desafio","titulo":"Desafío","descripcion":"Completa una partida con dificultad difícil.","icono":"🏔️","desbloqueado":dificiles>=1}]
        return {"jugador":user["usuario"],"usuario_id":user["sub"],"summary":summary,"achievements":achievements,"recent":recent}
    except Exception:
        logger.exception("Error consultando perfil"); raise HTTPException(status_code=503,detail="No se pudo consultar tu perfil.")
