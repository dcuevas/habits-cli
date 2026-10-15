"""Interfaz de línea de comandos: argumentos, textos en español y códigos de salida."""

import argparse
import sys
from datetime import date

from habits_cli.core import (
    MAX_NAME_LENGTH,
    CorruptData,
    DuplicateHabit,
    HabitNotFound,
    InvalidName,
    MarkResult,
    StorageWriteError,
    add_habit,
    find_habit,
    list_habits,
    mark_done,
)
from habits_cli.storage import default_path, load, save

GENERAL_SYNTAX = "habits <comando> [argumentos]"
SYNTAX = {
    None: GENERAL_SYNTAX,
    "add": 'habits add "<nombre>"',
    "done": 'habits done "<nombre>"',
    "list": "habits list",
}

HELP = {
    None: f"""Uso: {SYNTAX[None]}

Registra hábitos de estudio y consulta tu racha de días consecutivos.

Comandos:
  add "<nombre>"    Crea un hábito nuevo.
  done "<nombre>"   Marca un hábito como hecho hoy.
  list              Muestra tus hábitos con su racha.

Opciones:
  -h, --help        Muestra esta ayuda.

Usa "habits <comando> --help" para ver la ayuda de un comando.""",
    "add": f"""Uso: {SYNTAX["add"]}

Crea un hábito nuevo, sin días completados.
El nombre puede tener hasta 120 caracteres; escríbelo entre comillas si lleva espacios.

Opciones:
  -h, --help   Muestra esta ayuda.""",
    "done": f"""Uso: {SYNTAX["done"]}

Marca un hábito como hecho hoy. No distingue mayúsculas de minúsculas.

Opciones:
  -h, --help   Muestra esta ayuda.""",
    "list": f"""Uso: {SYNTAX["list"]}

Muestra tus hábitos en orden de creación, con su racha actual en días
y si ya los hiciste hoy.

Opciones:
  -h, --help   Muestra esta ayuda.""",
}

USAGE_ERROR = "Uso incorrecto. Prueba: habits --help"

MSG_CREATED = 'Hábito "{name}" creado.'
MSG_EMPTY_NAME = (
    'Error: el nombre del hábito no puede estar vacío. '
    'Escribe un nombre, por ejemplo: habits add "Leer"'
)
MSG_NAME_TOO_LONG = (
    f"Error: el nombre supera el límite de {MAX_NAME_LENGTH} caracteres. "
    "Acórtalo e inténtalo de nuevo."
)
MSG_DONE = '¡Hecho! "{name}" marcado para hoy.'
MSG_ALREADY_DONE = 'Aviso: "{name}" ya estaba marcado hoy.'
MSG_NOT_FOUND = 'Error: no existe ningún hábito llamado "{name}". Créalo con: habits add "{name}"'
MSG_NOT_FOUND_EMPTY = (
    "Error: no existe ningún hábito sin nombre. "
    'Escribe el nombre del hábito, por ejemplo: habits done "Leer"'
)
MSG_EMPTY_LIST = 'Aún no tienes hábitos. Crea el primero con: habits add "<nombre>"'
MSG_LIST_LINE = "{name} · racha: {streak} · {state}"
MSG_DONE_TODAY = "hecho hoy"
MSG_PENDING = "pendiente"
MSG_CORRUPT = (
    "Error: no se pueden leer los datos de {path}. "
    "Corrige el archivo a mano o muévelo para empezar de cero."
)
MSG_WRITE_FAILED = (
    "Error: no se pudo guardar en {path}. "
    "Revisa los permisos y el espacio en disco; tus datos anteriores no se han modificado."
)
MSG_DUPLICATE = 'Error: ya existe un hábito llamado "{name}". Elige otro nombre.'


class _UsageError(Exception):
    """Uso incorrecto de la línea de comandos."""


class _HelpRequested(Exception):
    """El usuario pidió la ayuda con -h o --help."""


class _HelpAction(argparse.Action):
    def __init__(self, option_strings, dest=argparse.SUPPRESS, default=argparse.SUPPRESS, help=None):
        super().__init__(option_strings, dest=dest, default=default, nargs=0, help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        raise _HelpRequested


class _Parser(argparse.ArgumentParser):
    """argparse sin textos propios: ni ayuda ni errores salen en inglés."""

    def error(self, message):
        raise _UsageError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="habits", add_help=False, allow_abbrev=False)
    parser.add_argument("-h", "--help", action=_HelpAction)
    commands = parser.add_subparsers(dest="command", required=True)

    for name in ("add", "done"):
        command = commands.add_parser(name, add_help=False, allow_abbrev=False)
        command.add_argument("-h", "--help", action=_HelpAction)
        command.add_argument("name")

    list_command = commands.add_parser("list", add_help=False, allow_abbrev=False)
    list_command.add_argument("-h", "--help", action=_HelpAction)
    return parser


def _command_in(argv: list[str]) -> str | None:
    """Comando que el usuario intentó usar, para mostrar su ayuda o sintaxis."""
    return argv[0] if argv and argv[0] in ("add", "done", "list") else None


def main(argv: list[str] | None = None, today: date | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        args = build_parser().parse_args(argv)
    except _HelpRequested:
        print(HELP[_command_in(argv)])
        return 0
    except _UsageError:
        print(USAGE_ERROR, file=sys.stderr)
        print(f"Uso: {SYNTAX[_command_in(argv)]}", file=sys.stderr)
        return 2
    if today is None:
        today = date.today()
    try:
        if args.command == "add":
            return _add(args.name)
        if args.command == "done":
            return _done(args.name, today)
        return _list(today)
    except CorruptData as error:
        return _error(MSG_CORRUPT.format(path=error.path))
    except StorageWriteError as error:
        return _error(MSG_WRITE_FAILED.format(path=error.path))


def _error(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def _add(raw_name: str) -> int:
    path = default_path()
    habits = load(path)
    try:
        habit = add_habit(habits, raw_name)
    except InvalidName as error:
        return _error(MSG_EMPTY_NAME if error.reason == "empty" else MSG_NAME_TOO_LONG)
    except DuplicateHabit as error:
        return _error(MSG_DUPLICATE.format(name=error.name))
    save(path, habits)
    print(MSG_CREATED.format(name=habit.name))
    return 0


def _done(raw_name: str, today: date) -> int:
    path = default_path()
    habits = load(path)
    try:
        result = mark_done(habits, raw_name, today)
    except HabitNotFound as error:
        return _error(MSG_NOT_FOUND.format(name=error.name) if error.name else MSG_NOT_FOUND_EMPTY)
    name = find_habit(habits, raw_name).name  # nombre tal como está guardado
    if result is MarkResult.ALREADY_DONE:
        print(MSG_ALREADY_DONE.format(name=name))
        return 0
    save(path, habits)
    print(MSG_DONE.format(name=name))
    return 0


def _days(count: int) -> str:
    return f"{count} día" if count == 1 else f"{count} días"


def _list(today: date) -> int:
    statuses = list_habits(load(default_path()), today)
    if not statuses:
        print(MSG_EMPTY_LIST)
        return 0
    for status in statuses:
        print(
            MSG_LIST_LINE.format(
                name=status.name,
                streak=_days(status.streak),
                state=MSG_DONE_TODAY if status.done_today else MSG_PENDING,
            )
        )
    return 0


def run() -> None:
    """Punto de entrada del programa `habits`."""
    sys.exit(main(sys.argv[1:]))
