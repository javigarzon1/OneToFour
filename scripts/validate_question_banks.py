#!/usr/bin/env python3
"""Auditor de calidad de los bancos CSV de OneToFour.

No modifica los bancos. Devuelve código 1 si encuentra errores críticos.
Incluye:
- esquema y campos obligatorios
- IDs duplicados
- preguntas duplicadas exactas
- preguntas demasiado similares mediante similitud de Jaccard de n-gramas
- opciones duplicadas
- correcta fuera de A/B/C/D
- explicación vacía
- categoría/dificultad inválidas
- distribución de dificultad
- preguntas con patrones potencialmente ambiguos
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK_DIR = ROOT / "data" / "question_banks"

CATEGORIES = {
    "historia.csv": "Historia",
    "cine.csv": "Cine",
    "ciencia.csv": "Ciencia",
    "deporte.csv": "Deporte",
    "corazon.csv": "Corazón",
    "naturaleza.csv": "Naturaleza",
    "geografia.csv": "Geografía",
    "tecnologia.csv": "Tecnología",
    "musica.csv": "Música",
    "arte.csv": "Arte",
    "literatura.csv": "Literatura",
    "cultura_general.csv": "Cultura general",
}
HEADERS = [
    "id", "pregunta", "opcion_a", "opcion_b", "opcion_c", "opcion_d",
    "correcta", "categoria", "dificultad", "explicacion", "fuente", "generado_en",
]
DIFFICULTIES = {"Fácil", "Medio", "Difícil"}

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    return re.sub(r"[^a-z0-9áéíóúüñ]+", " ", text).strip()

def shingles(text: str, size: int = 3) -> set[str]:
    words = normalize(text).split()
    return {" ".join(words[i:i + size]) for i in range(max(0, len(words) - size + 1))}

def similarity(a: str, b: str) -> float:
    sa, sb = shingles(a), shingles(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

def audit_file(path: Path, threshold: float) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != HEADERS:
            errors.append(f"{path.name}: columnas incorrectas.")
            return errors, warnings, {}
        rows = list(reader)

    expected_category = CATEGORIES[path.name]
    ids: set[str] = set()
    questions: dict[str, int] = {}
    difficulty = Counter()

    for line, row in enumerate(rows, start=2):
        prefix = f"{path.name}:{line}"
        raw_id = row["id"].strip()
        if raw_id in ids:
            errors.append(f"{prefix}: ID duplicado {raw_id}.")
        ids.add(raw_id)

        question = row["pregunta"].strip()
        key = normalize(question)
        if not key:
            errors.append(f"{prefix}: pregunta vacía.")
        elif key in questions:
            errors.append(f"{prefix}: pregunta duplicada con la línea {questions[key]}.")
        else:
            questions[key] = line

        options = [row[f"opcion_{x}"].strip() for x in "abcd"]
        normalized_options = [normalize(x) for x in options]
        if any(not x for x in options):
            errors.append(f"{prefix}: hay opciones vacías.")
        if len(set(normalized_options)) != 4:
            errors.append(f"{prefix}: las cuatro opciones no son distintas.")

        correct = row["correcta"].strip()
        if correct not in {"A", "B", "C", "D"}:
            errors.append(f"{prefix}: correcta inválida ({correct}).")

        if row["categoria"].strip() != expected_category:
            errors.append(f"{prefix}: categoría incorrecta.")

        difficulty_value = row["dificultad"].strip()
        if difficulty_value not in DIFFICULTIES:
            errors.append(f"{prefix}: dificultad inválida.")
        else:
            difficulty[difficulty_value] += 1

        if not row["explicacion"].strip():
            errors.append(f"{prefix}: explicación vacía.")
        if len(question) < 12:
            warnings.append(f"{prefix}: pregunta muy corta.")
        if question.endswith("?") is False:
            warnings.append(f"{prefix}: pregunta sin signo de interrogación.")
        lower_question = normalize(question)
        ambiguous_patterns = (
            "cual es la mejor", "quien es el mejor", "que opinas",
            "en la actualidad", "hoy en dia", "recientemente",
            "segun tu", "que crees",
        )
        if any(pattern in lower_question for pattern in ambiguous_patterns):
            warnings.append(f"{prefix}: posible pregunta subjetiva o temporal.")

    return errors, warnings, {
        "rows": len(rows),
        "difficulty": difficulty,
        "questions": list(questions),
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-per-category", type=int, default=0)
    parser.add_argument("--similarity-threshold", type=float, default=0.82)
    args = parser.parse_args()

    all_errors: list[str] = []
    all_warnings: list[str] = []
    all_questions: list[tuple[str, str, int]] = []
    summary = {}

    for filename, category in CATEGORIES.items():
        path = BANK_DIR / filename
        if not path.exists():
            all_errors.append(f"Falta {filename}.")
            continue
        errors, warnings, info = audit_file(path, args.similarity_threshold)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        summary[category] = info
        if info and info["rows"] < args.min_per_category:
            all_errors.append(
                f"{category}: {info['rows']} preguntas; se requieren al menos {args.min_per_category}."
            )
        all_questions.extend((category, q, i) for i, q in enumerate(info.get("questions", []), start=1))

    # Comparación por pares dentro de cada categoría. Para 1.200 preguntas,
    # la comparación de 3-gramas es suficientemente ligera para CI.
    for category in summary:
        items = [(q, line) for cat, q, line in all_questions if cat == category]
        for i in range(len(items)):
            q1, line1 = items[i]
            for j in range(i + 1, len(items)):
                q2, line2 = items[j]
                score = similarity(q1, q2)
                if score >= args.similarity_threshold:
                    all_errors.append(
                        f"{category}: preguntas demasiado similares "
                        f"(líneas {line1} y {line2}, similitud {score:.2f})."
                    )

    total = sum(info["rows"] for info in summary.values())
    print(f"Preguntas auditadas: {total}")
    for category, info in summary.items():
        dist = ", ".join(f"{k}={v}" for k, v in sorted(info["difficulty"].items()))
        print(f"- {category}: {info['rows']} ({dist})")

    if all_warnings:
        print(f"\nAvisos: {len(all_warnings)}")
        for warning in all_warnings[:50]:
            print(f"WARNING: {warning}")
        if len(all_warnings) > 50:
            print(f"... y {len(all_warnings) - 50} avisos más.")

    if all_errors:
        print(f"\nErrores críticos: {len(all_errors)}")
        for error in all_errors[:100]:
            print(f"ERROR: {error}")
        if len(all_errors) > 100:
            print(f"... y {len(all_errors) - 100} errores más.")
        return 1

    print("\nAuditoría OK.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
