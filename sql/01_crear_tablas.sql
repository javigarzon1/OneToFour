CREATE SCHEMA IF NOT EXISTS workspace.quiz;

CREATE TABLE IF NOT EXISTS workspace.quiz.preguntas (
  id INT,
  pregunta STRING,
  opcion_a STRING,
  opcion_b STRING,
  opcion_c STRING,
  opcion_d STRING,
  correcta STRING,
  categoria STRING,
  dificultad STRING
)
USING DELTA;

CREATE TABLE IF NOT EXISTS workspace.quiz.resultados (
  partida_id STRING,
  jugador STRING,
  fecha TIMESTAMP,
  puntuacion INT,
  total_preguntas INT,
  porcentaje DOUBLE,
  categoria STRING,
  dificultad STRING
)
USING DELTA;

INSERT INTO workspace.quiz.preguntas
SELECT * FROM VALUES
  (1, '¿Cuál es la capital de España?', 'Madrid', 'Sevilla', 'Valencia', 'Bilbao', 'A', 'Geografía', 'Fácil'),
  (2, '¿Cuánto es 5 × 6?', '25', '30', '35', '40', 'B', 'Matemáticas', 'Fácil'),
  (3, '¿Qué lenguaje se utiliza en este proyecto?', 'Java', 'C++', 'Python', 'PHP', 'C', 'Programación', 'Fácil'),
  (4, '¿Cuál es el planeta más cercano al Sol?', 'Venus', 'Tierra', 'Marte', 'Mercurio', 'D', 'Ciencia', 'Fácil'),
  (5, '¿Cuántos continentes se suelen considerar en el modelo de 7 continentes?', '5', '6', '7', '8', 'C', 'Geografía', 'Fácil'),
  (6, '¿Qué estructura de Python almacena pares clave-valor?', 'Lista', 'Tupla', 'Diccionario', 'Conjunto', 'C', 'Programación', 'Medio'),
  (7, '¿Qué tecnología utiliza Databricks para almacenar tablas transaccionales?', 'Delta Lake', 'HTML', 'FTP', 'SMTP', 'A', 'Databricks', 'Medio'),
  (8, '¿Cuál es el resultado de 10 // 3 en Python?', '2', '3', '3.33', '4', 'B', 'Programación', 'Medio'),
  (9, '¿Qué función de Spark se utiliza habitualmente para leer una tabla?', 'spark.read.table', 'spark.write.table', 'spark.table.read', 'spark.load.table', 'A', 'Spark', 'Medio'),
  (10, '¿Cuál es el símbolo usado para comentarios de una línea en Python?', '//', '#', '<!--', '-->', 'B', 'Programación', 'Fácil')
AS v(id, pregunta, opcion_a, opcion_b, opcion_c, opcion_d, correcta, categoria, dificultad)
WHERE NOT EXISTS (SELECT 1 FROM workspace.quiz.preguntas);
