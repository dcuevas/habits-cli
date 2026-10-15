"""RNF-3: cada comando responde en menos de 1 s con 100 hábitos y 10 años de fechas."""

import time
from datetime import date, timedelta

from habits_cli.core import Habit, list_habits
from habits_cli.storage import load, save

TODAY = date(2026, 10, 14)
HABIT_COUNT = 100
YEARS_OF_DAYS = 3650
LIMIT_SECONDS = 1.0


def big_habits() -> list[Habit]:
    # Racha ininterrumpida hasta hoy: el peor caso para el cálculo de racha.
    dates = {TODAY - timedelta(days=n) for n in range(YEARS_OF_DAYS)}
    return [Habit(f"Hábito {i}", set(dates)) for i in range(HABIT_COUNT)]


def test_load_and_list_100_habits_with_10_years_of_dates_takes_under_one_second(tmp_path):
    path = tmp_path / "habits.json"
    save(path, big_habits())

    start = time.perf_counter()
    statuses = list_habits(load(path), TODAY)
    elapsed = time.perf_counter() - start

    assert len(statuses) == HABIT_COUNT
    assert all(s.streak == YEARS_OF_DAYS and s.done_today for s in statuses)
    assert elapsed < LIMIT_SECONDS


def test_save_100_habits_with_10_years_of_dates_takes_under_one_second(tmp_path):
    habits = big_habits()
    path = tmp_path / "habits.json"

    start = time.perf_counter()
    save(path, habits)
    elapsed = time.perf_counter() - start

    assert elapsed < LIMIT_SECONDS
