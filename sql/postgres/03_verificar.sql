-- Verificación después de instalar el esquema y el banco de preguntas.

SELECT categoria, dificultad, COUNT(*) AS preguntas
FROM quiz.preguntas
GROUP BY categoria, dificultad
ORDER BY categoria, dificultad;

SELECT COUNT(*) AS total_preguntas FROM quiz.preguntas;

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'quiz'
ORDER BY table_name;
