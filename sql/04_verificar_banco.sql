-- Verificación después de instalar el banco ampliado.

SELECT categoria, dificultad, COUNT(*) AS preguntas
FROM workspace.quiz.preguntas
GROUP BY categoria, dificultad
ORDER BY categoria, dificultad;

SELECT COUNT(*) AS total_preguntas
FROM workspace.quiz.preguntas;

SELECT categoria, COUNT(*) AS disponibles
FROM workspace.quiz.preguntas p
WHERE NOT EXISTS (
  SELECT 1
  FROM workspace.quiz.preguntas_usadas u
  WHERE u.jugador = 'PRUEBA_ONETOFOUR'
    AND u.pregunta_id = p.id
)
GROUP BY categoria
ORDER BY categoria;
