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
  dificultad STRING,
  explicacion STRING
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
  (1, '¿Cuál es la capital de España?', 'Madrid', 'Sevilla', 'Valencia', 'Bilbao', 'A', 'Geografía', 'Fácil', 'Madrid es la capital de España.'),
  (2, '¿Cuánto es 5 × 6?', '25', '30', '35', '40', 'B', 'Cultura general', 'Fácil', '5 × 6 = 30.'),
  (3, '¿Qué lenguaje se utiliza principalmente en el backend de OneToFour?', 'Java', 'C++', 'Python', 'PHP', 'C', 'Tecnología', 'Fácil', 'OneToFour utiliza Python en su backend.'),
  (4, '¿Cuál es el planeta más cercano al Sol?', 'Venus', 'Tierra', 'Marte', 'Mercurio', 'D', 'Ciencia', 'Fácil', 'Mercurio es el planeta más cercano al Sol.'),
  (5, '¿Cuántos continentes se suelen considerar en el modelo de 7 continentes?', '5', '6', '7', '8', 'C', 'Geografía', 'Fácil', 'El modelo de siete continentes considera siete continentes.'),
  (6, '¿Qué estructura de Python almacena pares clave-valor?', 'Lista', 'Tupla', 'Diccionario', 'Conjunto', 'C', 'Tecnología', 'Medio', 'Un diccionario relaciona claves con valores en Python.'),
  (7, '¿Qué tecnología utiliza Databricks para almacenar tablas transaccionales?', 'Delta Lake', 'HTML', 'FTP', 'SMTP', 'A', 'Tecnología', 'Medio', 'Delta Lake aporta transacciones ACID para tablas de datos.'),
  (8, '¿Cuál es el resultado de 10 // 3 en Python?', '2', '3', '3.33', '4', 'B', 'Tecnología', 'Medio', 'La división entera devuelve 3.'),
  (9, '¿Qué función de Spark se utiliza habitualmente para leer una tabla?', 'spark.read.table', 'spark.write.table', 'spark.table.read', 'spark.load.table', 'A', 'Tecnología', 'Medio', 'spark.read.table permite leer una tabla como DataFrame.'),
  (10, '¿Cuál es el símbolo usado para comentarios de una línea en Python?', '//', '#', '<!--', '-->', 'B', 'Tecnología', 'Fácil', 'En Python, # inicia un comentario de una línea.')
AS v(id, pregunta, opcion_a, opcion_b, opcion_c, opcion_d, correcta, categoria, dificultad, explicacion)
WHERE NOT EXISTS (SELECT 1 FROM workspace.quiz.preguntas);

CREATE TABLE IF NOT EXISTS workspace.quiz.preguntas_usadas (
  jugador STRING,
  pregunta_id INT,
  partida_id STRING,
  fecha_uso TIMESTAMP
)
USING DELTA;
