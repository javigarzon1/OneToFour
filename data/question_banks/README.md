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


## Control de calidad

Antes de sincronizar un banco con Databricks se ejecuta:

```bash
python scripts/validate_question_banks.py --min-per-category 1200
```

El auditor comprueba automáticamente:

- estructura y columnas del CSV;
- IDs y preguntas duplicadas;
- preguntas muy similares dentro de cada categoría;
- cuatro opciones no vacías y distintas;
- respuesta correcta válida;
- categoría y dificultad;
- explicaciones;
- volumen mínimo por categoría;
- distribución de dificultad;
- patrones de preguntas potencialmente subjetivas o dependientes de actualidad.

Los avisos no bloquean la publicación; los errores críticos sí. La revisión de **veracidad factual** se mantiene como una segunda capa: para hechos sensibles, cambiantes o controvertidos no se debe tratar la salida de un modelo como fuente única.
