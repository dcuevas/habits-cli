"""Fecha de hoy (RNF-6, RNF-7) y ejecución real como programa (RF-4.1)."""

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from habits_cli import cli
from habits_cli.cli import main, run
from habits_cli.core import Habit
from habits_cli.storage import load, save

FAKE_TODAY = date(2026, 10, 14)


@pytest.fixture
def data_file(tmp_path, monkeypatch):
    path = tmp_path / "datos" / "habits.json"
    monkeypatch.setenv("HABITS_FILE", str(path))
    return path


@pytest.fixture
def fake_clock(monkeypatch):
    """Sustituye el reloj de la CLI y cuenta cuántas veces se lee la fecha."""

    class FakeDate(date):
        reads = 0

        @classmethod
        def today(cls):
            FakeDate.reads += 1
            return FAKE_TODAY

    monkeypatch.setattr(cli, "date", FakeDate)
    return FakeDate


# --- Fecha de hoy: RNF-6, RNF-7 --------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [["add", "Nuevo"], ["done", "Leer"], ["list"]],
    ids=["add", "done", "list"],
)
def test_main_without_today_reads_the_date_exactly_once(argv, data_file, fake_clock):
    save(data_file, [Habit("Leer")])
    assert main(argv) == 0
    assert fake_clock.reads == 1


def test_main_without_today_uses_the_date_it_reads_for_done_and_list(
    data_file, fake_clock, capsys
):
    save(data_file, [Habit("Leer", {date(2026, 10, 13)})])
    assert main(["list"]) == 0
    assert capsys.readouterr().out == "Leer · racha: 1 día · pendiente\n"

    assert main(["done", "Leer"]) == 0
    assert load(data_file)[0].dates == {date(2026, 10, 13), FAKE_TODAY}

    assert main(["list"]) == 0
    assert capsys.readouterr().out.endswith("Leer · racha: 2 días · hecho hoy\n")


def test_main_with_today_does_not_read_the_clock(data_file, fake_clock):
    save(data_file, [Habit("Leer")])
    assert main(["list"], today=date(2030, 1, 1)) == 0
    assert fake_clock.reads == 0


def test_help_and_usage_errors_do_not_read_the_clock(fake_clock, capsys):
    assert main(["--help"]) == 0
    assert main(["add"]) == 2
    assert fake_clock.reads == 0


# --- run(): argumentos reales y código de salida ---------------------------


def test_run_passes_command_line_arguments_and_exits_with_the_code(
    data_file, monkeypatch, capsys
):
    monkeypatch.setattr(sys, "argv", ["habits", "--help"])
    with pytest.raises(SystemExit) as exit_info:
        run()
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.startswith("Uso: habits")


def test_run_exits_with_2_on_incorrect_usage(data_file, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["habits", "foo"])
    with pytest.raises(SystemExit) as exit_info:
        run()
    assert exit_info.value.code == 2


def test_main_without_argv_reads_sys_argv(data_file, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["habits", "add", "Desde argv"])
    assert main(today=FAKE_TODAY) == 0
    assert [h.name for h in load(data_file)] == ["Desde argv"]


# --- Ejecución como procesos reales: RF-4.1 --------------------------------


def run_process(command: list[str], data_file: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "HABITS_FILE": str(data_file), "PYTHONUTF8": "1"}
    return subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", env=env, timeout=30
    )


def module_command(*args: str) -> list[str]:
    return [sys.executable, "-m", "habits_cli", *args]


def script_command(*args: str) -> list[str]:
    script = Path(sys.executable).parent / ("habits.exe" if os.name == "nt" else "habits")
    if not script.exists():
        pytest.skip("el script `habits` no está instalado (pip install -e .[dev])")
    return [str(script), *args]


@pytest.mark.parametrize("command", [module_command, script_command], ids=["module", "script"])
def test_data_is_kept_between_separate_executions(command, data_file):
    created = run_process(command("add", "Leer"), data_file)
    assert (created.returncode, created.stdout) == (0, 'Hábito "Leer" creado.\n')

    marked = run_process(command("done", "leer"), data_file)
    assert (marked.returncode, marked.stdout) == (0, '¡Hecho! "Leer" marcado para hoy.\n')

    listed = run_process(command("list"), data_file)
    assert (listed.returncode, listed.stdout, listed.stderr) == (
        0,
        "Leer · racha: 1 día · hecho hoy\n",
        "",
    )

    again = run_process(command("done", "Leer"), data_file)
    assert (again.returncode, again.stdout) == (0, 'Aviso: "Leer" ya estaba marcado hoy.\n')

    stored = load(data_file)
    assert len(stored) == 1
    assert len(stored[0].dates) == 1


@pytest.mark.parametrize("command", [module_command, script_command], ids=["module", "script"])
def test_real_process_exit_codes(command, data_file):
    help_result = run_process(command("--help"), data_file)
    assert help_result.returncode == 0
    assert help_result.stdout.startswith("Uso: habits <comando> [argumentos]")

    usage = run_process(command(), data_file)
    assert usage.returncode == 2
    assert usage.stderr.splitlines()[0] == "Uso incorrecto. Prueba: habits --help"

    missing = run_process(command("done", "NoExiste"), data_file)
    assert missing.returncode == 1
    assert missing.stderr.startswith('Error: no existe ningún hábito llamado "NoExiste".')

    assert not data_file.exists()  # ninguno de estos casos escribe datos


def test_real_process_with_corrupt_data_exits_with_1(data_file):
    data_file.parent.mkdir(parents=True)
    data_file.write_text("{ roto", encoding="utf-8")
    result = run_process(module_command("list"), data_file)
    assert result.returncode == 1
    assert "no se pueden leer los datos" in result.stderr
    assert data_file.read_text(encoding="utf-8") == "{ roto"


def test_module_entry_point_does_not_run_when_imported():
    import importlib

    importlib.import_module("habits_cli.__main__")  # no debe salir ni leer sys.argv
