-- Migra una tabla workspace.quiz.resultados creada con el esquema antiguo.
-- El backend necesita estas columnas para conservar categoría y dificultad.
ALTER TABLE workspace.quiz.resultados
ADD COLUMNS (
  categoria STRING,
  dificultad STRING
);
