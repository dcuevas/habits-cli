import importlib

import pytest


@pytest.mark.parametrize("module", ["core", "storage", "cli", "__main__"])
def test_package_modules_are_importable(module):
    importlib.import_module(f"habits_cli.{module}")
