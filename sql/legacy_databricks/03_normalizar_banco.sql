-- Normaliza las primeras preguntas del banco creado en versiones anteriores.
-- Ejecutar después de 02_ampliar_banco_preguntas.sql.

UPDATE workspace.quiz.preguntas
SET categoria = CASE id
  WHEN 1 THEN 'Geografía'
  WHEN 2 THEN 'Cultura general'
  WHEN 3 THEN 'Tecnología'
  WHEN 4 THEN 'Ciencia'
  WHEN 5 THEN 'Geografía'
  WHEN 6 THEN 'Tecnología'
  WHEN 7 THEN 'Tecnología'
  WHEN 8 THEN 'Tecnología'
  WHEN 9 THEN 'Tecnología'
  WHEN 10 THEN 'Tecnología'
  ELSE categoria
END
WHERE id BETWEEN 1 AND 10;

-- Evita que el banco antiguo vuelva a introducir preguntas con categorías
-- que ya no aparecen en la interfaz principal.
DELETE FROM workspace.quiz.preguntas
WHERE categoria IN ('Programación','Matemáticas','Databricks','Spark');
