#!/usr/bin/env python3
"""Genera y actualiza los bancos CSV de OneToFour con Groq.

Uso:
  python scripts/generate_question_banks.py --target 1200
  python scripts/generate_question_banks.py --new-per-topic 100
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from groq import Groq

ROOT = Path(__file__).resolve().parents[1]
BANK_DIR = ROOT / "data" / "question_banks"
MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

CATEGORIES = [
    ("historia", "Historia"),
    ("cine", "Cine"),
    ("ciencia", "Ciencia"),
    ("deporte", "Deporte"),
    ("corazon", "Corazón"),
    ("naturaleza", "Naturaleza"),
    ("geografia", "Geografía"),
    ("tecnologia", "Tecnología"),
    ("musica", "Música"),
    ("arte", "Arte"),
    ("literatura", "Literatura"),
    ("cultura_general", "Cultura general"),
]

HEADERS = [
    "id",
    "pregunta",
    "opcion_a",
    "opcion_b",
    "opcion_c",
    "opcion_d",
    "correcta",
    "categoria",
    "dificultad",
    "explicacion",
    "fuente",
    "generado_en",
]


def normalize(value: str) -> str:
    value = value.lower().strip()
    return re.sub(r"\s+", " ", value)


def question_key(question: str) -> str:
    return hashlib.sha256(normalize(question).encode("utf-8")).hexdigest()


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_question(item: dict, category: str) -> bool:
    required = [
        "pregunta",
        "opcion_a",
        "opcion_b",
        "opcion_c",
        "opcion_d",
        "correcta",
        "dificultad",
        "explicacion",
    ]

    if any(not str(item.get(key, "")).strip() for key in required):
        return False

    if item.get("correcta") not in {"A", "B", "C", "D"}:
        return False

    if item.get("dificultad") not in {"Fácil", "Medio", "Difícil"}:
        return False

    options = [str(item[f"opcion_{letter}"]).strip() for letter in "abcd"]
    if len(set(map(normalize, options))) != 4:
        return False

    if len(normalize(item["pregunta"])) < 12:
        return False

    if len(item["pregunta"]) > 500 or len(item["explicacion"]) > 500:
        return False

    return str(item.get("categoria", category)).strip() == category


def schema(batch_size: int) -> dict:
    question = {
        "type": "object",
        "properties": {
            "pregunta": {"type": "string"},
            "opcion_a": {"type": "string"},
            "opcion_b": {"type": "string"},
            "opcion_c": {"type": "string"},
            "opcion_d": {"type": "string"},
            "correcta": {
                "type": "string",
                "enum": ["A", "B", "C", "D"],
            },
            "categoria": {"type": "string"},
            "dificultad": {
                "type": "string",
                "enum": ["Fácil", "Medio", "Difícil"],
            },
            "explicacion": {"type": "string"},
        },
        "required": [
            "pregunta",
            "opcion_a",
            "opcion_b",
            "opcion_c",
            "opcion_d",
            "correcta",
            "categoria",
            "dificultad",
            "explicacion",
        ],
        "additionalProperties": False,
    }

    return {
        "type": "object",
        "properties": {
            "preguntas": {
                "type": "array",
                "minItems": batch_size,
                "maxItems": batch_size,
                "items": question,
            }
        },
        "required": ["preguntas"],
        "additionalProperties": False,
    }


def generate_batch(
    client: Groq,
    category: str,
    batch_size: int,
) -> list[dict]:
    prompt = f"""
Genera exactamente {batch_size} preguntas nuevas para el juego español OneToFour.
Categoría: {category}.

Requisitos estrictos:
- Todo en español.
- Cada pregunta tiene exactamente cuatro opciones plausibles y una sola correcta.
- No uses preguntas de verdadero/falso.
- Mezcla dificultad: aproximadamente 30% Fácil, 50% Medio y 20% Difícil.
- Las preguntas deben ser variadas, interesantes y aptas para público general.
- Evita preguntas ambiguas, opiniones, rumores, difamación y datos cuya respuesta dependa de una fecha futura.
- Prioriza hechos estables y ampliamente verificables.
- No repitas formulaciones obvias entre preguntas.
- La explicación debe justificar brevemente la respuesta correcta.
- La categoría debe ser exactamente "{category}".
- No incluyas IDs ni fuentes.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres el curador de contenido de OneToFour. "
                    "Genera bancos MCQ de alta calidad, sin duplicados "
                    "y con una única respuesta correcta."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "onetoFour_question_batch",
                "strict": True,
                "schema": schema(batch_size),
            },
        },
        temperature=0.6,
        reasoning_effort="low",
        max_completion_tokens=6000,
    )

    content = response.choices[0].message.content or "{}"
    payload = json.loads(content)
    return payload["preguntas"]


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        type=int,
        default=0,
        help="Objetivo total por categoría.",
    )
    parser.add_argument(
        "--new-per-topic",
        type=int,
        default=0,
        help="Preguntas nuevas por categoría.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Preguntas por llamada al modelo. Un lote pequeño ayuda a respetar los límites gratuitos.",
    )
    args = parser.parse_args()

    if not os.getenv("GROQ_API_KEY"):
        raise SystemExit("Falta GROQ_API_KEY.")

    if args.target <= 0 and args.new_per_topic <= 0:
        raise SystemExit("Indica --target o --new-per-topic.")

    if args.batch_size < 1 or args.batch_size > 20:
        raise SystemExit("--batch-size debe estar entre 1 y 20.")

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    generated_at = datetime.now(timezone.utc).isoformat()

    for category_index, (slug, category) in enumerate(CATEGORIES, start=1):
        path = BANK_DIR / f"{slug}.csv"
        rows = load_rows(path)
        known = {
            question_key(row["pregunta"])
            for row in rows
            if row.get("pregunta")
        }

        needed = max(0, args.target - len(rows)) if args.target > 0 else 0
        needed += args.new_per_topic

        added = 0

        while added < needed:
            batch_size = min(args.batch_size, needed - added)
            accepted: list[dict[str, str]] = []
            attempts = 0

            while len(accepted) < batch_size and attempts < 4:
                attempts += 1
                candidates = generate_batch(client, category, batch_size)

                for item in candidates:
                    item["categoria"] = category
                    key = question_key(item["pregunta"])

                    if key in known or key in {
                        question_key(x["pregunta"]) for x in accepted
                    }:
                        continue

                    if not validate_question(item, category):
                        continue

                    accepted.append(item)
                    known.add(key)

                    if len(accepted) == batch_size:
                        break

            if len(accepted) < batch_size:
                raise RuntimeError(
                    f"No se pudo completar un lote de {batch_size} "
                    f"preguntas para {category}."
                )

            next_local_id = len(rows) + 1

            for offset, item in enumerate(accepted):
                item["id"] = str(
                    category_index * 1_000_000 + next_local_id + offset
                )
                item["fuente"] = "Groq · OneToFour"
                item["generado_en"] = generated_at
                rows.append(
                    {field: item.get(field, "") for field in HEADERS}
                )

            added += len(accepted)
            print(f"{category}: +{len(accepted)} ({len(rows)} total)")

        write_rows(path, rows)


if __name__ == "__main__":
    main()
