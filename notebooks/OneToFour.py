# Databricks notebook source
# MAGIC %md
# MAGIC # OneToFour
# MAGIC
# MAGIC Juego de preguntas y respuestas con cuatro opciones y una respuesta correcta.

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

# MAGIC %md
# MAGIC ## Cargar preguntas

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

columnas = [
    "id", "pregunta", "opcion_a", "opcion_b", "opcion_c",
    "opcion_d", "correcta", "categoria", "dificultad"
]

df_preguntas = spark.createDataFrame(preguntas, columnas)

df_preguntas.write     .format("delta")     .mode("overwrite")     .option("overwriteSchema", "true")     .saveAsTable(QUESTIONS_TABLE)

display(spark.table(QUESTIONS_TABLE))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Crear tabla de resultados

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {RESULTS_TABLE} (
    partida_id STRING,
    jugador STRING,
    fecha TIMESTAMP,
    puntuacion INT,
    total_preguntas INT,
    porcentaje DOUBLE
)
USING DELTA
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Jugar

# COMMAND ----------

def jugar(jugador="Jugador", numero_preguntas=5):
    preguntas_disponibles = [
        fila.asDict()
        for fila in spark.table(QUESTIONS_TABLE).collect()
    ]

    if not preguntas_disponibles:
        raise ValueError("No hay preguntas disponibles.")

    numero_preguntas = min(numero_preguntas, len(preguntas_disponibles))
    seleccion = random.sample(preguntas_disponibles, numero_preguntas)
    puntuacion = 0

    print("=" * 50)
    print("ONETOFOUR")
    print("=" * 50)

    for numero, pregunta in enumerate(seleccion, start=1):
        print(f"\nPregunta {numero}/{numero_preguntas}")
        print(pregunta["pregunta"])
        print(f"A) {pregunta['opcion_a']}")
        print(f"B) {pregunta['opcion_b']}")
        print(f"C) {pregunta['opcion_c']}")
        print(f"D) {pregunta['opcion_d']}")

        while True:
            respuesta = input("Respuesta [A/B/C/D]: ").strip().upper()

            if respuesta in {"A", "B", "C", "D"}:
                break

            print("Respuesta no válida. Utiliza A, B, C o D.")

        if respuesta == pregunta["correcta"]:
            puntuacion += 1
            print("Correcto.")
        else:
            opcion_correcta = pregunta[
                f"opcion_{pregunta['correcta'].lower()}"
            ]
            print(
                f"Incorrecto. La respuesta era "
                f"{pregunta['correcta']}) {opcion_correcta}"
            )

    porcentaje = round(puntuacion * 100 / numero_preguntas, 2)
    partida_id = str(uuid.uuid4())

    resultado = spark.createDataFrame(
        [(
            partida_id,
            jugador,
            datetime.now(),
            puntuacion,
            numero_preguntas,
            porcentaje
        )],
        [
            "partida_id",
            "jugador",
            "fecha",
            "puntuacion",
            "total_preguntas",
            "porcentaje"
        ]
    )

    resultado.write         .format("delta")         .mode("append")         .saveAsTable(RESULTS_TABLE)

    print()
    print(f"Resultado: {puntuacion}/{numero_preguntas}")
    print(f"Porcentaje: {porcentaje}%")

    return partida_id

# COMMAND ----------

jugador = input("Nombre del jugador: ").strip() or "Jugador"
jugar(jugador=jugador, numero_preguntas=5)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Historial

# COMMAND ----------

display(
    spark.table(RESULTS_TABLE)
    .orderBy(F.col("fecha").desc())
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Estadísticas

# COMMAND ----------

estadisticas = (
    spark.table(RESULTS_TABLE)
    .groupBy("jugador")
    .agg(
        F.count("*").alias("partidas"),
        F.max("puntuacion").alias("mejor_puntuacion"),
        F.round(F.avg("porcentaje"), 2).alias("porcentaje_medio")
    )
    .orderBy(F.col("mejor_puntuacion").desc())
)

display(estadisticas)
