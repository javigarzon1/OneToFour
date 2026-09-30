from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


class FakeCursor:
    def __init__(self, rows=None, columns=None, one=None):
        self.rows = rows or []
        self.columns = columns or []
        self.one = one
        self.description = [(column,) for column in self.columns]
        self.executed = None
        self.params = None

    def execute(self, query, params=None):
        self.executed = query
        self.params = params

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.one

    def close(self):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def close(self):
        pass


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_databricks_health():
    cursor = FakeCursor(one=(1,))

    with patch("backend.app.main.get_connection", return_value=FakeConnection(cursor)):
        response = client.get("/api/health/databricks")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "databricks": True}


def test_questions_endpoint_returns_rows():
    cursor = FakeCursor(
        rows=[
            (
                1,
                "Pregunta de prueba",
                "A",
                "B",
                "C",
                "D",
                "A",
                "Prueba",
                "Fácil",
            )
        ],
        columns=[
            "id",
            "pregunta",
            "opcion_a",
            "opcion_b",
            "opcion_c",
            "opcion_d",
            "correcta",
            "categoria",
            "dificultad",
        ],
    )

    with patch("backend.app.main.get_connection", return_value=FakeConnection(cursor)):
        response = client.get("/api/questions?limit=1")

    assert response.status_code == 200
    assert response.json()[0]["pregunta"] == "Pregunta de prueba"
    assert "workspace.quiz.preguntas" in cursor.executed


def test_save_game():
    cursor = FakeCursor()

    with patch("backend.app.main.get_connection", return_value=FakeConnection(cursor)):
        response = client.post(
            "/api/games",
            json={
                "jugador": "Javi",
                "puntuacion": 4,
                "total_preguntas": 5,
                "porcentaje": 80,
            },
        )

    assert response.status_code == 200
    assert response.json()["jugador"] == "Javi"
    assert response.json()["puntuacion"] == 4
    assert "workspace.quiz.resultados" in cursor.executed


def test_ranking_endpoint():
    cursor = FakeCursor(
        rows=[("Javi", 5, 100.0)],
        columns=["jugador", "puntuacion", "porcentaje"],
    )

    with patch("backend.app.main.get_connection", return_value=FakeConnection(cursor)):
        response = client.get("/api/ranking")

    assert response.status_code == 200
    assert response.json() == [
        {"jugador": "Javi", "puntuacion": 5, "porcentaje": 100.0}
    ]


def test_stats_endpoint():
    cursors = [
        FakeCursor(rows=[(3, 2, 75.0, 10)], columns=["partidas", "jugadores", "porcentaje_medio", "mejor_puntuacion"]),
        FakeCursor(rows=[("Programación", 2, 80.0, 100.0)], columns=["categoria", "partidas", "porcentaje_medio", "mejor_porcentaje"]),
        FakeCursor(rows=[("Medio", 2, 70.0)], columns=["dificultad", "partidas", "porcentaje_medio"]),
        FakeCursor(rows=[("Javi", 5, 5, 100.0, "Programación", "Medio", "2026-09-30")], columns=["jugador", "puntuacion", "total_preguntas", "porcentaje", "categoria", "dificultad", "fecha"]),
    ]

    class MultiCursorConnection:
        def cursor(self):
            return cursors.pop(0)
        def close(self):
            pass

    with patch("backend.app.main.get_connection", return_value=MultiCursorConnection()):
        response = client.get("/api/stats")

    assert response.status_code == 200
    assert response.json()["summary"][0]["partidas"] == 3
    assert response.json()["categories"][0]["categoria"] == "Programación"
    assert response.json()["difficulties"][0]["dificultad"] == "Medio"
    assert response.json()["recent"][0]["jugador"] == "Javi"


def test_agent_options():
    response = client.get("/api/agent/options")
    assert response.status_code == 200
    assert "Historia" in response.json()["categorias"]
    assert "Difícil" in response.json()["dificultades"]


def test_agent_requires_api_key():
    with patch.dict("os.environ", {}, clear=True):
        response = client.post(
            "/api/agent/generate",
            json={"numero_preguntas": 3, "tema": "Historia", "dificultad": "Medio"},
        )
    assert response.status_code == 503
