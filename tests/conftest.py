"""Configuração do pytest: garante o pacote src importável a partir da raiz."""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


import pytest
import streamlit as st
from tests.oidc_helpers import CONFIG, identity

@pytest.fixture(autouse=True)
def _native_oidc_regression_config(monkeypatch):
    from src.auth import gate
    monkeypatch.setattr(gate, "_config", lambda: CONFIG["google"])
    monkeypatch.setattr(st, "user", identity())
