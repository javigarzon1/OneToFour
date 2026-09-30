-- Registro de preguntas ya servidas a cada jugador.
-- Permite evitar repeticiones incluso cuando el catálogo se baraja aleatoriamente.

CREATE TABLE IF NOT EXISTS workspace.quiz.preguntas_usadas (
  jugador STRING,
  pregunta_id INT,
  partida_id STRING,
  fecha_uso TIMESTAMP
)
USING DELTA;

CREATE TABLE IF NOT EXISTS workspace.quiz.catalogo_control (
  pregunta_id INT,
  categoria STRING,
  hash_pregunta STRING,
  generado_en TIMESTAMP
)
USING DELTA;
