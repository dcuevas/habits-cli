"""Lógica pura de habits-cli: sin consola ni archivos."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum

MAX_NAME_LENGTH = 120


class HabitsError(Exception):
    """Base de los errores del core. Llevan datos, nunca texto para el usuario."""


class InvalidName(HabitsError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason  # "empty" | "too_long"


class DuplicateHabit(HabitsError):
    def __init__(self, name: str):
        super().__init__(name)
        self.name = name


class HabitNotFound(HabitsError):
    def __init__(self, name: str):
        super().__init__(name)
        self.name = name


class CorruptData(HabitsError):
    def __init__(self, path: str, detail: str):
        super().__init__(path, detail)
        self.path = path
        self.detail = detail


class StorageWriteError(HabitsError):
    def __init__(self, path: str):
        super().__init__(path)
        self.path = path


class MarkResult(Enum):
    MARKED = "marked"
    ALREADY_DONE = "already_done"


@dataclass(frozen=True)
class HabitStatus:
    name: str
    streak: int
    done_today: bool


@dataclass
class Habit:
    name: str
    dates: set[date] = field(default_factory=set)


def validate_name(raw: str) -> str:
    """Devuelve el nombre sin espacios externos o lanza InvalidName."""
    name = raw.strip()
    if not name:
        raise InvalidName("empty")
    if len(name) > MAX_NAME_LENGTH:
        raise InvalidName("too_long")
    return name


def _key(name: str) -> str:
    """Clave de comparación: nombre ya recortado, sin distinguir mayúsculas."""
    return name.casefold()


def add_habit(habits: list[Habit], raw_name: str) -> Habit:
    """Añade un hábito al final de la lista o lanza InvalidName / DuplicateHabit."""
    name = validate_name(raw_name)
    key = _key(name)
    for existing in habits:
        if _key(existing.name) == key:
            raise DuplicateHabit(existing.name)
    habit = Habit(name)
    habits.append(habit)
    return habit


def is_done_today(dates: set[date], today: date) -> bool:
    return today in dates


def current_streak(dates: set[date], today: date) -> int:
    """Días consecutivos que terminan hoy o, si hoy no está marcado, ayer.

    Las fechas posteriores a hoy nunca se examinan, así que se ignoran.
    """
    if today in dates:
        cursor = today
    elif today != date.min and today - timedelta(days=1) in dates:
        cursor = today - timedelta(days=1)
    else:
        return 0

    count = 0
    while cursor in dates:
        count += 1
        if cursor == date.min:
            break
        cursor -= timedelta(days=1)
    return count


def find_habit(habits: list[Habit], raw_name: str) -> Habit:
    """Busca un hábito sin distinguir mayúsculas ni espacios externos."""
    name = raw_name.strip()
    key = _key(name)
    for habit in habits:
        if _key(habit.name) == key:
            return habit
    raise HabitNotFound(name)


def mark_done(habits: list[Habit], raw_name: str, today: date) -> MarkResult:
    """Registra hoy para el hábito indicado o lanza HabitNotFound."""
    habit = find_habit(habits, raw_name)
    if today in habit.dates:
        return MarkResult.ALREADY_DONE
    habit.dates.add(today)
    return MarkResult.MARKED


def list_habits(habits: list[Habit], today: date) -> list[HabitStatus]:
    """Estado de cada hábito, en el mismo orden que la lista."""
    return [
        HabitStatus(
            name=habit.name,
            streak=current_streak(habit.dates, today),
            done_today=is_done_today(habit.dates, today),
        )
        for habit in habits
    ]
