# Databricks notebook source
# MAGIC %md
# MAGIC # OneToFour
# MAGIC Juego de preguntas y respuestas: 4 opciones, una única correcta.

# COMMAND ----------

from pyspark.sql import functions as F
import random
import uuid
from datetime import datetime

SCHEMA = "quiz"
QUESTIONS_TABLE = f"{SCHEMA}.preguntas"
RESULTS_TABLE = f"{SCHEMA}.resultados"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

# COMMAND ----------

preguntas = [
    (1, "¿Cuál es la capital de España?", "Madrid", "Sevilla", "Valencia", "Bilbao", "A", "Geografía", "Fácil"),
    (2, "¿Cuánto es 5 × 6?", "25", "30", "35", "40", "B", "Matemáticas", "Fácil"),
    (3, "¿Qué lenguaje se utiliza en este proyecto?", "Java", "C++", "Python", "PHP", "C", "Programación", "Fácil"),
    (4, "¿Cuál es el planeta más cercano al Sol?", "Venus", "Tierra", "Marte", "Mercurio", "D", "Ciencia", "Fácil"),
    (5, "¿Cuántos continentes se suelen considerar en el modelo de 7 continentes?", "5", "6", "7", "8", "C", "Geografía", "Fácil"),
    (6, "¿Qué estructura de Python almacena pares clave-valor?", "Lista", "Tupla", "Diccionario", "Conjunto", "C", "Programación", "Medio"),
    (7, "¿Qué tecnología utiliza Databricks para almacenar tablas transaccionales?", "Delta Lake", "HTML", "FTP", "SMTP", "A", "Databricks", "Medio"),
    (8, "¿Cuál es el resultado de 10 // 3 en Python?", "2", "3", "3.33", "4", "B", "Programación", "Medio"),
    (9, "¿Qué función de Spark se utiliza habitualmente para leer una tabla?", "spark.read.table", "spark.write.table", "spark.table.read", "spark.load.table", "A", "Spark", "Medio"),
    (10, "¿Cuál es el símbolo usado para comentarios de una línea en Python?", "//", "#", "<!--", "-->", "B", "Programación", "Fácil"),
]

columns = ["id", "pregunta", "opcion_a", "opcion_b", "opcion_c", "opcion_d", "correcta", "categoria", "dificultad"]

spark.createDataFrame(preguntas, columns).write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(QUESTIONS_TABLE)

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {RESULTS_TABLE} (
    partida_id STRING,
    jugador STRING,
    fecha TIMESTAMP,
    puntuacion INT,
    total_preguntas INT,
    porcentaje DOUBLE
) USING DELTA
""")

# COMMAND ----------

def jugar(jugador="Jugador", numero_preguntas=5):
    preguntas_disponibles = [r.asDict() for r in spark.table(QUESTIONS_TABLE).collect()]
    if not preguntas_disponibles:
        raise ValueError("No hay preguntas disponibles.")

    numero_preguntas = min(numero_preguntas, len(preguntas_disponibles))
    seleccion = random.sample(preguntas_disponibles, numero_preguntas)
    puntuacion = 0

    print("=" * 60)
    print("ONETOFOUR")
    print("=" * 60)

    for numero, p in enumerate(seleccion, start=1):
        print(f"\nPregunta {numero}/{numero_preguntas}: {p['pregunta']}")
        print(f"A) {p['opcion_a']}")
        print(f"B) {p['opcion_b']}")
        print(f"C) {p['opcion_c']}")
        print(f"D) {p['opcion_d']}")

        while True:
            respuesta = input("Respuesta [A/B/C/D]: ").strip().upper()
            if respuesta in {"A", "B", "C", "D"}:
                break
            print("Introduce solamente A, B, C o D.")

        if respuesta == p["correcta"]:
            puntuacion += 1
            print("✓ Correcto")
        else:
            correcta = p[f"opcion_{p['correcta'].lower()}"]
            print(f"✗ Incorrecto. Respuesta correcta: {p['correcta']}) {correcta}")

    porcentaje = round(puntuacion * 100 / numero_preguntas, 2)
    partida_id = str(uuid.uuid4())

    spark.createDataFrame(
        [(partida_id, jugador, datetime.now(), puntuacion, numero_preguntas, porcentaje)],
        ["partida_id", "jugador", "fecha", "puntuacion", "total_preguntas", "porcentaje"]
    ).write.format("delta").mode("append").saveAsTable(RESULTS_TABLE)

    print(f"\nResultado: {puntuacion}/{numero_preguntas} ({porcentaje}%)")
    return partida_id

# COMMAND ----------

jugador = input("Nombre del jugador: ").strip() or "Jugador"
jugar(jugador=jugador, numero_preguntas=5)

# COMMAND ----------

display(spark.table(RESULTS_TABLE).orderBy(F.col("fecha").desc()))

# COMMAND ----------

display(
    spark.table(RESULTS_TABLE)
    .groupBy("jugador")
    .agg(
        F.count("*").alias("partidas"),
        F.max("puntuacion").alias("mejor_puntuacion"),
        F.round(F.avg("porcentaje"), 2).alias("porcentaje_medio")
    )
    .orderBy(F.col("mejor_puntuacion").desc())
)
