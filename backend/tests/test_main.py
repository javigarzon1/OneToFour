import json
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

GAME_ID = uuid.uuid4()


class FakeCursor:
    """Cursor que devuelve, en orden, un resultado (lista de dicts) por cada execute()."""

    def __init__(self, *results):
        self.results = list(results)
        self.rows = []
        self.history = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, query, params=None):
        self.history.append((query, params))
        self.rows = self.results.pop(0) if self.results else []

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def queries(self):
        return [query for query, _ in self.history]


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return self._cursor


def use_db(cursor):
    return patch(
        "backend.app.main.get_connection",
        return_value=FakeConnection(cursor),
    )


def stored(index, correct="A", level="Fácil"):
    return {
        "id": 100 + index,
        "pregunta": f"Pregunta de prueba número {index}",
        "opcion_a": "Uno",
        "opcion_b": "Dos",
        "opcion_c": "Tres",
        "opcion_d": "Cuatro",
        "correcta": correct,
        "categoria": "Historia",
        "dificultad": level,
        "explicacion": f"Explicación {index}.",
    }


def game_row(answers=None, finished=False, questions=None):
    return {
        "partida_id": GAME_ID,
        "jugador": "Javi",
        "origen": "banco",
        "categoria": "Historia",
        "dificultad": "Todas",
        "preguntas": questions or [stored(0, "A", "Fácil"), stored(1, "B", "Medio")],
        "respuestas": answers or [],
        "finalizada": finished,
    }


# --- salud -----------------------------------------------------------------

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_database_health():
    cursor = FakeCursor([{"ok": 1}])
    with patch.dict("os.environ", {"DATABASE_URL": "postgres://u:p@h/db"}, clear=True):
        with use_db(cursor):
            response = client.get("/api/health/db")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": True,
        "configured": {"database_url": True},
    }


def test_database_health_reports_missing_configuration():
    with patch.dict("os.environ", {}, clear=True):
        response = client.get("/api/health/db")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error_category"] == "configuration_missing"
    assert detail["configured"] == {"database_url": False}


def test_ai_health_without_key():
    with patch.dict("os.environ", {}, clear=True):
        response = client.get("/api/health/ai")

    assert response.status_code == 200
    assert response.json()["provider"] == "Groq"
    assert response.json()["configured"] is False


def test_ai_health_with_key():
    with patch.dict(
        "os.environ",
        {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "qwen/qwen3.8-27b"},
        clear=True,
    ):
        response = client.get("/api/health/ai")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "provider": "Groq",
        "model": "qwen/qwen3.8-27b",
        "configured": True,
    }


# --- agente IA -------------------------------------------------------------

def test_agent_options():
    response = client.get("/api/agent/options")

    assert response.status_code == 200
    assert response.json()["max_preguntas"] == 10
    assert response.json()["proveedor"] == "Groq"
    assert "Historia" in response.json()["categorias"]
    assert "Difícil" in response.json()["dificultades"]


def test_agent_requires_api_key():
    with patch.dict("os.environ", {}, clear=True):
        response = client.post(
            "/api/agent/generate",
            json={"numero_preguntas": 10, "tema": "Historia", "dificultad": "Medio"},
        )

    assert response.status_code == 503


def fake_groq(questions):
    fake_client = SimpleNamespace()
    fake_client.chat = SimpleNamespace()
    fake_client.chat.completions = SimpleNamespace(
        create=lambda **kwargs: SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps({"preguntas": questions}))
                )
            ]
        )
    )
    return fake_client


def generated_questions():
    return [
        {
            "pregunta": f"Pregunta de prueba número {index}",
            "opcion_a": "Opción A",
            "opcion_b": "Opción B",
            "opcion_c": "Opción C",
            "opcion_d": "Opción D",
            "correcta": "ABCD"[(index - 1) % 4],
            "categoria": "Videojuegos",
            "dificultad": "Medio",
            "explicacion": "Explicación de prueba.",
        }
        for index in range(1, 11)
    ]


def test_agent_generates_ten_questions_and_creates_game():
    # execute(): límite por IP, límite global, INSERT partida y dos DELETE de limpieza.
    cursor = FakeCursor([{"usos": 1}], [{"usos": 1}], [], [], [])

    with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}, clear=True):
        with patch("backend.app.main.Groq", return_value=fake_groq(generated_questions())):
            with use_db(cursor):
                response = client.post(
                    "/api/agent/generate",
                    json={
                        "numero_preguntas": 10,
                        "tema": "Videojuegos — Años 90",
                        "dificultad": "Medio",
                        "jugador": "Javi",
                    },
                )

    assert response.status_code == 200
    body = response.json()
    assert uuid.UUID(body["partida_id"])
    assert len(body["preguntas"]) == 10
    assert body["tema"] == "Videojuegos — Años 90"
    assert body["generado_por"] == "Groq · qwen/qwen3.8-27b"
    # El navegador no recibe las soluciones.
    assert all("correcta" not in q and "explicacion" not in q for q in body["preguntas"])
    assert any("INSERT INTO quiz.partidas" in query for query in cursor.queries())


def test_agent_is_rate_limited_per_ip():
    cursor = FakeCursor([{"usos": 99}], [{"usos": 1}])

    with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}, clear=True):
        with use_db(cursor):
            response = client.post(
                "/api/agent/generate",
                json={"numero_preguntas": 10, "tema": "Historia", "dificultad": "Medio"},
            )

    assert response.status_code == 429
    assert int(response.headers["retry-after"]) >= 1


def test_agent_stops_when_daily_limit_is_reached():
    cursor = FakeCursor([{"usos": 1}], [{"usos": 10_000}])

    with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}, clear=True):
        with use_db(cursor):
            response = client.post(
                "/api/agent/generate",
                json={"numero_preguntas": 10, "tema": "Historia", "dificultad": "Medio"},
            )

    assert response.status_code == 429
    assert "diario" in response.json()["detail"]


# --- partidas --------------------------------------------------------------

def test_start_game_from_question_bank():
    rows = [stored(i) for i in range(10)]
    cursor = FakeCursor(rows, [], [], [])

    with use_db(cursor):
        response = client.post(
            "/api/games/start",
            json={"jugador": "Javi", "categoria": "Historia", "dificultad": "Fácil"},
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body["preguntas"]) == 10
    assert body["respondidas"] == 0
    assert body["origen"] == "banco"
    assert all("correcta" not in q for q in body["preguntas"])

    select_query, select_params = cursor.history[0]
    assert "quiz.preguntas" in select_query
    assert "random()" in select_query
    assert "p.categoria = %s" in select_query
    assert "p.dificultad = %s" in select_query
    assert select_params == ["Javi", "Historia", "Fácil", 10]


def test_start_random_game_balances_categories_and_ignores_category():
    cursor = FakeCursor([stored(0)], [], [], [])

    with use_db(cursor):
        response = client.post(
            "/api/games/start",
            json={"jugador": "Javi", "categoria": "Historia", "modo": "aleatorio"},
        )

    assert response.status_code == 200
    select_query, select_params = cursor.history[0]
    assert "PARTITION BY q.categoria" in select_query
    assert "ORDER BY r.rn, random()" in select_query
    assert "p.categoria = %s" not in select_query
    assert select_params == ["Javi", 10]
    assert response.json()["categoria"] == "Mixto"


def test_start_game_without_questions_returns_404():
    cursor = FakeCursor([])

    with use_db(cursor):
        response = client.post("/api/games/start", json={"jugador": "Javi"})

    assert response.status_code == 404


def test_get_game_returns_public_state():
    cursor = FakeCursor([game_row(answers=[{"respuesta": "A", "acierto": True}])])

    with use_db(cursor):
        response = client.get(f"/api/games/{GAME_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["respondidas"] == 1
    assert body["puntuacion"] == 1
    assert all("correcta" not in q for q in body["preguntas"])


def test_get_unknown_game_returns_404():
    with use_db(FakeCursor([])):
        response = client.get(f"/api/games/{uuid.uuid4()}")

    assert response.status_code == 404


def test_answer_correct_reveals_solution_and_saves():
    cursor = FakeCursor([game_row()], [])

    with use_db(cursor):
        response = client.post(
            f"/api/games/{GAME_ID}/answer", json={"indice": 0, "respuesta": "A"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["acierto"] is True
    assert body["correcta"] == "A"
    assert body["puntos"] == 1
    assert body["explicacion"] == "Explicación 0."
    assert any("UPDATE quiz.partidas SET respuestas" in q for q in cursor.queries())
    assert "FOR UPDATE" in cursor.history[0][0]


def test_answer_wrong_does_not_score():
    with use_db(FakeCursor([game_row()], [])):
        response = client.post(
            f"/api/games/{GAME_ID}/answer", json={"indice": 0, "respuesta": "C"}
        )

    assert response.status_code == 200
    assert response.json()["acierto"] is False
    assert response.json()["puntos"] == 0


def test_answer_out_of_order_is_rejected():
    cursor = FakeCursor([game_row()])

    with use_db(cursor):
        response = client.post(
            f"/api/games/{GAME_ID}/answer", json={"indice": 1, "respuesta": "B"}
        )

    assert response.status_code == 409
    assert not any("UPDATE" in q for q in cursor.queries())


def test_answer_on_finished_game_is_rejected():
    with use_db(FakeCursor([game_row(finished=True)])):
        response = client.post(
            f"/api/games/{GAME_ID}/answer", json={"indice": 0, "respuesta": "A"}
        )

    assert response.status_code == 409


def test_answer_validates_payload():
    response = client.post(
        f"/api/games/{GAME_ID}/answer", json={"indice": 0, "respuesta": "Z"}
    )
    assert response.status_code == 422

    response = client.post(
        f"/api/games/{GAME_ID}/answer", json={"indice": 99, "respuesta": "A"}
    )
    assert response.status_code == 422


def test_finish_computes_score_on_the_server_and_saves_result():
    answers = [
        {"respuesta": "A", "acierto": True},
        {"respuesta": "B", "acierto": True},
    ]
    cursor = FakeCursor([game_row(answers=answers)], [], [], [])

    with use_db(cursor):
        response = client.post(f"/api/games/{GAME_ID}/finish")

    assert response.status_code == 200
    body = response.json()
    assert body["puntuacion"] == 3  # 1 (fácil) + 2 (medio)
    assert body["porcentaje"] == 100
    assert body["racha"] == 2

    insert_query, insert_params = next(
        item for item in cursor.history if "INSERT INTO quiz.resultados" in item[0]
    )
    assert "ON CONFLICT (partida_id) DO NOTHING" in insert_query
    assert 3 in insert_params and 100 in insert_params
    assert any("INSERT INTO quiz.preguntas_usadas" in q for q in cursor.queries())
    assert any("SET finalizada = true" in q for q in cursor.queries())


def test_finish_requires_all_answers():
    cursor = FakeCursor([game_row(answers=[{"respuesta": "A", "acierto": True}])])

    with use_db(cursor):
        response = client.post(f"/api/games/{GAME_ID}/finish")

    assert response.status_code == 409
    assert not any("INSERT" in q for q in cursor.queries())


def test_finish_is_idempotent():
    answers = [
        {"respuesta": "A", "acierto": True},
        {"respuesta": "B", "acierto": True},
    ]
    cursor = FakeCursor([game_row(answers=answers, finished=True)])

    with use_db(cursor):
        response = client.post(f"/api/games/{GAME_ID}/finish")

    assert response.status_code == 200
    assert response.json()["puntuacion"] == 3
    assert len(cursor.history) == 1  # sólo la lectura: no se vuelve a guardar


def test_client_can_no_longer_post_its_own_score():
    response = client.post(
        "/api/games",
        json={"jugador": "Tramposo", "puntuacion": 99, "total_preguntas": 10, "porcentaje": 100},
    )

    assert response.status_code in (404, 405)


# --- ranking, estadísticas y perfil -----------------------------------------

def test_ranking_endpoint():
    cursor = FakeCursor([{"jugador": "Javi", "puntuacion": 5, "porcentaje": 100.0}])

    with use_db(cursor):
        response = client.get("/api/ranking")

    assert response.status_code == 200
    assert response.json() == [{"jugador": "Javi", "puntuacion": 5, "porcentaje": 100.0}]
    assert "DISTINCT ON (jugador)" in cursor.history[0][0]


def test_stats_endpoint():
    cursor = FakeCursor(
        [{"partidas": 3, "jugadores": 2, "porcentaje_medio": 75.0, "mejor_puntuacion": 10}],
        [{"categoria": "Historia", "partidas": 2, "porcentaje_medio": 80.0, "mejor_porcentaje": 100.0}],
        [{"dificultad": "Medio", "partidas": 2, "porcentaje_medio": 70.0}],
        [
            {
                "jugador": "Javi",
                "puntuacion": 5,
                "total_preguntas": 5,
                "porcentaje": 100.0,
                "categoria": "Historia",
                "dificultad": "Medio",
                "fecha": "2026-09-30",
            }
        ],
    )

    with use_db(cursor):
        response = client.get("/api/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"][0]["partidas"] == 3
    assert body["categories"][0]["categoria"] == "Historia"
    assert body["difficulties"][0]["dificultad"] == "Medio"
    assert body["recent"][0]["jugador"] == "Javi"


def test_player_profile():
    summary = {
        "partidas": 6,
        "puntos_totales": 40,
        "mejor_puntuacion": 9,
        "mejor_porcentaje": 100.0,
        "porcentaje_medio": 82.5,
        "categorias": 3,
        "perfectas": 1,
        "dificiles": 1,
    }
    recent = [
        {
            "puntuacion": 9,
            "total_preguntas": 10,
            "porcentaje": 100.0,
            "categoria": "Historia",
            "dificultad": "Difícil",
            "fecha": "2026-09-30",
        }
    ]

    with use_db(FakeCursor([summary], recent)):
        response = client.get("/api/player/Javi/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["jugador"] == "Javi"
    assert body["summary"]["partidas"] == 6
    unlocked = {a["id"] for a in body["achievements"] if a["desbloqueado"]}
    assert {"primera", "cinco", "perfecta", "categorias_tres", "dificil"} <= unlocked
    assert "diez" not in unlocked
