from datetime import date

import pytest

from habits_cli.core import (
    MAX_NAME_LENGTH,
    CorruptData,
    DuplicateHabit,
    Habit,
    HabitNotFound,
    InvalidName,
    StorageWriteError,
    add_habit,
    current_streak,
    find_habit,
    HabitStatus,
    is_done_today,
    list_habits,
    mark_done,
    validate_name,
    MarkResult,
)

TODAY = date(2026, 10, 14)


def days(*day_numbers: int) -> set[date]:
    """Fechas de octubre de 2026 a partir del número de día."""
    return {date(2026, 10, d) for d in day_numbers}


# --- Habit y errores -------------------------------------------------------


def test_habit_starts_without_completed_days():
    habit = Habit("Leer")
    assert habit.name == "Leer"
    assert habit.dates == set()


def test_habits_do_not_share_their_dates():
    first, second = Habit("Leer"), Habit("Correr")
    first.dates.add(date(2026, 10, 14))
    assert second.dates == set()


def test_typed_errors_carry_data_not_text():
    assert InvalidName("empty").reason == "empty"
    assert DuplicateHabit("Leer").name == "Leer"
    assert HabitNotFound("Leer").name == "Leer"
    assert CorruptData("/tmp/x.json", "json").path == "/tmp/x.json"
    assert CorruptData("/tmp/x.json", "json").detail == "json"
    assert StorageWriteError("/tmp/x.json").path == "/tmp/x.json"


# --- validate_name: RF-1.2 (recorte) ---------------------------------------


def test_valid_name_is_returned_unchanged():
    assert validate_name("Leer") == "Leer"


def test_strips_regular_spaces_at_both_ends():
    assert validate_name("   Leer  ") == "Leer"


def test_strips_tabs_and_non_breaking_spaces():
    assert validate_name("\t Leer \t") == "Leer"


def test_keeps_original_casing():
    assert validate_name("  LeEr Mucho ") == "LeEr Mucho"


def test_internal_spaces_are_untouched():
    assert validate_name("Leer  mucho") == "Leer  mucho"
    assert validate_name("Leer  mucho") != validate_name("Leer mucho")


# --- validate_name: RF-1.3 (vacío) -----------------------------------------


@pytest.mark.parametrize("raw", ["", " ", "   ", "\t", " ", " \t  "])
def test_empty_or_blank_name_is_rejected(raw):
    with pytest.raises(InvalidName) as error:
        validate_name(raw)
    assert error.value.reason == "empty"


# --- validate_name: RF-1.6 (límite de 120) ---------------------------------


def test_name_of_exactly_120_characters_is_valid():
    name = "a" * MAX_NAME_LENGTH
    assert MAX_NAME_LENGTH == 120
    assert validate_name(name) == name


def test_name_of_121_characters_is_rejected():
    with pytest.raises(InvalidName) as error:
        validate_name("a" * 121)
    assert error.value.reason == "too_long"


def test_length_is_counted_after_stripping_outer_spaces():
    name = "a" * 120
    assert validate_name(f"  {name}  ") == name


# --- validate_name: RF-1.7 (sin otras restricciones) -----------------------


@pytest.mark.parametrize("name", ["Estudiar inglés 📚", "Línea1\nLínea2", "-x", "ñandú", "a/b"])
def test_no_other_restrictions_on_characters(name):
    assert validate_name(name) == name


# --- add_habit: RF-1.1, RF-1.4, RF-1.5 -------------------------------------


def test_add_habit_creates_habit_without_completed_days():
    habits: list[Habit] = []
    created = add_habit(habits, "Leer")
    assert created.name == "Leer"
    assert created.dates == set()
    assert habits == [created]


def test_add_habit_appends_at_the_end_in_creation_order():
    habits: list[Habit] = []
    add_habit(habits, "Leer")
    add_habit(habits, "Correr")
    add_habit(habits, "Escribir")
    assert [h.name for h in habits] == ["Leer", "Correr", "Escribir"]


def test_add_habit_keeps_original_casing_without_outer_spaces():
    habits: list[Habit] = []
    add_habit(habits, "  LeEr MuCho \t")
    assert habits[0].name == "LeEr MuCho"


@pytest.mark.parametrize("duplicate", ["leer", "LEER", "  Leer  ", "\tlEEr "])
def test_add_habit_rejects_duplicate_ignoring_case_and_outer_spaces(duplicate):
    habits = [Habit("Leer")]
    with pytest.raises(DuplicateHabit) as error:
        add_habit(habits, duplicate)
    assert error.value.name == "Leer"
    assert [h.name for h in habits] == ["Leer"]


def test_add_habit_treats_different_internal_spaces_as_different_habits():
    habits: list[Habit] = []
    add_habit(habits, "Leer mucho")
    add_habit(habits, "Leer  mucho")
    assert [h.name for h in habits] == ["Leer mucho", "Leer  mucho"]


@pytest.mark.parametrize("raw", ["", "   ", "a" * 121])
def test_add_habit_leaves_list_untouched_on_invalid_name(raw):
    habits = [Habit("Leer")]
    with pytest.raises(InvalidName):
        add_habit(habits, raw)
    assert [h.name for h in habits] == ["Leer"]


def test_add_habit_does_not_modify_existing_habits():
    existing = Habit("Leer", {date(2026, 10, 13)})
    habits = [existing]
    with pytest.raises(DuplicateHabit):
        add_habit(habits, "leer")
    assert existing.dates == {date(2026, 10, 13)}


# --- current_streak / is_done_today: RF-3.2, RF-3.3, RF-3.5 ----------------


@pytest.mark.parametrize(
    ("dates", "streak", "done_today"),
    [
        (days(12, 13, 14), 3, True),  # hoy, ayer y anteayer
        (days(12, 13), 2, False),  # termina ayer: la racha se mantiene
        (days(11, 14), 1, True),  # hueco: se cuenta desde la fecha más reciente
        (days(12), 0, False),  # ni hoy ni ayer
        (set(), 0, False),  # sin días completados
        (days(14), 1, True),  # solo hoy
        (days(13), 1, False),  # solo ayer
        (days(15, 20), 0, False),  # solo fechas futuras
        (days(13, 14, 15), 2, True),  # una fecha futura no cuenta
        (days(13, 15, 16), 1, False),  # futuras ignoradas, termina ayer
        (days(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14), 14, True),  # racha larga
    ],
)
def test_streak_and_done_today(dates, streak, done_today):
    assert current_streak(dates, TODAY) == streak
    assert is_done_today(dates, TODAY) is done_today


def test_streak_does_not_modify_the_dates():
    dates = days(13, 14, 15)
    current_streak(dates, TODAY)
    assert dates == days(13, 14, 15)


def test_streak_crosses_month_and_year_boundaries():
    dates = {date(2025, 12, 30), date(2025, 12, 31), date(2026, 1, 1)}
    assert current_streak(dates, date(2026, 1, 1)) == 3


def test_streak_includes_leap_day():
    dates = {date(2028, 2, 28), date(2028, 2, 29), date(2028, 3, 1)}
    assert current_streak(dates, date(2028, 3, 1)) == 3


def test_streak_does_not_overflow_at_minimum_date():
    assert current_streak({date.min}, date.min) == 1


# --- mark_done: RF-2.1 a RF-2.5 --------------------------------------------


def test_mark_done_registers_today_for_the_habit():
    habits = [Habit("Leer"), Habit("Correr")]
    assert mark_done(habits, "Leer", TODAY) is MarkResult.MARKED
    assert habits[0].dates == {TODAY}
    assert habits[1].dates == set()


@pytest.mark.parametrize("raw", ["leer", "LEER", "  Leer  ", "\tlEEr "])
def test_mark_done_finds_habit_ignoring_case_and_outer_spaces(raw):
    habits = [Habit("Leer")]
    assert mark_done(habits, raw, TODAY) is MarkResult.MARKED
    assert habits[0].dates == {TODAY}
    assert habits[0].name == "Leer"


def test_mark_done_twice_does_not_duplicate_the_record():
    habits = [Habit("Leer")]
    assert mark_done(habits, "Leer", TODAY) is MarkResult.MARKED
    assert mark_done(habits, "leer", TODAY) is MarkResult.ALREADY_DONE
    assert habits[0].dates == {TODAY}


def test_mark_done_already_marked_today_changes_nothing():
    habits = [Habit("Leer", days(13, 14))]
    assert mark_done(habits, "Leer", TODAY) is MarkResult.ALREADY_DONE
    assert habits[0].dates == days(13, 14)


def test_mark_done_unknown_habit_raises_and_creates_nothing():
    habits = [Habit("Leer")]
    with pytest.raises(HabitNotFound) as error:
        mark_done(habits, "  Correr ", TODAY)
    assert error.value.name == "Correr"
    assert [h.name for h in habits] == ["Leer"]
    assert habits[0].dates == set()


@pytest.mark.parametrize("raw", ["", "   ", "\t "])
def test_mark_done_empty_name_is_habit_not_found(raw):
    habits = [Habit("Leer")]
    with pytest.raises(HabitNotFound):
        mark_done(habits, raw, TODAY)
    assert habits[0].dates == set()


def test_mark_done_on_empty_list_raises_habit_not_found():
    habits: list[Habit] = []
    with pytest.raises(HabitNotFound):
        mark_done(habits, "Leer", TODAY)
    assert habits == []


def test_mark_done_with_future_dates_registers_today_and_keeps_them():
    habits = [Habit("Leer", days(15, 20))]
    assert mark_done(habits, "Leer", TODAY) is MarkResult.MARKED
    assert habits[0].dates == days(14, 15, 20)


def test_mark_done_does_not_match_names_with_different_internal_spaces():
    habits = [Habit("Leer  mucho")]
    with pytest.raises(HabitNotFound):
        mark_done(habits, "Leer mucho", TODAY)


# --- list_habits: RF-3.1 ---------------------------------------------------


def test_list_habits_returns_empty_list_when_there_are_no_habits():
    assert list_habits([], TODAY) == []


def test_list_habits_reports_name_streak_and_done_today():
    habits = [Habit("Leer", days(12, 13, 14))]
    assert list_habits(habits, TODAY) == [HabitStatus("Leer", 3, True)]


def test_list_habits_keeps_creation_order():
    habits = [Habit("Zeta"), Habit("Alfa"), Habit("Mu")]
    assert [s.name for s in list_habits(habits, TODAY)] == ["Zeta", "Alfa", "Mu"]


def test_list_habits_with_several_habits_has_correct_values_for_each():
    habits = [
        Habit("Hecho hoy", days(13, 14)),
        Habit("Termina ayer", days(12, 13)),
        Habit("Roto", days(10)),
        Habit("Nuevo"),
        Habit("Solo futuras", days(15, 16)),
    ]
    assert list_habits(habits, TODAY) == [
        HabitStatus("Hecho hoy", 2, True),
        HabitStatus("Termina ayer", 2, False),
        HabitStatus("Roto", 0, False),
        HabitStatus("Nuevo", 0, False),
        HabitStatus("Solo futuras", 0, False),
    ]


def test_list_habits_does_not_modify_the_habits():
    habits = [Habit("Leer", days(13, 15))]
    list_habits(habits, TODAY)
    assert habits == [Habit("Leer", days(13, 15))]


def test_habit_status_is_immutable():
    status = HabitStatus("Leer", 1, True)
    with pytest.raises(AttributeError):
        status.streak = 5  # type: ignore[misc]


# --- find_habit: RF-2.2 ----------------------------------------------------


@pytest.mark.parametrize("raw", ["Leer", "leer", "LEER", "  Leer  ", "\tlEEr\u00a0"])
def test_find_habit_returns_the_stored_habit_ignoring_case_and_outer_spaces(raw):
    stored = Habit("Leer")
    assert find_habit([Habit("Correr"), stored], raw) is stored


@pytest.mark.parametrize("raw", ["Escribir", "", "   ", "Leer mucho"])
def test_find_habit_raises_habit_not_found(raw):
    with pytest.raises(HabitNotFound) as error:
        find_habit([Habit("Leer  mucho"), Habit("Correr")], raw)
    assert error.value.name == raw.strip()
