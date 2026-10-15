"""Un test de extremo a extremo (por la CLI) por cada caso límite de la sección 6 de la spec."""

from datetime import date, timedelta

import pytest

from habits_cli.cli import main
from habits_cli.core import Habit
from habits_cli.storage import load, save

TODAY = date(2026, 10, 14)


def ago(days: int) -> date:
    return TODAY - timedelta(days=days)


@pytest.fixture
def data_file(tmp_path, monkeypatch):
    path = tmp_path / "datos" / "habits.json"
    monkeypatch.setenv("HABITS_FILE", str(path))
    return path


@pytest.fixture
def run(capsys):
    def _run(*argv: str, today: date = TODAY):
        code = main(list(argv), today=today)
        out, err = capsys.readouterr()
        return code, out, err

    return _run


def listing(run, today: date = TODAY) -> str:
    code, out, err = run("list", today=today)
    assert (code, err) == (0, "")
    return out


def test_marked_yesterday_and_day_before_but_not_today_keeps_streak(data_file, run):
    save(data_file, [Habit("Leer", {ago(2), ago(1)})])
    assert listing(run) == "Leer · racha: 2 días · pendiente\n"


def test_marked_today_yesterday_and_day_before_has_streak_of_three(data_file, run):
    save(data_file, [Habit("Leer", {ago(2), ago(1), ago(0)})])
    assert listing(run) == "Leer · racha: 3 días · hecho hoy\n"


def test_gap_between_marked_days_restarts_streak_from_the_latest(data_file, run):
    save(data_file, [Habit("Leer", {ago(3), ago(0)})])  # ni ayer ni anteayer
    assert listing(run) == "Leer · racha: 1 día · hecho hoy\n"


def test_not_marked_today_nor_yesterday_has_streak_zero(data_file, run):
    save(data_file, [Habit("Leer", {ago(2), ago(3), ago(4)})])
    assert listing(run) == "Leer · racha: 0 días · pendiente\n"


def test_new_habit_never_marked_has_streak_zero_and_is_pending(data_file, run):
    assert run("add", "Leer")[0] == 0
    assert listing(run) == "Leer · racha: 0 días · pendiente\n"


def test_habit_with_only_future_dates_has_streak_zero_and_is_pending(data_file, run):
    save(data_file, [Habit("Leer", {ago(-1), ago(-2)})])
    assert listing(run) == "Leer · racha: 0 días · pendiente\n"


def test_names_differing_only_in_case_or_outer_spaces_are_the_same_habit(data_file, run):
    assert run("add", "Leer")[0] == 0
    assert run("add", "  LEER ")[0] == 1
    assert run("done", " leer")[0] == 0
    assert [h.name for h in load(data_file)] == ["Leer"]


def test_names_differing_in_internal_spaces_are_different_habits(data_file, run):
    assert run("add", "Leer mucho")[0] == 0
    assert run("add", "Leer  mucho")[0] == 0
    assert [h.name for h in load(data_file)] == ["Leer mucho", "Leer  mucho"]


def test_empty_name_is_rejected_by_add_and_is_not_found_by_done(data_file, run):
    save(data_file, [Habit("Leer")])
    before = data_file.read_bytes()
    for blank in ("", "   "):
        assert run("add", blank)[0] == 1
        assert run("done", blank)[0] == 1
    assert data_file.read_bytes() == before


def test_name_of_120_characters_is_valid_and_121_is_rejected(data_file, run):
    assert run("add", "a" * 120)[0] == 0
    code, _, err = run("add", "b" * 121)
    assert code == 1
    assert "120" in err
    assert [h.name for h in load(data_file)] == ["a" * 120]


def test_marking_a_nonexistent_habit_fails_and_creates_nothing(data_file, run):
    save(data_file, [Habit("Leer")])
    code, _, err = run("done", "Correr")
    assert code == 1
    assert "no existe" in err
    assert [h.name for h in load(data_file)] == ["Leer"]


def test_corrupt_data_makes_commands_fail_without_modifying_the_file(data_file, run):
    data_file.parent.mkdir(parents=True)
    data_file.write_text('{"habits": [', encoding="utf-8")
    for argv in (["list"], ["add", "Leer"], ["done", "Leer"]):
        code, out, err = run(*argv)
        assert (code, out) == (1, "")
        assert "no se pueden leer los datos" in err
    assert data_file.read_text(encoding="utf-8") == '{"habits": ['


def test_first_use_lists_friendly_message_without_errors_or_files(data_file, run):
    code, out, err = run("list")
    assert code == 0
    assert err == ""
    assert 'habits add "<nombre>"' in out
    assert not data_file.parent.exists()


def test_marking_the_same_habit_several_times_in_a_day_keeps_one_record(data_file, run):
    assert run("add", "Leer")[0] == 0
    assert run("done", "Leer")[0] == 0
    for _ in range(3):
        code, out, _ = run("done", "Leer")
        assert code == 0
        assert out.startswith("Aviso:")
    assert load(data_file)[0].dates == {TODAY}


def test_day_change_while_tool_is_not_in_use_is_evaluated_with_the_query_date(data_file, run):
    save(data_file, [Habit("Leer", {ago(1), ago(0)})])
    assert listing(run, today=TODAY) == "Leer · racha: 2 días · hecho hoy\n"
    assert listing(run, today=TODAY + timedelta(days=1)) == "Leer · racha: 2 días · pendiente\n"
    assert listing(run, today=TODAY + timedelta(days=2)) == "Leer · racha: 0 días · pendiente\n"
