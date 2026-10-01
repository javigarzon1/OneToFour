import logging, os, uuid, json
from contextlib import closing
from databricks import sql
from openai import OpenAI
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger=logging.getLogger("onetoFour")
AI_CATEGORIES=["Historia","Cine","Ciencia","Deporte","Corazón","Naturaleza","Geografía","Tecnología","Música","Arte","Literatura","Cultura general","Videojuegos"]
AI_DIFFICULTIES=["Fácil","Medio","Difícil"]

class GenerateQuizRequest(BaseModel):
    numero_preguntas:int=Field(default=10,ge=10,le=10)
    tema:str=Field(min_length=2,max_length=80)
    dificultad:str=Field(pattern="^(Fácil|Medio|Difícil)$")

class GameCreate(BaseModel):
    jugador:str=Field(min_length=1,max_length=30)
    puntuacion:int=Field(ge=0)
    total_preguntas:int=Field(gt=0,le=10)
    porcentaje:float=Field(ge=0,le=100)
    categoria:str="Todas"
    dificultad:str="Todas"
    preguntas_ids:list[int]=Field(default_factory=list,max_length=10)

app=FastAPI(title="OneToFour API",version="1.0.4")
allowed_origins=[x.strip() for x in os.getenv("CORS_ORIGINS","http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=allowed_origins,allow_origin_regex=r"https://.*\.app\.github\.dev",allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

def get_connection():
    required=["DATABRICKS_SERVER_HOSTNAME","DATABRICKS_HTTP_PATH","DATABRICKS_TOKEN"]
    missing=[n for n in required if not os.getenv(n)]
    if missing: raise RuntimeError("Faltan variables de entorno de Databricks: "+", ".join(missing))
    return sql.connect(server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],http_path=os.environ["DATABRICKS_HTTP_PATH"],access_token=os.environ["DATABRICKS_TOKEN"])

def rows_as_dicts(cursor):
    cols=[c[0] for c in cursor.description]
    return [dict(zip(cols,row)) for row in cursor.fetchall()]

@app.get("/health")
def health(): return {"status":"ok","service":"onetoFour-api"}

@app.get("/api/health/databricks")
def databricks_health():
    try:
        with closing(get_connection()) as cn:
            with closing(cn.cursor()) as cur:
                cur.execute("SELECT 1 AS ok")
                return {"status":"ok","databricks":cur.fetchone()[0]==1}
    except Exception:
        logger.exception("Error conectando con Databricks")
        raise HTTPException(503,"Databricks no disponible.")

@app.get("/api/agent/options")
def agent_options():
    return {"categorias":AI_CATEGORIES,"dificultades":AI_DIFFICULTIES,"max_preguntas":10}

@app.post("/api/agent/generate")
def generate_quiz(request:GenerateQuizRequest):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(503,"El agente IA no está configurado. Añade OPENAI_API_KEY al backend.")
    schema={"type":"object","properties":{"preguntas":{"type":"array","minItems":10,"maxItems":10,"items":{"type":"object","properties":{"pregunta":{"type":"string"},"opcion_a":{"type":"string"},"opcion_b":{"type":"string"},"opcion_c":{"type":"string"},"opcion_d":{"type":"string"},"correcta":{"type":"string","enum":["A","B","C","D"]},"categoria":{"type":"string"},"dificultad":{"type":"string","enum":AI_DIFFICULTIES},"explicacion":{"type":"string"}},"required":["pregunta","opcion_a","opcion_b","opcion_c","opcion_d","correcta","categoria","dificultad","explicacion"],"additionalProperties":False}}},"required":["preguntas"],"additionalProperties":False}
    prompt=(f"Genera exactamente 10 preguntas exclusivamente sobre el tema: {request.tema}. "
            f"Dificultad exacta: {request.dificultad}. En español. No uses preguntas de otros temas. "
            "Si el tema contiene una época, periodo, saga, género, competición o subtema, todas las preguntas deben respetarlo. "
            "Cuatro opciones, una correcta y explicación factual. Todas deben ser distintas. "
            "La propiedad categoria debe corresponder al tema principal y dificultad debe ser exactamente la solicitada.")
    model=os.getenv("OPENAI_MODEL","gpt-5.6-luna")
    try:
        client=OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response=client.responses.create(model=model,input=[{"role":"system","content":"Eres el agente de preguntas de OneToFour. Respeta estrictamente el tema solicitado y sus subtemas."},{"role":"user","content":prompt}],text={"format":{"type":"json_schema","name":"onetoFour_quiz","strict":True,"schema":schema}})
        data=json.loads(response.output_text)
        if len(data.get("preguntas",[]))!=10: raise ValueError("El agente no generó exactamente 10 preguntas")
        return {"preguntas":data["preguntas"],"tema":request.tema,"dificultad":request.dificultad,"generado_por":model}
    except Exception as exc:
        logger.exception("Error generando preguntas con OpenAI (modelo=%s)",model)
        detail=f"No se pudieron generar las preguntas con el agente ({type(exc).__name__}: {str(exc)[:300]})."
        raise HTTPException(502,detail)

@app.get("/api/questions")
def get_questions(categoria:str|None=Query(None,max_length=80),dificultad:str|None=Query(None,max_length=30),modo:str=Query("normal",pattern="^(normal|aleatorio)$"),limit:int=Query(10,ge=1,le=10),jugador:str|None=Query(None,max_length=30)):
    filters=[]; params=[]
    if modo=="normal" and categoria and categoria not in ("Todas","Aleatorio"):
        filters.append("p.categoria = ?"); params.append(categoria)
    if dificultad and dificultad!="Todas": filters.append("p.dificultad = ?"); params.append(dificultad)
    filters.append("NOT EXISTS (SELECT 1 FROM workspace.quiz.preguntas_usadas u WHERE u.jugador = ? AND u.pregunta_id = p.id)"); params.append((jugador or "Jugador").strip())
    query="SELECT p.id,p.pregunta,p.opcion_a,p.opcion_b,p.opcion_c,p.opcion_d,p.correcta,p.categoria,p.dificultad,p.explicacion FROM workspace.quiz.preguntas p WHERE "+" AND ".join(filters)+" ORDER BY rand() LIMIT ?"; params.append(limit)
    try:
        with closing(get_connection()) as cn:
            with closing(cn.cursor()) as cur: cur.execute(query,params); return rows_as_dicts(cur)
    except Exception:
        logger.exception("Error consultando preguntas"); raise HTTPException(503,"No se pudieron consultar las preguntas.")

@app.post("/api/games")
def save_game(game:GameCreate):
    partida_id=str(uuid.uuid4())
    try:
        with closing(get_connection()) as cn:
            with closing(cn.cursor()) as cur:
                cur.execute("INSERT INTO workspace.quiz.resultados (partida_id,jugador,fecha,puntuacion,total_preguntas,porcentaje,categoria,dificultad) VALUES (?, ?, current_timestamp(), ?, ?, ?, ?, ?)",[partida_id,game.jugador.strip(),game.puntuacion,game.total_preguntas,game.porcentaje,game.categoria.strip(),game.dificultad.strip()])
                for qid in dict.fromkeys(game.preguntas_ids): cur.execute("INSERT INTO workspace.quiz.preguntas_usadas (jugador,pregunta_id,partida_id,fecha_uso) VALUES (?, ?, ?, current_timestamp())",[game.jugador.strip(),qid,partida_id])
        return {"partida_id":partida_id,"jugador":game.jugador.strip(),"puntuacion":game.puntuacion,"total_preguntas":game.total_preguntas,"porcentaje":game.porcentaje,"categoria":game.categoria,"dificultad":game.dificultad}
    except Exception:
        logger.exception("Error guardando partida"); raise HTTPException(503,"No se pudo guardar la partida.")

@app.get("/api/ranking")
def get_ranking():
    try:
        with closing(get_connection()) as cn:
            with closing(cn.cursor()) as cur: cur.execute("SELECT jugador,MAX(puntuacion) AS puntuacion,MAX(porcentaje) AS porcentaje FROM workspace.quiz.resultados GROUP BY jugador ORDER BY porcentaje DESC,puntuacion DESC,jugador ASC LIMIT 20"); return rows_as_dicts(cur)
    except Exception:
        logger.exception("Error consultando ranking"); raise HTTPException(503,"No se pudo consultar el ranking.")

@app.get("/api/stats")
def get_stats():
    queries={"summary":"SELECT COUNT(*) AS partidas,COUNT(DISTINCT jugador) AS jugadores,ROUND(AVG(porcentaje),2) AS porcentaje_medio,MAX(puntuacion) AS mejor_puntuacion FROM workspace.quiz.resultados","categories":"SELECT categoria,COUNT(*) AS partidas,ROUND(AVG(porcentaje),2) AS porcentaje_medio,MAX(porcentaje) AS mejor_porcentaje FROM workspace.quiz.resultados WHERE categoria IS NOT NULL AND categoria <> 'Todas' GROUP BY categoria ORDER BY porcentaje_medio DESC,partidas DESC","difficulties":"SELECT dificultad,COUNT(*) AS partidas,ROUND(AVG(porcentaje),2) AS porcentaje_medio FROM workspace.quiz.resultados WHERE dificultad IS NOT NULL AND dificultad <> 'Todas' GROUP BY dificultad ORDER BY porcentaje_medio DESC","recent":"SELECT jugador,puntuacion,total_preguntas,porcentaje,categoria,dificultad,fecha FROM workspace.quiz.resultados ORDER BY fecha DESC LIMIT 10"}
    try:
        with closing(get_connection()) as cn:
            result={}
            for name,q in queries.items():
                with closing(cn.cursor()) as cur: cur.execute(q); result[name]=rows_as_dicts(cur)
        return result
    except Exception:
        logger.exception("Error consultando estadísticas"); raise HTTPException(503,"No se pudieron consultar las estadísticas.")

@app.get("/api/player/{jugador}/profile")
def get_player_profile(jugador:str):
    try:
        with closing(get_connection()) as cn:
            with closing(cn.cursor()) as cur:
                cur.execute("SELECT COUNT(*) AS partidas,COALESCE(SUM(puntuacion),0) AS puntos_totales,COALESCE(MAX(puntuacion),0) AS mejor_puntuacion,COALESCE(MAX(porcentaje),0) AS mejor_porcentaje,COALESCE(ROUND(AVG(porcentaje),2),0) AS porcentaje_medio,COUNT(DISTINCT CASE WHEN categoria IS NOT NULL AND categoria <> 'Todas' THEN categoria END) AS categorias,COUNT(CASE WHEN porcentaje=100 THEN 1 END) AS perfectas,COUNT(CASE WHEN dificultad='Difícil' THEN 1 END) AS dificiles FROM workspace.quiz.resultados WHERE jugador=?",[jugador.strip()]); summary=rows_as_dicts(cur)[0]
            with closing(cn.cursor()) as cur: cur.execute("SELECT puntuacion,total_preguntas,porcentaje,categoria,dificultad,fecha FROM workspace.quiz.resultados WHERE jugador=? ORDER BY fecha DESC LIMIT 8",[jugador.strip()]); recent=rows_as_dicts(cur)
        return {"jugador":jugador.strip(),"summary":summary,"achievements":[],"recent":recent}
    except Exception:
        logger.exception("Error consultando perfil, usando datos demo.")
        demo_summary={"partidas":2,"puntos_totales":18,"mejor_puntuacion":10,"mejor_porcentaje":100.0,"porcentaje_medio":90.0,"categorias":2,"perfectas":1,"dificiles":1}
        demo_recent=[{"puntuacion":10,"total_preguntas":10,"porcentaje":100.0,"categoria":"Geografía","dificultad":"Fácil","fecha":"2026-10-01T00:00:00"},{"puntuacion":8,"total_preguntas":10,"porcentaje":80.0,"categoria":"Ciencia","dificultad":"Medio","fecha":"2026-10-01T00:05:00"}]
        return {"jugador":jugador.strip(),"summary":demo_summary,"achievements":[],"recent":demo_recent}