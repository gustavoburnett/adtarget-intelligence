"""Synthetic acceptance app must preserve native gate and never connect Sheets."""
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import app_homologacao
from tests.oidc_helpers import CONFIG, identity

ENTRY = Path(__file__).resolve().parents[1] / "app_homologacao.py"


@pytest.mark.parametrize("page", [
    "Performance Comercial", "Metas e Resultados", "Analítico Comercial",
    "Analítico Veículos", "Carteira de Vendas",
])
def test_synthetic_pages_without_data_credentials(monkeypatch, page):
    st.cache_data.clear()
    monkeypatch.setattr(st, "secrets", {
        "auth": CONFIG, "spreadsheet_id": "SYNTHETIC_ONLY", "gcp_service_account": {},
    })
    app = AppTest.from_file(str(ENTRY))
    app.session_state["nav_pagina"] = page
    app.run(timeout=30)
    assert not app.exception
    assert any(button.label == "Sair" for button in app.button)
    assert app.radio[0].value == page
    st.cache_data.clear()


def test_synthetic_entry_keeps_anonymous_gate(monkeypatch):
    monkeypatch.setattr(st, "secrets", {"auth": CONFIG})
    monkeypatch.setattr(st, "user", identity(is_logged_in=False))
    app = AppTest.from_file(str(ENTRY)).run(timeout=20)
    assert not app.exception
    assert [button.label for button in app.button] == ["Entrar com Google"]
    assert not app.radio


def test_real_sheet_client_always_blocked():
    with pytest.raises(RuntimeError, match="não permite"):
        app_homologacao.bloquear_cliente_real({})
