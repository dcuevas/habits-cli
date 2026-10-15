from datetime import date

import pytest

from habits_cli.cli import main
from habits_cli.core import Habit
from habits_cli.storage import load, save

TODAY = date(2026, 10, 14)

# Textos por defecto de argparse (en inglés) que no deben aparecer nunca.
ENGLISH_ARGPARSE_WORDS = [
    "usage:",
    "options:",
    "positional arguments",
    "error:",
    "unrecognized",
    "required",
    "invalid choice",
    "the following arguments",
    "show this help message",
]


def assert_no_english(text: str) -> None:
    lowered = text.lower()
    for word in ENGLISH_ARGPARSE_WORDS:
        assert word not in lowered, f"texto en inglés de argparse: {word!r}"


@pytest.fixture(autouse=True)
def data_file(tmp_path, monkeypatch):
    path = tmp_path / "datos" / "habits.json"
    monkeypatch.setenv("HABITS_FILE", str(path))
    return path


# --- Ayuda: RF-5.1 ---------------------------------------------------------


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_global_help_is_in_spanish_and_exits_with_zero(flag, capsys):
    assert main([flag]) == 0
    out, err = capsys.readouterr()
    assert err == ""
    assert out.startswith("Uso: habits <comando> [argumentos]")
    assert "Comandos" in out
    for command in ('add "<nombre>"', 'done "<nombre>"', "list"):
        assert command in out
    assert "habits <comando> --help" in out
    assert_no_english(out)


@pytest.mark.parametrize(
    ("command", "syntax", "description"),
    [
        ("add", 'Uso: habits add "<nombre>"', "Crea un hábito"),
        ("done", 'Uso: habits done "<nombre>"', "Marca un hábito como hecho hoy"),
        ("list", "Uso: habits list", "racha"),
    ],
)
@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_command_help_shows_syntax_and_description_in_spanish(
    command, syntax, description, flag, capsys
):
    assert main([command, flag]) == 0
    out, err = capsys.readouterr()
    assert err == ""
    assert out.startswith(syntax)
    assert description in out
    assert_no_english(out)


def test_command_help_wins_over_other_arguments(capsys):
    assert main(["add", "Leer", "--help"]) == 0
    out, _ = capsys.readouterr()
    assert out.startswith('Uso: habits add "<nombre>"')


def test_help_does_not_create_the_data_file(data_file, capsys):
    main(["--help"])
    main(["add", "--help"])
    assert not data_file.exists()
    assert not data_file.parent.exists()


# --- Uso incorrecto: RF-5.2 ------------------------------------------------

GENERAL = "Uso: habits <comando> [argumentos]"
ADD = 'Uso: habits add "<nombre>"'
DONE = 'Uso: habits done "<nombre>"'
LIST = "Uso: habits list"


@pytest.mark.parametrize(
    ("argv", "syntax"),
    [
        ([], GENERAL),  # sin comando
        (["foo"], GENERAL),  # comando desconocido
        (["Add", "Leer"], GENERAL),  # los comandos distinguen mayúsculas
        (["ad", "Leer"], GENERAL),  # sin abreviaturas de comando
        (["--nope"], GENERAL),  # opción desconocida
        (["add"], ADD),  # faltan argumentos
        (["add", "Leer", "mucho"], ADD),  # argumentos de más
        (["add", "--nope"], ADD),
        (["add", "-x"], ADD),  # un nombre que parece opción
        (["done"], DONE),
        (["done", "Leer", "otro"], DONE),
        (["done", "--nope", "Leer"], DONE),
        (["list", "Leer"], LIST),
        (["list", "--nope"], LIST),
    ],
)
def test_incorrect_usage_shows_spanish_message_syntax_and_exits_with_2(argv, syntax, capsys):
    assert main(argv) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.splitlines() == ["Uso incorrecto. Prueba: habits --help", syntax]
    assert_no_english(err)


def test_incorrect_usage_does_not_create_the_data_file(data_file):
    main([])
    main(["add"])
    main(["foo"])
    assert not data_file.exists()
    assert not data_file.parent.exists()


# --- Comando add: RF-1.1, RF-1.3, RF-1.4, RF-1.6 ---------------------------


def add(name: str, capsys):
    code = main(["add", name], today=TODAY)
    out, err = capsys.readouterr()
    return code, out, err


def test_add_creates_habit_and_confirms(data_file, capsys):
    code, out, err = add("Leer", capsys)
    assert (code, out, err) == (0, 'Hábito "Leer" creado.\n', "")
    assert load(data_file) == [Habit("Leer", set())]


def test_add_strips_outer_spaces_and_keeps_original_casing(data_file, capsys):
    code, out, _ = add("  LeEr MuCho \t", capsys)
    assert code == 0
    assert out == 'Hábito "LeEr MuCho" creado.\n'
    assert [h.name for h in load(data_file)] == ["LeEr MuCho"]


def test_add_appends_habits_in_creation_order(data_file, capsys):
    for name in ("Zeta", "Alfa", "Mu"):
        assert add(name, capsys)[0] == 0
    assert [h.name for h in load(data_file)] == ["Zeta", "Alfa", "Mu"]


def test_add_keeps_existing_habits_and_their_dates(data_file, capsys):
    save(data_file, [Habit("Leer", {date(2026, 10, 13), date(2999, 1, 1)})])
    assert add("Correr", capsys)[0] == 0
    assert load(data_file) == [
        Habit("Leer", {date(2026, 10, 13), date(2999, 1, 1)}),
        Habit("Correr", set()),
    ]


def test_add_accepts_accents_emoji_and_spaces_inside(data_file, capsys):
    assert add("Estudiar inglés 📚", capsys)[0] == 0
    assert "Estudiar inglés 📚" in data_file.read_text(encoding="utf-8")


def test_add_accepts_a_name_starting_with_dash_after_double_dash(data_file, capsys):
    assert main(["add", "--", "-x"], today=TODAY) == 0
    assert [h.name for h in load(data_file)] == ["-x"]


def test_add_accepts_name_of_exactly_120_characters(data_file, capsys):
    assert add("a" * 120, capsys)[0] == 0
    assert load(data_file)[0].name == "a" * 120


@pytest.mark.parametrize("name", ["", "   ", "\t", "\u00a0 "])
def test_add_empty_name_fails_and_registers_nothing(name, data_file, capsys):
    code, out, err = add(name, capsys)
    assert code == 1
    assert out == ""
    assert err.startswith("Error: el nombre del hábito no puede estar vacío.")
    assert 'habits add "Leer"' in err  # dice qué hacer
    assert not data_file.exists()


def test_add_name_over_120_characters_fails_mentioning_the_limit(data_file, capsys):
    code, out, err = add("a" * 121, capsys)
    assert code == 1
    assert out == ""
    assert err.startswith("Error: el nombre supera el límite de 120 caracteres.")
    assert "Acórtalo" in err  # dice qué hacer
    assert not data_file.exists()


def test_add_length_limit_ignores_outer_spaces(data_file, capsys):
    assert add("  " + "a" * 120 + "  ", capsys)[0] == 0


@pytest.mark.parametrize("duplicate", ["Leer", "leer", "LEER", "  Leer  ", "\tlEEr\u00a0"])
def test_add_duplicate_name_fails_and_leaves_data_untouched(duplicate, data_file, capsys):
    save(data_file, [Habit("Leer", {date(2026, 10, 13)})])
    before = data_file.read_bytes()

    code, out, err = add(duplicate, capsys)

    assert code == 1
    assert out == ""
    assert err == 'Error: ya existe un hábito llamado "Leer". Elige otro nombre.\n'
    assert data_file.read_bytes() == before


def test_add_names_differing_in_internal_spaces_are_different_habits(data_file, capsys):
    assert add("Leer mucho", capsys)[0] == 0
    assert add("Leer  mucho", capsys)[0] == 0
    assert len(load(data_file)) == 2


def test_failed_add_does_not_create_file_over_existing_directory_structure(data_file, capsys):
    add("", capsys)
    add("a" * 121, capsys)
    assert not data_file.parent.exists()


# --- Comando done: RF-2.1 a RF-2.5 -----------------------------------------


def done(name: str, capsys):
    code = main(["done", name], today=TODAY)
    out, err = capsys.readouterr()
    return code, out, err


def test_done_marks_today_and_confirms(data_file, capsys):
    save(data_file, [Habit("Leer")])
    code, out, err = done("Leer", capsys)
    assert (code, out, err) == (0, '¡Hecho! "Leer" marcado para hoy.\n', "")
    assert load(data_file) == [Habit("Leer", {TODAY})]


def test_done_uses_the_date_given_to_main(data_file, capsys):
    save(data_file, [Habit("Leer")])
    other_day = date(2030, 1, 31)
    assert main(["done", "Leer"], today=other_day) == 0
    assert load(data_file)[0].dates == {other_day}


@pytest.mark.parametrize("typed", ["leer", "LEER", "  Leer  ", "\tlEEr\u00a0"])
def test_done_finds_habit_ignoring_case_and_outer_spaces(typed, data_file, capsys):
    save(data_file, [Habit("Leer")])
    code, out, _ = done(typed, capsys)
    assert code == 0
    assert out == '¡Hecho! "Leer" marcado para hoy.\n'  # muestra el nombre guardado
    assert load(data_file)[0].dates == {TODAY}


def test_done_marks_only_the_requested_habit(data_file, capsys):
    save(data_file, [Habit("Leer"), Habit("Correr", {date(2026, 10, 13)})])
    assert done("Leer", capsys)[0] == 0
    assert load(data_file) == [
        Habit("Leer", {TODAY}),
        Habit("Correr", {date(2026, 10, 13)}),
    ]


def test_done_already_marked_today_warns_without_duplicating(data_file, capsys):
    save(data_file, [Habit("Leer", {date(2026, 10, 13), TODAY})])
    before = data_file.read_bytes()

    code, out, err = done("Leer", capsys)

    assert code == 0
    assert out == 'Aviso: "Leer" ya estaba marcado hoy.\n'
    assert err == ""
    assert data_file.read_bytes() == before


def test_done_twice_in_a_day_keeps_a_single_record(data_file, capsys):
    save(data_file, [Habit("Leer")])
    assert done("Leer", capsys)[0] == 0
    code, out, _ = done("leer", capsys)
    assert code == 0
    assert out.startswith("Aviso:")
    assert load(data_file)[0].dates == {TODAY}


def test_done_with_future_dates_registers_today_and_keeps_them(data_file, capsys):
    future = {date(2026, 10, 15), date(2999, 1, 1)}
    save(data_file, [Habit("Leer", set(future))])
    assert done("Leer", capsys)[0] == 0
    assert load(data_file)[0].dates == future | {TODAY}


def test_done_unknown_habit_fails_and_creates_nothing(data_file, capsys):
    save(data_file, [Habit("Leer")])
    before = data_file.read_bytes()

    code, out, err = done("  Correr ", capsys)

    assert code == 1
    assert out == ""
    assert err == (
        'Error: no existe ningún hábito llamado "Correr". '
        'Créalo con: habits add "Correr"\n'
    )
    assert data_file.read_bytes() == before


def test_done_unknown_habit_without_data_file_creates_no_file(data_file, capsys):
    code, out, err = done("Leer", capsys)
    assert code == 1
    assert err.startswith('Error: no existe ningún hábito llamado "Leer".')
    assert not data_file.exists()
    assert not data_file.parent.exists()


@pytest.mark.parametrize("name", ["", "   ", "\t", "\u00a0 "])
def test_done_empty_name_is_habit_not_found(name, data_file, capsys):
    save(data_file, [Habit("Leer")])
    before = data_file.read_bytes()

    code, out, err = done(name, capsys)

    assert code == 1
    assert out == ""
    assert err.startswith("Error: no existe ningún hábito")
    assert 'habits done "Leer"' in err  # dice qué hacer
    assert data_file.read_bytes() == before
    assert [h.name for h in load(data_file)] == ["Leer"]  # no se crea ningún hábito


def test_done_does_not_match_names_with_different_internal_spaces(data_file, capsys):
    save(data_file, [Habit("Leer  mucho")])
    code, _, err = done("Leer mucho", capsys)
    assert code == 1
    assert "no existe" in err


# --- Comando list: RF-3.1 a RF-3.5 -----------------------------------------

EMPTY_LIST_MESSAGE = 'Aún no tienes hábitos. Crea el primero con: habits add "<nombre>"\n'


def list_(capsys, today=TODAY):
    code = main(["list"], today=today)
    out, err = capsys.readouterr()
    return code, out, err


def test_list_shows_name_streak_and_done_today(data_file, capsys):
    save(data_file, [Habit("Leer", {date(2026, 10, 12), date(2026, 10, 13), TODAY})])
    code, out, err = list_(capsys)
    assert (code, out, err) == (0, "Leer · racha: 3 días · hecho hoy\n", "")


def test_list_shows_pending_when_not_done_today(data_file, capsys):
    save(data_file, [Habit("Leer", {date(2026, 10, 12), date(2026, 10, 13)})])
    assert list_(capsys)[1] == "Leer · racha: 2 días · pendiente\n"


@pytest.mark.parametrize(
    ("dates", "expected"),
    [
        (set(), "Leer · racha: 0 días · pendiente"),
        ({TODAY}, "Leer · racha: 1 día · hecho hoy"),
        ({date(2026, 10, 13)}, "Leer · racha: 1 día · pendiente"),
        ({date(2026, 10, 13), TODAY}, "Leer · racha: 2 días · hecho hoy"),
        ({date(2026, 10, 12)}, "Leer · racha: 0 días · pendiente"),  # ni hoy ni ayer
        ({date(2026, 10, 11), TODAY}, "Leer · racha: 1 día · hecho hoy"),  # hueco
    ],
)
def test_list_singular_plural_and_streak_rules(dates, expected, data_file, capsys):
    save(data_file, [Habit("Leer", dates)])
    assert list_(capsys)[1] == expected + "\n"


def test_list_with_only_future_dates_shows_zero_and_pending(data_file, capsys):
    save(data_file, [Habit("Leer", {date(2026, 10, 15), date(2999, 1, 1)})])
    assert list_(capsys)[1] == "Leer · racha: 0 días · pendiente\n"


def test_list_ignores_future_dates_without_deleting_them(data_file, capsys):
    dates = {date(2026, 10, 13), TODAY, date(2026, 10, 15)}
    save(data_file, [Habit("Leer", set(dates))])
    assert list_(capsys)[1] == "Leer · racha: 2 días · hecho hoy\n"
    assert load(data_file)[0].dates == dates


def test_list_shows_one_line_per_habit_in_creation_order(data_file, capsys):
    save(
        data_file,
        [
            Habit("Zeta", {TODAY}),
            Habit("Alfa"),
            Habit("Mu", {date(2026, 10, 13)}),
        ],
    )
    code, out, _ = list_(capsys)
    assert code == 0
    assert out.splitlines() == [
        "Zeta · racha: 1 día · hecho hoy",
        "Alfa · racha: 0 días · pendiente",
        "Mu · racha: 1 día · pendiente",
    ]


def test_list_does_not_truncate_long_names_or_alter_them(data_file, capsys):
    long_name = "Estudiar inglés 📚 " + "x" * 100
    save(data_file, [Habit(long_name, {TODAY})])
    assert list_(capsys)[1] == f"{long_name} · racha: 1 día · hecho hoy\n"


def test_list_uses_the_date_given_to_main(data_file, capsys):
    save(data_file, [Habit("Leer", {date(2030, 1, 30), date(2030, 1, 31)})])
    assert list_(capsys, today=date(2030, 1, 31))[1] == "Leer · racha: 2 días · hecho hoy\n"
    assert list_(capsys, today=date(2030, 2, 1))[1] == "Leer · racha: 2 días · pendiente\n"
    assert list_(capsys, today=date(2030, 2, 2))[1] == "Leer · racha: 0 días · pendiente\n"


def test_list_without_habits_shows_friendly_message_and_creates_nothing(data_file, capsys):
    code, out, err = list_(capsys)
    assert (code, out, err) == (0, EMPTY_LIST_MESSAGE, "")
    assert not data_file.exists()
    assert not data_file.parent.exists()


def test_list_with_empty_habit_list_in_file_shows_friendly_message(data_file, capsys):
    save(data_file, [])
    code, out, _ = list_(capsys)
    assert (code, out) == (0, EMPTY_LIST_MESSAGE)


def test_list_never_modifies_the_data_file(data_file, capsys):
    save(data_file, [Habit("Leer", {TODAY, date(2999, 1, 1)}), Habit("Correr")])
    before = data_file.read_bytes()
    list_(capsys)
    assert data_file.read_bytes() == before


def test_list_reflects_add_and_done_end_to_end(data_file, capsys):
    assert main(["add", "Leer"], today=TODAY) == 0
    assert main(["add", "Correr"], today=TODAY) == 0
    assert main(["done", "leer"], today=TODAY) == 0
    capsys.readouterr()
    assert list_(capsys)[1].splitlines() == [
        "Leer · racha: 1 día · hecho hoy",
        "Correr · racha: 0 días · pendiente",
    ]


# --- Errores de datos y de escritura: RF-4.3, RF-4.5 -----------------------

CORRUPT_CONTENTS = [
    "",
    "{ roto",
    "[]",
    '{"habits": {}}',
    '{"habits": [{"name": "Leer"}]}',
    '{"habits": [{"name": "  Leer", "dates": []}]}',
    '{"habits": [{"name": "Leer", "dates": ["20261014"]}]}',
    '{"habits": [{"name": "Leer", "dates": []}, {"name": "leer", "dates": []}]}',
]

COMMANDS = [["add", "Nuevo"], ["done", "Leer"], ["list"]]


@pytest.mark.parametrize("argv", COMMANDS, ids=["add", "done", "list"])
@pytest.mark.parametrize("content", CORRUPT_CONTENTS)
def test_corrupt_data_fails_without_touching_the_file(argv, content, data_file, capsys):
    data_file.parent.mkdir(parents=True)
    data_file.write_text(content, encoding="utf-8")
    before = data_file.read_bytes()

    code = main(argv, today=TODAY)
    out, err = capsys.readouterr()

    assert code == 1
    assert out == ""
    assert err == (
        f"Error: no se pueden leer los datos de {data_file}. "
        "Corrige el archivo a mano o muévelo para empezar de cero.\n"
    )
    assert data_file.read_bytes() == before
    assert [p.name for p in data_file.parent.iterdir()] == ["habits.json"]


@pytest.mark.parametrize("argv", COMMANDS, ids=["add", "done", "list"])
def test_unreadable_data_fails_with_the_same_message(argv, data_file, capsys):
    data_file.mkdir(parents=True)  # un directorio no se puede leer como archivo

    code = main(argv, today=TODAY)
    out, err = capsys.readouterr()

    assert code == 1
    assert out == ""
    assert err.startswith(f"Error: no se pueden leer los datos de {data_file}.")


def test_done_unknown_habit_with_corrupt_data_reports_corrupt_data(data_file, capsys):
    data_file.parent.mkdir(parents=True)
    data_file.write_text("{ roto", encoding="utf-8")
    code = main(["done", "NoExiste"], today=TODAY)
    _, err = capsys.readouterr()
    assert code == 1
    assert "no se pueden leer los datos" in err


def break_replace(monkeypatch):
    def broken_replace(*args, **kwargs):
        raise OSError("disco lleno")

    monkeypatch.setattr("habits_cli.storage.os.replace", broken_replace)


WRITE_ERROR = (
    "Error: no se pudo guardar en {path}. Revisa los permisos y el espacio en disco; "
    "tus datos anteriores no se han modificado.\n"
)


@pytest.mark.parametrize("argv", [["add", "Nuevo"], ["done", "Leer"]], ids=["add", "done"])
def test_write_failure_reports_error_and_keeps_original(argv, data_file, capsys, monkeypatch):
    save(data_file, [Habit("Leer")])
    before = data_file.read_bytes()
    break_replace(monkeypatch)

    code = main(argv, today=TODAY)
    out, err = capsys.readouterr()

    assert code == 1
    assert out == ""  # no se confirma nada que no se guardó
    assert err == WRITE_ERROR.format(path=data_file)
    assert data_file.read_bytes() == before
    assert [p.name for p in data_file.parent.iterdir()] == ["habits.json"]


@pytest.mark.parametrize("argv", [["add", "Nuevo"]], ids=["add"])
def test_write_failure_on_first_use_creates_no_data_file(argv, data_file, capsys, monkeypatch):
    break_replace(monkeypatch)

    code = main(argv, today=TODAY)
    out, err = capsys.readouterr()

    assert code == 1
    assert out == ""
    assert err == WRITE_ERROR.format(path=data_file)
    assert not data_file.exists()
    assert list(data_file.parent.iterdir()) == []


def test_commands_that_do_not_write_ignore_write_problems(data_file, capsys, monkeypatch):
    save(data_file, [Habit("Leer", {TODAY})])
    break_replace(monkeypatch)

    assert main(["list"], today=TODAY) == 0
    assert main(["done", "Leer"], today=TODAY) == 0  # ya marcado hoy: no escribe
    assert main(["add", "leer"], today=TODAY) == 1  # duplicado: error de negocio
    _, err = capsys.readouterr()
    assert "ya existe un hábito" in err
    assert "no se pudo guardar" not in err


def test_data_error_messages_say_what_to_do(data_file, capsys, monkeypatch):
    data_file.parent.mkdir(parents=True)
    data_file.write_text("{ roto", encoding="utf-8")
    main(["list"], today=TODAY)
    assert "Corrige el archivo a mano o muévelo" in capsys.readouterr().err

    data_file.unlink()
    break_replace(monkeypatch)
    main(["add", "Leer"], today=TODAY)
    assert "Revisa los permisos y el espacio en disco" in capsys.readouterr().err
