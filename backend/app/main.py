import os
import uuid
from contextlib import closing

from databricks import sql
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="OneToFour API", version="1.0.0", description="API de OneToFour conectada a Azure Databricks.")

allowed_origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class GameCreate(BaseModel):
    jugador: str = Field(min_length=1, max_length=30)
    puntuacion: int = Field(ge=0)
    total_preguntas: int = Field(gt=0, le=100)
    porcentaje: float = Field(ge=0, le=100)

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
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Databricks no disponible: {exc}")

@app.get("/api/questions")
def get_questions(
    categoria: str | None = Query(default=None, max_length=50),
    dificultad: str | None = Query(default=None, max_length=30),
    limit: int = Query(default=20, ge=1, le=100),
):
    filters = []
    params = []
    if categoria and categoria != "Todas":
        filters.append("categoria = ?")
        params.append(categoria)
    if dificultad and dificultad != "Todas":
        filters.append("dificultad = ?")
        params.append(dificultad)
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    query = f"""
        SELECT id, pregunta, opcion_a, opcion_b, opcion_c, opcion_d,
               correcta, categoria, dificultad
        FROM quiz.preguntas
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
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Error consultando preguntas: {exc}")

@app.post("/api/games")
def save_game(game: GameCreate):
    partida_id = str(uuid.uuid4())
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    """
                    INSERT INTO quiz.resultados
                    (partida_id, jugador, fecha, puntuacion, total_preguntas, porcentaje)
                    VALUES (?, ?, current_timestamp(), ?, ?, ?)
                    """,
                    [partida_id, game.jugador.strip(), game.puntuacion, game.total_preguntas, game.porcentaje],
                )
        return {"partida_id": partida_id, "jugador": game.jugador.strip(), "puntuacion": game.puntuacion, "total_preguntas": game.total_preguntas, "porcentaje": game.porcentaje}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Error guardando partida: {exc}")

@app.get("/api/ranking")
def get_ranking():
    query = """
        SELECT jugador, MAX(puntuacion) AS puntuacion, MAX(porcentaje) AS porcentaje
        FROM quiz.resultados
        GROUP BY jugador
        ORDER BY porcentaje DESC, puntuacion DESC, jugador ASC
        LIMIT 20
    """
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(query)
                return rows_as_dicts(cursor)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Error consultando ranking: {exc}")
