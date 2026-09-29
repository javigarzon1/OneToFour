# OneToFour

Proyecto de preguntas y respuestas desarrollado con Python, PySpark y Databricks.

La idea es sencilla: presentar una serie de preguntas con cuatro opciones, comprobar la respuesta seleccionada y guardar el resultado de cada partida.

## ¿Cómo funciona?

1. Se crea el esquema `quiz`.
2. Se carga el banco de preguntas en una tabla Delta.
3. Se seleccionan preguntas de forma aleatoria.
4. El jugador responde con A, B, C o D.
5. Se calcula la puntuación.
6. La partida queda registrada para poder consultar resultados posteriores.

## Estructura del proyecto

```
OneToFour/
├── data/
│   └── preguntas.csv
├── notebooks/
│   └── OneToFour.py
├── sql/
│   └── 01_crear_tablas.sql
├── requirements.txt
└── README.md
```

## Tecnologías

- Python
- PySpark
- Databricks
- Delta Lake
- SQL

## Ejecutarlo en Databricks

Importar `notebooks/OneToFour.py` como notebook y ejecutar las celdas en orden.

El juego utiliza la tabla `quiz.preguntas` para obtener las preguntas y `quiz.resultados` para almacenar las partidas.

## Datos

El proyecto incluye un pequeño conjunto inicial de preguntas en `data/preguntas.csv`. Se puede ampliar fácilmente añadiendo nuevas preguntas, categorías y niveles de dificultad.

## Tablas

### quiz.preguntas

Contiene el banco de preguntas:

- `id`
- `pregunta`
- `opcion_a`
- `opcion_b`
- `opcion_c`
- `opcion_d`
- `correcta`
- `categoria`
- `dificultad`

### quiz.resultados

Guarda el resultado de cada partida:

- `partida_id`
- `jugador`
- `fecha`
- `puntuacion`
- `total_preguntas`
- `porcentaje`
