import json
from datetime import date
from pathlib import Path

import pytest

from habits_cli.core import CorruptData, Habit, StorageWriteError
from habits_cli.storage import default_path, load, save


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# --- default_path: RNF-4 ---------------------------------------------------


def test_habits_file_variable_takes_priority(monkeypatch, tmp_path):
    target = tmp_path / "otro" / "datos.json"
    monkeypatch.setenv("HABITS_FILE", str(target))
    assert default_path() == target


def test_default_path_is_in_home_directory(monkeypatch, tmp_path):
    monkeypatch.delenv("HABITS_FILE", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert default_path() == tmp_path / ".habits-cli" / "habits.json"


def test_empty_habits_file_variable_is_ignored(monkeypatch, tmp_path):
    monkeypatch.setenv("HABITS_FILE", "")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert default_path() == tmp_path / ".habits-cli" / "habits.json"


# --- load: archivo inexistente (RF-4.2) ------------------------------------


def test_missing_file_loads_as_no_habits(tmp_path):
    assert load(tmp_path / "habits.json") == []


def test_missing_file_and_directory_are_not_created(tmp_path):
    path = tmp_path / ".habits-cli" / "habits.json"
    assert load(path) == []
    assert not path.exists()
    assert not path.parent.exists()


# --- load: JSON válido (RF-4.1) --------------------------------------------


def test_valid_file_is_loaded_with_dates_as_a_set(tmp_path):
    path = tmp_path / "habits.json"
    write_json(
        path,
        {"habits": [{"name": "Leer", "dates": ["2026-10-13", "2026-10-14"]}]},
    )
    habits = load(path)
    assert habits == [Habit("Leer", {date(2026, 10, 13), date(2026, 10, 14)})]
    assert isinstance(habits[0].dates, set)


def test_empty_habit_list_loads_as_no_habits(tmp_path):
    path = tmp_path / "habits.json"
    write_json(path, {"habits": []})
    assert load(path) == []


def test_habit_without_dates_loads_with_empty_set(tmp_path):
    path = tmp_path / "habits.json"
    write_json(path, {"habits": [{"name": "Leer", "dates": []}]})
    assert load(path) == [Habit("Leer", set())]


def test_order_of_habits_in_file_is_preserved(tmp_path):
    path = tmp_path / "habits.json"
    write_json(
        path,
        {
            "habits": [
                {"name": "Zeta", "dates": []},
                {"name": "Alfa", "dates": []},
                {"name": "Mu", "dates": []},
            ]
        },
    )
    assert [h.name for h in load(path)] == ["Zeta", "Alfa", "Mu"]


def test_names_with_accents_and_emoji_are_read_as_utf8(tmp_path):
    path = tmp_path / "habits.json"
    write_json(path, {"habits": [{"name": "Estudiar inglés 📚", "dates": []}]})
    assert load(path)[0].name == "Estudiar inglés 📚"


def test_load_accepts_a_string_path(tmp_path):
    path = tmp_path / "habits.json"
    write_json(path, {"habits": [{"name": "Leer", "dates": []}]})
    assert load(str(path)) == [Habit("Leer", set())]


# --- load: datos dañados (RF-4.3) ------------------------------------------


def habit(name="Leer", dates=()):
    return {"name": name, "dates": list(dates)}


def assert_corrupt(path: Path) -> CorruptData:
    with pytest.raises(CorruptData) as error:
        load(path)
    assert error.value.path == str(path)
    assert error.value.detail
    return error.value


def test_unreadable_file_is_corrupt(tmp_path):
    path = tmp_path / "habits.json"
    path.mkdir()  # leer un directorio como archivo falla con OSError
    assert_corrupt(path)


def test_file_that_is_not_utf8_is_corrupt(tmp_path):
    path = tmp_path / "habits.json"
    path.write_bytes(b"\xff\xfe\x00")
    assert_corrupt(path)


@pytest.mark.parametrize("content", ["", "   \n", "{", "no es json", '{"habits": ['])
def test_invalid_or_empty_json_is_corrupt(tmp_path, content):
    path = tmp_path / "habits.json"
    path.write_text(content, encoding="utf-8")
    assert_corrupt(path)


@pytest.mark.parametrize(
    "data",
    [
        [],
        "habits",
        None,
        {},
        {"habitos": []},
        {"habits": {}},
        {"habits": None},
        {"habits": [], "version": 1},
        {"habits": ["Leer"]},
        {"habits": [{"name": "Leer"}]},
        {"habits": [{"dates": []}]},
        {"habits": [{"name": "Leer", "dates": [], "extra": 1}]},
        {"habits": [{"name": 5, "dates": []}]},
        {"habits": [{"name": None, "dates": []}]},
        {"habits": [{"name": "Leer", "dates": "2026-10-14"}]},
        {"habits": [{"name": "Leer", "dates": None}]},
        {"habits": [{"name": "Leer", "dates": [20261014]}]},
        {"habits": [{"name": "Leer", "dates": [None]}]},
    ],
)
def test_wrong_structure_is_corrupt(tmp_path, data):
    path = tmp_path / "habits.json"
    write_json(path, data)
    assert_corrupt(path)


@pytest.mark.parametrize(
    "name", ["", "   ", "a" * 121, " Leer", "Leer ", "\tLeer", "Leer\u00a0"]
)
def test_invalid_or_untrimmed_name_is_corrupt(tmp_path, name):
    path = tmp_path / "habits.json"
    write_json(path, {"habits": [habit(name)]})
    assert_corrupt(path)


def test_name_of_exactly_120_characters_is_valid(tmp_path):
    path = tmp_path / "habits.json"
    write_json(path, {"habits": [habit("a" * 120)]})
    assert load(path)[0].name == "a" * 120


@pytest.mark.parametrize("second", ["Leer", "leer", "LEER", "LeEr"])
def test_duplicate_names_ignoring_case_are_corrupt(tmp_path, second):
    path = tmp_path / "habits.json"
    write_json(path, {"habits": [habit("Leer"), habit(second)]})
    assert_corrupt(path)


def test_names_differing_in_internal_spaces_are_not_duplicates(tmp_path):
    path = tmp_path / "habits.json"
    write_json(path, {"habits": [habit("Leer mucho"), habit("Leer  mucho")]})
    assert len(load(path)) == 2


@pytest.mark.parametrize(
    "bad_date",
    [
        "20261014",
        "2026-13-01",
        "2026-02-30",
        "2026-10-14T00:00:00",
        " 2026-10-14",
        "2026-10-14 ",
        "2026-1-4",
        "14/10/2026",
        "hoy",
        "",
    ],
)
def test_invalid_date_format_is_corrupt(tmp_path, bad_date):
    path = tmp_path / "habits.json"
    write_json(path, {"habits": [habit(dates=[bad_date])]})
    assert_corrupt(path)


# --- load: datos válidos que no son dañados (RF-4.4, RF-3.5) ---------------


def test_duplicate_dates_are_accepted_as_a_set(tmp_path):
    path = tmp_path / "habits.json"
    write_json(path, {"habits": [habit(dates=["2026-10-14", "2026-10-14"])]})
    assert load(path)[0].dates == {date(2026, 10, 14)}


def test_unsorted_dates_are_accepted(tmp_path):
    path = tmp_path / "habits.json"
    write_json(
        path,
        {"habits": [habit(dates=["2026-10-14", "2026-10-12", "2026-10-13"])]},
    )
    assert load(path)[0].dates == {
        date(2026, 10, 12),
        date(2026, 10, 13),
        date(2026, 10, 14),
    }


def test_future_dates_are_accepted(tmp_path):
    path = tmp_path / "habits.json"
    write_json(path, {"habits": [habit(dates=["2999-01-01"])]})
    assert load(path)[0].dates == {date(2999, 1, 1)}


def test_corrupt_file_is_never_modified_by_load(tmp_path):
    path = tmp_path / "habits.json"
    path.write_text("{ roto", encoding="utf-8")
    with pytest.raises(CorruptData):
        load(path)
    assert path.read_text(encoding="utf-8") == "{ roto"


# --- save: guardado atómico (RF-4.1, RF-4.2, RF-4.5, RNF-5) ----------------


def sample_habits() -> list[Habit]:
    return [
        Habit("Leer", {date(2026, 10, 13), date(2026, 10, 14)}),
        Habit("Estudiar inglés 📚"),
        Habit("Con futuras", {date(2026, 10, 14), date(2999, 1, 1)}),
    ]


def test_save_then_load_returns_the_same_habits(tmp_path):
    path = tmp_path / "habits.json"
    save(path, sample_habits())
    assert load(path) == sample_habits()


def test_save_creates_missing_directory_and_file(tmp_path):
    path = tmp_path / ".habits-cli" / "datos" / "habits.json"
    save(path, sample_habits())
    assert path.is_file()


def test_save_accepts_a_string_path(tmp_path):
    path = tmp_path / "habits.json"
    save(str(path), sample_habits())
    assert load(path) == sample_habits()


def test_save_writes_dates_sorted_without_duplicates(tmp_path):
    path = tmp_path / "habits.json"
    save(path, [Habit("Leer", {date(2026, 10, 14), date(2026, 1, 2), date(2026, 10, 3)})])
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {
        "habits": [{"name": "Leer", "dates": ["2026-01-02", "2026-10-03", "2026-10-14"]}]
    }


def test_save_keeps_habit_order(tmp_path):
    path = tmp_path / "habits.json"
    save(path, [Habit("Zeta"), Habit("Alfa"), Habit("Mu")])
    assert [h.name for h in load(path)] == ["Zeta", "Alfa", "Mu"]


def test_save_writes_readable_utf8_json(tmp_path):
    path = tmp_path / "habits.json"
    save(path, [Habit("Estudiar inglés 📚")])
    text = path.read_text(encoding="utf-8")
    assert "Estudiar inglés 📚" in text
    assert "\\u" not in text
    assert "\n  " in text  # con sangría


def test_save_replaces_previous_content(tmp_path):
    path = tmp_path / "habits.json"
    save(path, [Habit("Leer"), Habit("Correr")])
    save(path, [Habit("Solo")])
    assert load(path) == [Habit("Solo")]


def test_save_leaves_no_temporary_files(tmp_path):
    path = tmp_path / "habits.json"
    save(path, sample_habits())
    save(path, sample_habits())
    assert [p.name for p in tmp_path.iterdir()] == ["habits.json"]


def test_failed_replace_keeps_original_and_leaves_no_temporary_files(tmp_path, monkeypatch):
    path = tmp_path / "habits.json"
    save(path, [Habit("Original")])
    before = path.read_bytes()

    def broken_replace(*args, **kwargs):
        raise OSError("disco lleno")

    monkeypatch.setattr("habits_cli.storage.os.replace", broken_replace)
    with pytest.raises(StorageWriteError) as error:
        save(path, [Habit("Nuevo")])

    assert error.value.path == str(path)
    assert path.read_bytes() == before
    assert [p.name for p in tmp_path.iterdir()] == ["habits.json"]


def test_failure_while_writing_keeps_original_and_leaves_no_temporary_files(
    tmp_path, monkeypatch
):
    path = tmp_path / "habits.json"
    save(path, [Habit("Original")])
    before = path.read_bytes()

    def broken_fsync(fd):
        raise OSError("fallo de disco")

    monkeypatch.setattr("habits_cli.storage.os.fsync", broken_fsync)
    with pytest.raises(StorageWriteError):
        save(path, [Habit("Nuevo")])

    assert path.read_bytes() == before
    assert [p.name for p in tmp_path.iterdir()] == ["habits.json"]


def test_save_failure_on_first_use_creates_no_data_file(tmp_path, monkeypatch):
    path = tmp_path / "habits.json"

    def broken_replace(*args, **kwargs):
        raise OSError("sin permisos")

    monkeypatch.setattr("habits_cli.storage.os.replace", broken_replace)
    with pytest.raises(StorageWriteError):
        save(path, [Habit("Leer")])
    assert list(tmp_path.iterdir()) == []


def test_save_raises_storage_write_error_when_directory_cannot_be_created(tmp_path):
    blocker = tmp_path / "es-un-archivo"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(StorageWriteError):
        save(blocker / "habits.json", [Habit("Leer")])
