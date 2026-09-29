CREATE SCHEMA IF NOT EXISTS quiz;

CREATE TABLE IF NOT EXISTS quiz.preguntas (
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

CREATE TABLE IF NOT EXISTS quiz.resultados (
  partida_id STRING,
  jugador STRING,
  fecha TIMESTAMP,
  puntuacion INT,
  total_preguntas INT,
  porcentaje DOUBLE
)
USING DELTA;
