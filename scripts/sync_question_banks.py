#!/usr/bin/env python3
"""Sincroniza los CSV de preguntas con quiz.preguntas (PostgreSQL / Neon).

Uso:
  DATABASE_URL=postgresql://... python scripts/sync_question_banks.py

Es idempotente: inserta las preguntas nuevas y actualiza las existentes por id.
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
BANK_DIR = ROOT / "data" / "question_banks"
SCHEMA_FILE = ROOT / "sql" / "postgres" / "01_schema.sql"

COLUMNS = [
    "id", "pregunta", "opcion_a", "opcion_b", "opcion_c", "opcion_d",
    "correcta", "categoria", "dificultad", "explicacion",
]
BATCH_SIZE = 200

UPSERT = (
    "INSERT INTO quiz.preguntas (" + ", ".join(COLUMNS) + ") "
    "VALUES (" + ", ".join(["%s"] * len(COLUMNS)) + ") "
    "ON CONFLICT (id) DO UPDATE SET "
    + ", ".join(f"{c} = EXCLUDED.{c}" for c in COLUMNS if c != "id")
)


def database_url() -> str:
    for name in ("DATABASE_URL", "POSTGRES_URL"):
        value = os.getenv(name, "").strip()
        if value:
            return value
    raise SystemExit("Falta la variable de entorno DATABASE_URL.")


def read_rows() -> list[tuple]:
    rows = []
    for path in sorted(BANK_DIR.glob("*.csv")):
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if not row.get("id") or not row.get("pregunta"):
                    continue
                values = [row.get(column, "") for column in COLUMNS]
                values[0] = int(values[0])
                rows.append(tuple(values))
    return rows


def main() -> int:
    rows = read_rows()
    if not rows:
        print("No hay preguntas en data/question_banks; no hay nada que sincronizar.")
        return 0

    with psycopg.connect(database_url(), connect_timeout=20) as connection:
        with connection.cursor() as cursor:
            # Garantiza que el esquema existe (el SQL es idempotente).
            cursor.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
            for start in range(0, len(rows), BATCH_SIZE):
                batch = rows[start:start + BATCH_SIZE]
                cursor.executemany(UPSERT, batch)
                print(f"Sincronizadas {min(start + BATCH_SIZE, len(rows))}/{len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
