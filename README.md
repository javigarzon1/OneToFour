# OneToFour

Juego de preguntas y respuestas desarrollado en Python para ejecutarse en Databricks.

## Características
- 4 opciones por pregunta y una única respuesta correcta.
- Preguntas almacenadas en una tabla Delta.
- Orden aleatorio de preguntas.
- Puntuación automática.
- Registro de resultados de cada partida.
- Notebook preparado para Databricks.

## Estructura
- `notebooks/OneToFour.py`: notebook principal para Databricks.
- `data/preguntas.csv`: banco inicial de preguntas.
- `sql/01_crear_tablas.sql`: creación de tablas Delta.
- `requirements.txt`: dependencias externas.

## Ejecución
1. Importa `notebooks/OneToFour.py` como notebook en Databricks.
2. Ejecuta las celdas en orden.
3. Introduce A, B, C o D durante la partida.
4. Los resultados se guardan en `quiz.resultados`.
