-- OneToFour Auth 1.0
CREATE TABLE IF NOT EXISTS workspace.quiz.usuarios (
  id STRING,
  usuario STRING,
  password_hash STRING,
  creado_en TIMESTAMP,
  ultimo_login TIMESTAMP,
  activo BOOLEAN
) USING DELTA;

ALTER TABLE workspace.quiz.resultados ADD COLUMNS IF NOT EXISTS (usuario_id STRING);

CREATE TABLE IF NOT EXISTS workspace.quiz.preguntas_usadas (
  usuario_id STRING,
  jugador STRING,
  pregunta_id INT,
  partida_id STRING,
  fecha_uso TIMESTAMP
) USING DELTA;

ALTER TABLE workspace.quiz.preguntas_usadas ADD COLUMNS IF NOT EXISTS (usuario_id STRING);
