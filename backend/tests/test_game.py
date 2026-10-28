"""Tests de las reglas del juego (sin FastAPI ni base de datos)."""
import pytest

from backend.app.game import (
    GameError,
    final_result,
    points_for,
    public_question,
    public_state,
    register_answer,
    stored_question,
    summarize,
)


def make_questions():
    levels = ["Fácil", "Medio", "Difícil", "Fácil"]
    return [
        stored_question(
            {
                "pregunta": f"Pregunta {i}",
                "opcion_a": "Uno",
                "opcion_b": "Dos",
                "opcion_c": "Tres",
                "opcion_d": "Cuatro",
                "correcta": "ABCD"[i],
                "categoria": "Historia",
                "dificultad": level,
                "explicacion": f"Porque sí {i}.",
            },
            question_id=100 + i,
        )
        for i, level in enumerate(levels)
    ]


def play(questions, letters):
    answers = []
    for index, letter in enumerate(letters):
        answers, _ = register_answer(questions, answers, index, letter)
    return answers


def test_points_by_difficulty():
    assert points_for("Fácil") == 1
    assert points_for("Medio") == 2
    assert points_for("Difícil") == 3
    assert points_for("Desconocida") == 1
    assert points_for(None) == 1


def test_public_question_hides_solution():
    question = make_questions()[0]
    public = public_question(question)
    assert "correcta" not in public
    assert "explicacion" not in public
    assert "id" not in public
    assert public["pregunta"] == "Pregunta 0"


def test_perfect_game_scores_maximum():
    questions = make_questions()
    answers = play(questions, ["A", "B", "C", "D"])
    summary = summarize(questions, answers)
    assert summary["puntuacion"] == 1 + 2 + 3 + 1
    assert summary["maximo"] == 7
    assert summary["porcentaje"] == 100
    assert summary["racha_max"] == 4


def test_wrong_and_timeout_do_not_score_and_break_streak():
    questions = make_questions()
    # acierta, falla, tiempo agotado, acierta
    answers = play(questions, ["A", "A", "", "D"])
    summary = summarize(questions, answers)
    assert summary["puntuacion"] == 1 + 1
    assert summary["aciertos"] == 2
    assert summary["racha_max"] == 1
    assert summary["racha"] == 1
    assert summary["porcentaje"] == 29  # 2 / 7


def test_register_answer_feedback_reveals_solution_only_after_answering():
    questions = make_questions()
    _, feedback = register_answer(questions, [], 0, "B")
    assert feedback["acierto"] is False
    assert feedback["correcta"] == "A"
    assert feedback["explicacion"] == "Porque sí 0."
    assert feedback["puntos"] == 0
    assert feedback["tiempo_agotado"] is False

    _, timeout = register_answer(questions, [], 0, "")
    assert timeout["tiempo_agotado"] is True
    assert timeout["acierto"] is False


def test_answers_must_be_in_order_and_only_once():
    questions = make_questions()
    with pytest.raises(GameError) as skipped:
        register_answer(questions, [], 2, "C")
    assert skipped.value.status_code == 409

    answers, _ = register_answer(questions, [], 0, "A")
    with pytest.raises(GameError) as repeated:
        register_answer(questions, answers, 0, "A")
    assert repeated.value.status_code == 409


def test_invalid_letter_and_index_are_rejected():
    questions = make_questions()
    with pytest.raises(GameError) as bad_letter:
        register_answer(questions, [], 0, "Z")
    assert bad_letter.value.status_code == 422

    with pytest.raises(GameError) as bad_index:
        register_answer(questions, [], 9, "A")
    assert bad_index.value.status_code == 409


def test_public_state_supports_resuming():
    questions = make_questions()
    answers = play(questions, ["A", "A"])
    state = public_state(
        {
            "partida_id": "abc",
            "jugador": "Javi",
            "origen": "banco",
            "categoria": "Historia",
            "dificultad": "Todas",
            "preguntas": questions,
            "respuestas": answers,
            "finalizada": False,
        }
    )
    assert state["respondidas"] == 2
    assert state["resultados"] == [True, False]
    assert state["puntuacion"] == 1
    assert all("correcta" not in q for q in state["preguntas"])


def test_final_result_requires_all_answers():
    questions = make_questions()
    game = {
        "partida_id": "abc",
        "jugador": "Javi",
        "categoria": "Historia",
        "dificultad": "Todas",
        "preguntas": questions,
        "respuestas": play(questions, ["A", "B"]),
    }
    with pytest.raises(GameError) as incomplete:
        final_result(game)
    assert incomplete.value.status_code == 409

    game["respuestas"] = play(questions, ["A", "B", "C", "D"])
    result = final_result(game)
    assert result["puntuacion"] == 7
    assert result["porcentaje"] == 100
    assert result["racha"] == 4
    assert result["total_preguntas"] == 4
