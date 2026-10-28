-- OneToFour · esquema para PostgreSQL (Neon).
-- Es idempotente: se puede ejecutar varias veces.
--
-- Orden de ejecución:
--   1) 01_schema.sql
--   2) 02_seed_preguntas.sql
--   3) 03_verificar.sql (opcional)

CREATE SCHEMA IF NOT EXISTS quiz;

-- Banco de preguntas.
CREATE TABLE IF NOT EXISTS quiz.preguntas (
  id          integer PRIMARY KEY,
  pregunta    text    NOT NULL,
  opcion_a    text    NOT NULL,
  opcion_b    text    NOT NULL,
  opcion_c    text    NOT NULL,
  opcion_d    text    NOT NULL,
  correcta    char(1) NOT NULL CHECK (correcta IN ('A', 'B', 'C', 'D')),
  categoria   text    NOT NULL,
  dificultad  text    NOT NULL CHECK (dificultad IN ('Fácil', 'Medio', 'Difícil')),
  explicacion text
);

CREATE INDEX IF NOT EXISTS preguntas_categoria_dificultad_idx
  ON quiz.preguntas (categoria, dificultad);

-- Partidas en curso o terminadas. El servidor guarda aquí las preguntas con su
-- respuesta correcta y las respuestas del jugador; el navegador nunca decide la
-- puntuación.
CREATE TABLE IF NOT EXISTS quiz.partidas (
  partida_id  uuid        PRIMARY KEY,
  jugador     text        NOT NULL,
  origen      text        NOT NULL CHECK (origen IN ('banco', 'ia')),
  categoria   text        NOT NULL,
  dificultad  text        NOT NULL,
  preguntas   jsonb       NOT NULL,
  respuestas  jsonb       NOT NULL DEFAULT '[]'::jsonb,
  creada_en   timestamptz NOT NULL DEFAULT now(),
  finalizada  boolean     NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS partidas_creada_en_idx ON quiz.partidas (creada_en);

-- Resultado final de cada partida terminada (alimenta ranking, estadísticas y perfil).
CREATE TABLE IF NOT EXISTS quiz.resultados (
  partida_id      uuid             PRIMARY KEY,
  jugador         text             NOT NULL,
  fecha           timestamptz      NOT NULL DEFAULT now(),
  puntuacion      integer          NOT NULL CHECK (puntuacion >= 0),
  total_preguntas integer          NOT NULL CHECK (total_preguntas > 0),
  porcentaje      double precision NOT NULL CHECK (porcentaje BETWEEN 0 AND 100),
  racha           integer          NOT NULL DEFAULT 0,
  categoria       text,
  dificultad      text
);

CREATE INDEX IF NOT EXISTS resultados_jugador_idx ON quiz.resultados (jugador);
CREATE INDEX IF NOT EXISTS resultados_fecha_idx   ON quiz.resultados (fecha DESC);

-- Preguntas del banco que ya ha jugado cada jugador (para no repetirlas).
CREATE TABLE IF NOT EXISTS quiz.preguntas_usadas (
  jugador     text        NOT NULL,
  pregunta_id integer     NOT NULL,
  partida_id  uuid,
  fecha_uso   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (jugador, pregunta_id)
);

-- Contadores del límite de uso (por ventana de tiempo). Funciona en serverless
-- porque el estado vive en la base de datos y no en la memoria de la función.
CREATE TABLE IF NOT EXISTS quiz.limites_uso (
  clave   text        NOT NULL,
  ventana timestamptz NOT NULL,
  usos    integer     NOT NULL DEFAULT 0,
  PRIMARY KEY (clave, ventana)
);
