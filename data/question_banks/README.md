# Bancos de preguntas de OneToFour

OneToFour mantiene un banco independiente por categoría:

- Historia
- Cine
- Ciencia
- Deporte
- Corazón
- Naturaleza
- Geografía
- Tecnología
- Música
- Arte
- Literatura
- Cultura general

Cada CSV usa UTF-8 y las columnas:

`id,pregunta,opcion_a,opcion_b,opcion_c,opcion_d,correcta,categoria,dificultad,explicacion,fuente,generado_en`

El objetivo operativo es mantener **al menos 1.200 preguntas disponibles por categoría**. El agente añade contenido nuevo semanalmente y el backend registra qué preguntas ha jugado cada usuario para evitar reutilizarlas.

Los CSV son una copia versionable del catálogo. La tabla Delta `workspace.quiz.preguntas` es la fuente de ejecución de la aplicación.

La generación inicial y las actualizaciones se realizan con `scripts/generate_question_banks.py`. El workflow semanal se encuentra en `.github/workflows/weekly-question-banks.yml`.
