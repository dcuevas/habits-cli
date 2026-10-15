# Tareas 001 — MVP de habits-cli

Desglose de [plan.md](plan.md) según [spec.md](spec.md). Reglas:
- Se hacen en orden; cada tarea depende de las anteriores y dura como máximo 20-30 minutos.
- Cada tarea incluye sus tests y termina con todos los tests en verde antes de pasar a la siguiente.
- No se implementa nada que no esté en la spec.
- En los tests, `today` siempre es una fecha fija (`date(2026, 10, 14)`) y el archivo de datos va en un directorio temporal (`HABITS_FILE`).

## Fase 0 — Base

- [x] **T-1. Esqueleto del proyecto.** Crear `pyproject.toml` (Python ≥3.12, script `habits`, extra `[dev]` con pytest), `src/habits_cli/` con `core.py`, `storage.py`, `cli.py` y `__main__.py` vacíos, y la carpeta `tests/`.
  Hecho cuando: `pip install -e .[dev]` y `pytest` terminan sin errores.

## Fase 1 — Core (`core.py`, solo tests unitarios)

- [x] **T-2. Modelo, errores y validación de nombre** (RF-1.2, RF-1.3, RF-1.6, RF-1.7). `Habit`, errores tipados sin texto y `validate_name`.
  Hecho cuando: los tests pasan para recorte de espacios, tabuladores y NBSP; vacío y solo espacios → `InvalidName`; 120 caracteres válido y 121 → `InvalidName`; espacios internos intactos.

- [x] **T-3. Crear hábito** (RF-1.1, RF-1.4, RF-1.5). `add_habit` con comparación por `casefold` del nombre recortado.
  Hecho cuando: los tests pasan para creación sin fechas y al final de la lista, grafía conservada, duplicado por mayúsculas o espacios externos → `DuplicateHabit`, "Leer  mucho" distinto de "Leer mucho", y lista sin cambios ante cualquier error.

- [x] **T-4. Cálculo de racha** (RF-3.2, RF-3.3, RF-3.5). `current_streak` e `is_done_today`.
  Hecho cuando: los tests pasan para marcado hoy, ayer y anteayer (3, hecho hoy); ayer y anteayer (2, pendiente); hueco (1); solo hace dos días (0); sin fechas (0); solo fechas futuras (0, pendiente); racha de 2 con una fecha futura (2).

- [x] **T-5. Marcar hábito** (RF-2.1, RF-2.2, RF-2.3, RF-2.4, RF-2.5). `mark_done` devuelve `MARKED` o `ALREADY_DONE`.
  Hecho cuando: los tests pasan para registro de hoy, búsqueda sin distinguir mayúsculas y con espacios externos, segundo marcado sin duplicar, hábito inexistente y nombre vacío → `HabitNotFound`, y fechas futuras conservadas al marcar.

- [x] **T-6. Listar hábitos** (RF-3.1). `list_habits` devuelve nombre, racha y hecho hoy por hábito.
  Hecho cuando: los tests pasan para orden de creación, valores correctos con varios hábitos y lista vacía cuando no hay hábitos.

## Fase 2 — Persistencia (`storage.py`)

- [x] **T-7. Ruta y carga válida** (RF-4.1, RF-4.2, RNF-4). `default_path` y `load`.
  Hecho cuando: los tests pasan para `HABITS_FILE` con prioridad sobre la ruta por defecto, archivo inexistente → lista vacía sin crear nada, y JSON válido cargado con fechas como conjunto.

- [x] **T-8. Datos dañados** (RF-4.3, RF-4.4). Validación estricta en `load`.
  Hecho cuando: hay un test por caso que lanza `CorruptData` (archivo ilegible, JSON inválido o vacío, estructura distinta, nombre inválido, nombres duplicados, fecha `20261014`), y se aceptan fechas duplicadas, desordenadas y futuras.

- [x] **T-9. Guardado atómico** (RF-4.1, RF-4.2, RF-4.5, RNF-5). `save` con archivo temporal y `os.replace`.
  Hecho cuando: los tests pasan para guardar y cargar con resultado idéntico, creación del directorio, fechas ordenadas sin duplicados, tildes legibles en el archivo, y fallo simulado de `os.replace` → `StorageWriteError` con el original intacto y sin archivos temporales.

- [x] **T-10. Rendimiento** (RNF-3). Prueba con datos grandes.
  Hecho cuando: un test que carga y lista 100 hábitos con 3650 fechas cada uno tarda menos de 1 segundo y pasa.

## Fase 3 — CLI (`cli.py`)

- [x] **T-11. Parser, ayuda y uso incorrecto** (RF-5.1, RF-5.2). `main(argv, today=None) -> int` con textos propios en español.
  Hecho cuando: los tests pasan para `--help` global y por comando (en español, código 0), y comando desconocido, argumentos de más o de menos y ejecución sin comando muestran el mensaje con la línea de sintaxis y código 2.

- [x] **T-12. Comando `add`** (RF-1.1, RF-1.3, RF-1.4, RF-1.6). Carga, `add_habit`, guarda y confirma.
  Hecho cuando: los tests de CLI pasan para creación (código 0, archivo creado) y para nombre vacío, 121 caracteres y duplicado (código 1, mensaje en stderr que dice qué hacer, archivo sin cambios).

- [x] **T-13. Comando `done`** (RF-2.1, RF-2.2, RF-2.3, RF-2.4, RF-2.5). Carga, `mark_done` y guarda solo si cambió algo.
  Hecho cuando: los tests de CLI pasan para marcado (código 0), aviso de ya marcado (código 0, sin duplicar), hábito inexistente y nombre vacío (código 1, no se crea ningún hábito).

- [x] **T-14. Comando `list`** (RF-3.1, RF-3.2, RF-3.3, RF-3.4, RF-3.5). Formato de salida y mensaje de lista vacía.
  Hecho cuando: los tests de CLI pasan para el formato `nombre · racha: N día(s) · hecho hoy|pendiente` con "1 día" y "N días", orden de creación, y mensaje amistoso sin hábitos con código 0 sin crear el archivo.

- [x] **T-15. Errores de datos y de escritura** (RF-4.3, RF-4.5). Traducción de `CorruptData` y `StorageWriteError` en los tres comandos.
  Hecho cuando: los tests pasan para archivo dañado en `add`, `done` y `list` (error en stderr con qué hacer, código 1, archivo byte a byte igual) y para fallo de escritura simulado (mensaje, código 1, original intacto).

- [x] **T-16. Fecha de hoy y punto de entrada real** (RF-4.1, RNF-6, RNF-7). Lectura única de `date.today()` y ejecución como programa.
  Hecho cuando: un test comprueba que `main` sin `today` lee la fecha una sola vez, y un test ejecuta `habits add`, `habits done` y `habits list` como procesos separados con `HABITS_FILE` temporal y los datos se conservan entre ejecuciones.

## Fase 4 — Cierre

- [x] **T-17. Verificación final** (spec secciones 6 y 8). Repaso de casos límite y criterios de finalización.
  Hecho cuando: cada caso límite de la sección 6 de la spec tiene al menos un test, `pytest` completo pasa en verde, `src/` solo importa biblioteca estándar, `core.py` no usa `print`, `input` ni `sys` (revisado con grep), y la tabla de cobertura de abajo no deja ningún RF sin tarea.

## Cobertura de requisitos

| RF | Tareas |
|---|---|
| RF-1.1 | T-3, T-12 |
| RF-1.2 | T-2 |
| RF-1.3 | T-2, T-12 |
| RF-1.4 | T-3, T-12 |
| RF-1.5 | T-3 |
| RF-1.6 | T-2, T-12 |
| RF-1.7 | T-2 |
| RF-2.1–2.5 | T-5, T-13 |
| RF-3.1 | T-6, T-14 |
| RF-3.2, RF-3.3, RF-3.5 | T-4, T-14 |
| RF-3.4 | T-14 |
| RF-4.1 | T-7, T-9, T-16 |
| RF-4.2 | T-7, T-9 |
| RF-4.3 | T-8, T-15 |
| RF-4.4 | T-8 |
| RF-4.5 | T-9, T-15 |
| RF-5.1, RF-5.2 | T-11 |
| RNF-3 | T-10 |
| RNF-4 | T-7 |
| RNF-5 | T-9 |
| RNF-6, RNF-7 | T-16 |
