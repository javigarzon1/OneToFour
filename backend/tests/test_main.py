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
