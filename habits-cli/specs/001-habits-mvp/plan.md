# Plan técnico 001 — MVP de habits-cli

Plan de [spec.md](spec.md), conforme a la [constitución](../../docs/constitution.md): solo biblioteca estándar (pytest solo para desarrollo), core sin consola, un único JSON, tests como puerta, código en inglés y mensajes en español. Entre corchetes, los requisitos que cubre cada parte.

## 1. Módulos

```
src/habits_cli/
├── core.py       # lógica pura: sin print, input ni archivos
├── storage.py    # lee y guarda el JSON
├── cli.py        # argparse, mensajes en español, códigos de salida
└── __main__.py   # python -m habits_cli
tests/            # test_core.py, test_storage.py, test_cli.py
pyproject.toml    # Python >=3.12, script `habits`, extra [dev] = pytest
```

| Módulo | Contiene | Cubre |
|---|---|---|
| `core.py` | `Habit(name, dates: set[date])`; errores `InvalidName`, `DuplicateHabit`, `HabitNotFound`, `CorruptData`, `StorageWriteError` (sin texto); `validate_name`, `current_streak`, `add_habit`, `mark_done`, `list_habits`. Reciben `today` como parámetro. | RF-1, RF-2, RF-3 |
| `storage.py` | `default_path()` (`HABITS_FILE` o `~/.habits-cli/habits.json`), `load(path)`, `save(path, habits)` | RF-4, RNF-4, RNF-5 |
| `cli.py` | `main(argv, today=None) -> int`. Lee `date.today()` una vez, llama a storage y core, traduce resultados y errores a español. | RF-5, RNF-1, RNF-2, RNF-6, RNF-7 |

Flujo de cada comando: `cli` obtiene `today` → `storage.load` → función del core → `storage.save` solo si cambió algo → mensaje y código de salida.

## 2. Datos JSON  [RF-4, RNF-4]

```json
{
  "habits": [
    {"name": "Leer", "dates": ["2026-10-13", "2026-10-14"]},
    {"name": "Estudiar inglés", "dates": []}
  ]
}
```

- Orden de la lista = orden de creación. `name` va recortado y con su grafía. `dates` son fechas ISO locales; al guardar, ordenadas y sin duplicados. Las fechas futuras se conservan.
- **Dañado** (`CorruptData`): archivo ilegible o JSON inválido (incluido vacío); estructura distinta de la esperada (claves exactas `habits`, `name`, `dates`); nombre inválido o no recortado; nombres duplicados sin distinguir mayúsculas; fecha que no sea exactamente `YYYY-MM-DD` válida. Un archivo inexistente no es dañado: equivale a lista vacía. Fechas duplicadas o desordenadas son válidas.
- **Guardado atómico:** archivo temporal en el mismo directorio y `os.replace`. Si falla, se borra el temporal, el original queda intacto y se lanza `StorageWriteError`. El directorio y el archivo se crean solo al guardar. [RF-4.2, 4.5, RNF-5]

## 3. Racha  [RF-3.2, 3.3, 3.5]

```
current_streak(dates, today):
    cursor = today si today en dates, si no ayer si ayer en dates, si no devolver 0
    n = 0
    mientras cursor en dates: n += 1; cursor -= 1 día
    devolver n
```

Las fechas posteriores a hoy nunca se miran, así que se ignoran sin borrarse. "Hecho hoy" es `today in dates`.

## 4. Contrato de la CLI  [RF-1 a RF-5]

Éxitos y avisos a `stdout`; errores a `stderr`. Los textos son orientativos.

| Comando | Caso | Salida | Código |
|---|---|---|---|
| `habits add "<nombre>"` | válido | `Hábito "Leer" creado.` | 0 |
| | vacío / más de 120 / ya existe | `Error: ...` con qué hacer | 1 |
| `habits done "<nombre>"` | existe | `¡Hecho! "Leer" marcado para hoy.` | 0 |
| | ya marcado hoy | `Aviso: "Leer" ya estaba marcado hoy.` | 0 |
| | no existe o nombre vacío | `Error: no existe ... Créalo con: habits add "X"` | 1 |
| `habits list` | con hábitos | `Leer · racha: 3 días · hecho hoy` (o `1 día`, `pendiente`) | 0 |
| | sin hábitos | `Aún no tienes hábitos. Crea el primero con: habits add "<nombre>"` | 0 |
| cualquiera | datos dañados / no se puede guardar | `Error: ...` con qué hacer; no se modifica el archivo | 1 |
| `--help`, `<comando> --help` | ayuda en español | sintaxis y descripción | 0 |
| uso incorrecto | | `Uso incorrecto. Prueba: habits --help` + línea de sintaxis | 2 |

Los nombres se comparan recortados y con `casefold()`. Ni los errores ni `list` crean el archivo. [RF-1.2–1.7, 2.2]

## 5. Decisiones técnicas

| Decisión | Por qué | Descartado |
|---|---|---|
| `argparse` con ayuda y `error()` propios en español | Stdlib; evita los textos en inglés de argparse [RF-5, RNF-1] | `click`/`typer` (dependencia no permitida) |
| `today` se pasa como parámetro | Tests sin depender del reloj [RNF-6, 7] | `freezegun` / mocks de `date` |
| Errores tipados sin texto en el core; la CLI los traduce | Core sin presentación [constitución 3] | Mensajes en español dentro del core |
| Guardado con temporal + `os.replace` | Sin datos corruptos ante fallos [RNF-5] | Escribir directamente; copias de seguridad |
| `list[Habit]` con `set[date]` | Conserva el orden de creación; tolera duplicados; búsquedas rápidas [RF-3.1, 4.4] | Diccionario por nombre |
| `HABITS_FILE` para apuntar el archivo | Tests con `tmp_path` [RNF-4] | Parchear `Path.home()` |

Consecuencia de `argparse` que la spec no cubre: un nombre que empiece por `-` se toma como opción y da error de uso (se puede escribir con `--`). No se añade comportamiento propio.

## 6. Tests (pytest)

Todos pasan `today` fijo (`date(2026, 10, 14)`) y usan `HABITS_FILE` en `tmp_path`; ninguno toca la fecha real ni el directorio personal. [RNF-6]

- **`test_core.py`:** nombres (recorte, espacios internos, mayúsculas, 120/121, duplicados); `current_streak` con los casos de la sección 6 de la spec; `add_habit`, `mark_done` (incluido ya marcado, inexistente, con fechas futuras) y `list_habits` (orden). [RF-1, 2, 3]
- **`test_storage.py`:** guardar y cargar; cada caso dañado de la sección 2; archivo inexistente; fallo de escritura simulado con `os.replace` (original intacto); 100 hábitos × 3650 fechas en menos de 1 s. [RF-4, RNF-3, 5]
- **`test_cli.py`:** cada fila de la tabla de la sección 4 (salida, código, archivo sin cambios en errores); datos dañados en los tres comandos; ayuda y uso incorrecto; cada error incluye qué hacer. [RF-1 a 5, RNF-1, 2]

Cada tarea termina con sus tests en verde antes de avanzar. [constitución 4]
