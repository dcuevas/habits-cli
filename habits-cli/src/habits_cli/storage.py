"""Lectura y escritura del archivo JSON de datos. Sin entrada/salida de consola."""

import json
import os
import tempfile
from datetime import date
from pathlib import Path

from habits_cli.core import (
    CorruptData,
    Habit,
    InvalidName,
    StorageWriteError,
    validate_name,
)


def default_path() -> Path:
    """HABITS_FILE si está definida y no vacía; si no, ~/.habits-cli/habits.json."""
    custom = os.environ.get("HABITS_FILE")
    if custom:
        return Path(custom)
    return Path.home() / ".habits-cli" / "habits.json"


def load(path: Path | str) -> list[Habit]:
    """Carga los hábitos o lanza CorruptData si los datos están dañados.

    Un archivo inexistente equivale a no tener hábitos. Nunca modifica el archivo.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except (OSError, UnicodeDecodeError) as error:
        raise CorruptData(str(path), f"no se puede leer el archivo: {error}") from error

    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise CorruptData(str(path), f"JSON inválido: {error}") from error

    try:
        return _parse(data)
    except ValueError as error:
        raise CorruptData(str(path), str(error)) from error


def save(path: Path | str, habits: list[Habit]) -> None:
    """Guarda los hábitos de forma atómica o lanza StorageWriteError.

    Escribe en un archivo temporal del mismo directorio y lo renombra sobre el
    original; si algo falla, el original queda intacto y el temporal se borra.
    """
    path = Path(path)
    data = {
        "habits": [
            {"name": h.name, "dates": sorted(d.isoformat() for d in h.dates)}
            for h in habits
        ]
    }
    temp_name: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=".habits-", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            json.dump(data, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, path)
    except OSError as error:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
        raise StorageWriteError(str(path)) from error


def _parse(data: object) -> list[Habit]:
    if not isinstance(data, dict) or set(data) != {"habits"}:
        raise ValueError('la estructura debe ser un objeto con la clave "habits"')
    items = data["habits"]
    if not isinstance(items, list):
        raise ValueError('"habits" debe ser una lista')

    habits: list[Habit] = []
    seen: set[str] = set()
    for item in items:
        habit = _parse_habit(item)
        key = habit.name.casefold()
        if key in seen:
            raise ValueError(f"nombre duplicado: {habit.name!r}")
        seen.add(key)
        habits.append(habit)
    return habits


def _parse_habit(item: object) -> Habit:
    if not isinstance(item, dict) or set(item) != {"name", "dates"}:
        raise ValueError('cada hábito debe tener exactamente "name" y "dates"')
    name, raw_dates = item["name"], item["dates"]
    if not isinstance(name, str):
        raise ValueError('"name" debe ser texto')
    if not isinstance(raw_dates, list):
        raise ValueError('"dates" debe ser una lista')

    try:
        valid_name = validate_name(name)
    except InvalidName as error:
        raise ValueError(f"nombre inválido ({error.reason}): {name!r}") from error
    if valid_name != name:
        raise ValueError(f"el nombre debe estar sin espacios externos: {name!r}")

    return Habit(name, {_parse_date(raw) for raw in raw_dates})


def _parse_date(raw: object) -> date:
    if not isinstance(raw, str):
        raise ValueError(f"fecha inválida: {raw!r}")
    parsed = date.fromisoformat(raw)  # ValueError si no es una fecha válida
    if parsed.isoformat() != raw:  # rechaza formatos como 20261014
        raise ValueError(f"la fecha debe tener formato AAAA-MM-DD: {raw!r}")
    return parsed
