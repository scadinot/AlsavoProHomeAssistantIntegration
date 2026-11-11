"""Load the protocol layer without Home Assistant.

``custom_components/alsavopro/__init__.py`` imports Home Assistant, so the
package is registered here as a bare namespace pointing at the component
folder. Its submodules (``const``, ``udpclient``, ``AlsavoPyCtrl``) only use
the standard library and can then be imported directly.
"""
import importlib
import sys
import types
from pathlib import Path

import pytest

COMPONENT_DIR = Path(__file__).resolve().parent.parent / "custom_components" / "alsavopro"

_pkg = types.ModuleType("alsavopro")
_pkg.__path__ = [str(COMPONENT_DIR)]
sys.modules.setdefault("alsavopro", _pkg)


@pytest.fixture
def ctrl():
    return importlib.import_module("alsavopro.AlsavoPyCtrl")


@pytest.fixture
def const():
    return importlib.import_module("alsavopro.const")


@pytest.fixture
def udpclient():
    return importlib.import_module("alsavopro.udpclient")
