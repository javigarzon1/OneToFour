#!/usr/bin/env python3
"""Sincroniza los CSV de preguntas con workspace.quiz.preguntas."""
from __future__ import annotations

import csv
import os
from pathlib import Path
from databricks import sql

ROOT = Path(__file__).resolve().parents[1]
BANK_DIR = ROOT / "data" / "question_banks"

COLUMNS = [
    "id", "pregunta", "opcion_a", "opcion_b", "opcion_c", "opcion_d",
    "correcta", "categoria", "dificultad", "explicacion",
]

def connection():
    return sql.connect(
        server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )

def read_rows():
    rows = []
    for path in sorted(BANK_DIR.glob("*.csv")):
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if not row.get("id") or not row.get("pregunta"):
                    continue
                rows.append(tuple(row.get(column, "") for column in COLUMNS))
    return rows

def main():
    rows = read_rows()
    if not rows:
        raise SystemExit("No hay preguntas en data/question_banks.")

    with connection() as conn:
        conn.cursor().execute("CREATE SCHEMA IF NOT EXISTS workspace.quiz")
        conn.cursor().execute("""
            CREATE TABLE IF NOT EXISTS workspace.quiz.preguntas (
              id INT, pregunta STRING, opcion_a STRING, opcion_b STRING,
              opcion_c STRING, opcion_d STRING, correcta STRING,
              categoria STRING, dificultad STRING, explicacion STRING
            ) USING DELTA
        """)

        for start in range(0, len(rows), 100):
            batch = rows[start:start + 100]
            values = ", ".join(["(" + ",".join(["?"] * len(COLUMNS)) + ")"] * len(batch))
            query = f"""
                MERGE INTO workspace.quiz.preguntas AS target
                USING (
                  SELECT * FROM VALUES {values}
                  AS source({", ".join(COLUMNS)})
                ) AS source
                ON target.id = CAST(source.id AS INT)
                WHEN MATCHED THEN UPDATE SET
                  pregunta = source.pregunta,
                  opcion_a = source.opcion_a,
                  opcion_b = source.opcion_b,
                  opcion_c = source.opcion_c,
                  opcion_d = source.opcion_d,
                  correcta = source.correcta,
                  categoria = source.categoria,
                  dificultad = source.dificultad,
                  explicacion = source.explicacion
                WHEN NOT MATCHED THEN INSERT ({", ".join(COLUMNS)})
                VALUES ({", ".join("source." + c for c in COLUMNS)})
            """
            params = [value for row in batch for value in row]
            with conn.cursor() as cursor:
                cursor.execute(query, params)
            print(f"Sincronizadas {min(start + 100, len(rows))}/{len(rows)}")

if __name__ == "__main__":
    main()
