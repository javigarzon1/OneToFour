"""Reglas del juego, sin base de datos ni FastAPI.

El servidor guarda las preguntas de cada partida (con su respuesta correcta) y
corrige cada respuesta. Así el navegador no recibe las soluciones por adelantado
ni decide la puntuación que acaba en el ranking.
"""
from __future__ import annotations

import math
from typing import Any

POINTS = {"Fácil": 1, "Medio": 2, "Difícil": 3}
LETTERS = ("A", "B", "C", "D")
PUBLIC_FIELDS = (
    "pregunta",
    "opcion_a",
    "opcion_b",
    "opcion_c",
    "opcion_d",
    "categoria",
    "dificultad",
)


class GameError(Exception):
    """Error de reglas con el código HTTP que debe devolverse."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def points_for(difficulty: str | None) -> int:
    return POINTS.get(difficulty or "", 1)


def stored_question(raw: dict[str, Any], question_id: int | None = None) -> dict[str, Any]:
    """Pregunta tal y como se guarda en el servidor (incluye la solución)."""
    return {
        "id": question_id,
        "pregunta": raw["pregunta"],
        "opcion_a": raw["opcion_a"],
        "opcion_b": raw["opcion_b"],
        "opcion_c": raw["opcion_c"],
        "opcion_d": raw["opcion_d"],
        "correcta": str(raw["correcta"]).strip(),
        "categoria": raw["categoria"],
        "dificultad": raw["dificultad"],
        "explicacion": raw.get("explicacion") or "",
    }


def public_question(question: dict[str, Any]) -> dict[str, Any]:
    """Pregunta que se envía al navegador: sin solución ni explicación."""
    return {field: question[field] for field in PUBLIC_FIELDS}


def summarize(questions: list[dict[str, Any]], answers: list[dict[str, Any]]) -> dict[str, Any]:
    """Puntuación, racha y porcentaje a partir de las respuestas registradas."""
    score = 0
    hits = 0
    streak = 0
    best_streak = 0
    for question, answer in zip(questions, answers):
        if answer.get("acierto"):
            score += points_for(question["dificultad"])
            hits += 1
            streak += 1
            best_streak = max(best_streak, streak)
        else:
            streak = 0

    maximum = sum(points_for(q["dificultad"]) for q in questions)
    percent = math.floor(score * 100 / maximum + 0.5) if maximum else 0
    return {
        "puntuacion": score,
        "maximo": maximum,
        "porcentaje": percent,
        "aciertos": hits,
        "racha": streak,
        "racha_max": best_streak,
    }


def register_answer(
    questions: list[dict[str, Any]],
    answers: list[dict[str, Any]],
    index: int,
    letter: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Corrige la respuesta ``letter`` a la pregunta ``index``.

    ``letter`` es A-D, o cadena vacía si se agotó el tiempo. Las preguntas se
    responden en orden y una sola vez. Devuelve las respuestas actualizadas y
    la información que se enseña al jugador tras responder.
    """
    if letter != "" and letter not in LETTERS:
        raise GameError(422, "La respuesta debe ser A, B, C o D.")
    if index >= len(questions):
        raise GameError(409, "Esa pregunta no existe en la partida.")
    if index != len(answers):
        raise GameError(
            409,
            "Las preguntas se responden en orden y una sola vez. "
            "Recarga la partida para continuar.",
        )

    question = questions[index]
    hit = letter != "" and letter == question["correcta"]
    updated = [*answers, {"respuesta": letter, "acierto": hit}]
    summary = summarize(questions, updated)
    feedback = {
        "indice": index,
        "acierto": hit,
        "tiempo_agotado": letter == "",
        "correcta": question["correcta"],
        "explicacion": question.get("explicacion") or "",
        "puntos": points_for(question["dificultad"]) if hit else 0,
        "puntuacion": summary["puntuacion"],
        "racha": summary["racha"],
        "respondidas": len(updated),
        "total": len(questions),
    }
    return updated, feedback


def public_state(game: dict[str, Any]) -> dict[str, Any]:
    """Estado de una partida para el navegador (sirve también para retomarla)."""
    questions = game["preguntas"]
    answers = game["respuestas"]
    summary = summarize(questions, answers)
    return {
        "partida_id": str(game["partida_id"]),
        "jugador": game["jugador"],
        "origen": game["origen"],
        "categoria": game["categoria"],
        "dificultad": game["dificultad"],
        "preguntas": [public_question(q) for q in questions],
        "respondidas": len(answers),
        "puntuacion": summary["puntuacion"],
        "racha": summary["racha"],
        "finalizada": bool(game["finalizada"]),
    }


def final_result(game: dict[str, Any]) -> dict[str, Any]:
    """Resultado definitivo; exige que todas las preguntas estén respondidas."""
    questions = game["preguntas"]
    answers = game["respuestas"]
    if len(answers) < len(questions):
        raise GameError(409, "Faltan preguntas por responder.")
    summary = summarize(questions, answers)
    return {
        "partida_id": str(game["partida_id"]),
        "jugador": game["jugador"],
        "puntuacion": summary["puntuacion"],
        "total_preguntas": len(questions),
        "porcentaje": summary["porcentaje"],
        "aciertos": summary["aciertos"],
        "racha": summary["racha_max"],
        "categoria": game["categoria"],
        "dificultad": game["dificultad"],
    }
