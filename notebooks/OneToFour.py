# Databricks notebook source
# MAGIC %md
# MAGIC # OneToFour
# MAGIC
# MAGIC Juego de preguntas y respuestas con cuatro opciones y una respuesta correcta.
# MAGIC
# MAGIC **Autor:** javigarzon1
# MAGIC
# MAGIC Proyecto preparado para Azure Databricks con PySpark, Delta Lake y widgets de Databricks.

# COMMAND ----------

from pyspark.sql import functions as F
import random
import uuid
from datetime import datetime

CATALOG = "workspace"
SCHEMA = "quiz"
QUESTIONS_TABLE = f"{CATALOG}.{SCHEMA}.preguntas"
RESULTS_TABLE = f"{CATALOG}.{SCHEMA}.resultados"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parámetros
# MAGIC
# MAGIC Los parámetros aparecen en la parte superior del notebook. También pueden ser enviados desde un Azure Databricks Job.

# COMMAND ----------

# Los widgets permiten utilizar el mismo notebook de forma interactiva
# o como tarea parametrizada de un Job.
dbutils.widgets.text("jugador", "Jugador", "Jugador")
dbutils.widgets.dropdown("modo", "interactivo", ["interactivo", "job"], "Modo")
dbutils.widgets.dropdown("numero_preguntas", "5", [str(i) for i in range(1, 11)], "Preguntas")
dbutils.widgets.dropdown("categoria", "Todas", [
    "Todas", "Geografía", "Matemáticas", "Programación", "Ciencia", "Databricks", "Spark"
], "Categoría")
dbutils.widgets.dropdown("dificultad", "Todas", ["Todas", "Fácil", "Medio"], "Dificultad")

jugador = dbutils.widgets.get("jugador").strip() or "Jugador"
modo = dbutils.widgets.get("modo")
numero_preguntas = int(dbutils.widgets.get("numero_preguntas"))
categoria = dbutils.widgets.get("categoria")
dificultad = dbutils.widgets.get("dificultad")

print(f"Jugador: {jugador}")
print(f"Modo: {modo}")
print(f"Número de preguntas: {numero_preguntas}")
print(f"Categoría: {categoria}")
print(f"Dificultad: {dificultad}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Banco de preguntas

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
# MAGIC ## Tabla de resultados

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {RESULTS_TABLE} (
    partida_id STRING,
    jugador STRING,
    fecha TIMESTAMP,
    puntuacion INT,
    total_preguntas INT,
    porcentaje DOUBLE,
    categoria STRING,
    dificultad STRING
)
USING DELTA
""")

spark.sql(f"ALTER TABLE {RESULTS_TABLE} ADD COLUMNS (categoria STRING, dificultad STRING)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Juego interactivo
# MAGIC
# MAGIC Al ejecutar esta celda se muestran las preguntas y las cuatro opciones.
# MAGIC La selección se realiza con un control visual cuando `ipywidgets` está disponible.
# MAGIC En ejecuciones no interactivas, como un Job, se utiliza la respuesta indicada por parámetro.

# COMMAND ----------

def obtener_preguntas():
    consulta = spark.table(QUESTIONS_TABLE)

    if categoria != "Todas":
        consulta = consulta.filter(F.col("categoria") == categoria)

    if dificultad != "Todas":
        consulta = consulta.filter(F.col("dificultad") == dificultad)

    disponibles = [fila.asDict() for fila in consulta.collect()]

    if not disponibles:
        raise ValueError("No hay preguntas para los filtros seleccionados.")

    return random.sample(disponibles, min(numero_preguntas, len(disponibles)))


def guardar_resultado(puntuacion, total):
    porcentaje = round(puntuacion * 100 / total, 2)
    partida_id = str(uuid.uuid4())

    resultado = spark.createDataFrame(
        [(
            partida_id,
            jugador,
            datetime.now(),
            puntuacion,
            total,
            porcentaje,
            categoria,
            dificultad
        )],
        [
            "partida_id", "jugador", "fecha", "puntuacion",
            "total_preguntas", "porcentaje", "categoria", "dificultad"
        ]
    )

    resultado.write.format("delta").mode("append").saveAsTable(RESULTS_TABLE)

    return partida_id, porcentaje


def jugar_interactivo():
    import ipywidgets as widgets
    from IPython.display import display, clear_output

    seleccion = obtener_preguntas()
    estado = {"indice": 0, "puntuacion": 0}

    titulo = widgets.HTML("<h2>OneToFour</h2>")
    pregunta_html = widgets.HTML()
    opciones = widgets.RadioButtons(
        options=[],
        description="Respuesta:",
        disabled=False
    )
    boton = widgets.Button(description="Responder")
    salida = widgets.Output()

    def mostrar_pregunta():
        actual = seleccion[estado["indice"]]
        pregunta_html.value = (
            f"<h3>Pregunta {estado['indice'] + 1}/{len(seleccion)}</h3>"
            f"<p>{actual['pregunta']}</p>"
        )
        opciones.options = [
            ("A) " + actual["opcion_a"], "A"),
            ("B) " + actual["opcion_b"], "B"),
            ("C) " + actual["opcion_c"], "C"),
            ("D) " + actual["opcion_d"], "D"),
        ]
        opciones.value = None
        boton.description = "Responder"

    def responder(_):
        with salida:
            clear_output()

            if opciones.value is None:
                print("Selecciona una respuesta.")
                return

            actual = seleccion[estado["indice"]]

            if opciones.value == actual["correcta"]:
                estado["puntuacion"] += 1
                print("Correcto.")
            else:
                correcta = actual[f"opcion_{actual['correcta'].lower()}"]
                print(f"Incorrecto. La respuesta correcta era {actual['correcta']}) {correcta}")

            estado["indice"] += 1

            if estado["indice"] >= len(seleccion):
                partida_id, porcentaje = guardar_resultado(
                    estado["puntuacion"],
                    len(seleccion)
                )
                print()
                print(f"Resultado: {estado['puntuacion']}/{len(seleccion)}")
                print(f"Porcentaje: {porcentaje}%")
                print(f"Partida: {partida_id}")
                boton.disabled = True
                opciones.disabled = True
                return

            mostrar_pregunta()

    boton.on_click(responder)
    mostrar_pregunta()

    display(titulo, pregunta_html, opciones, boton, salida)


if modo == "interactivo":
    jugar_interactivo()
else:
    print("Ejecución de Job completada.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Historial de partidas

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
