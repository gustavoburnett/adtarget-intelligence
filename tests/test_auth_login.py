"""OIDC authorization and real entry-point isolation, without real credentials."""
from pathlib import Path
import time

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from src.auth import gate
from tests.oidc_helpers import CONFIG, Identity, identity
from src.data import loader, metas_loader, representacoes
from pages_content import (performance_comercial, metas_resultados, analitico_comercial,
                           analitico_veiculos, carteira_vendas)

APP = Path(__file__).resolve().parents[1] / "app.py"
PAGES = dict(zip(("Performance Comercial", "Metas e Resultados", "Analítico Comercial",
                  "Analítico Veículos", "Carteira de Vendas"),
                 (performance_comercial, metas_resultados, analitico_comercial,
                  analitico_veiculos, carteira_vendas)))
REAL_CONFIG = gate._config


def gate_app():
    import streamlit as st
    from src.auth.gate import exigir_autenticacao
    exigir_autenticacao()
    st.text("PROTECTED")


@pytest.mark.parametrize("changes", [
    {"hd": None}, {"hd": "gmail.com"}, {"hd": "adtarget.com.br.attacker.com"},
    {"hd": "other.com", "email": "employee@adtarget.com.br"},
    {"email_verified": False}, {"email_verified": "true"}, {"sub": ""},
    {"iss": "https://evil.invalid"}, {"aud": "other-client"},
    {"exp": 0}, {"exp": True}, {"exp": float("nan")}, {"exp": "999999999999"},
])
def test_reject_invalid_identity(changes):
    assert not gate.identidade_autorizada(identity(**changes), "OFFLINE_CLIENT")


def test_authorize_workspace_using_hd_not_email():
    assert gate.identidade_autorizada(identity(email="alias@example.com"), "OFFLINE_CLIENT")
    assert not gate.identidade_autorizada(identity(hd=None, email="employee@adtarget.com.br"), "OFFLINE_CLIENT")


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("user", [Identity(), identity(hd="gmail.com"), identity(exp=0)])
def test_all_direct_pages_block_before_any_loader(monkeypatch, page, user):
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("Data accessed before authorization")
    monkeypatch.setattr(st, "user", user)
    monkeypatch.setattr(st, "secrets", {"spreadsheet_id": "OFFLINE", "gcp_service_account": {}})
    for module, name in ((loader, "load_all_sheets"), (metas_loader, "load_metas"),
                         (representacoes, "load_representacoes")):
        monkeypatch.setattr(module, name, forbidden)
    app = AppTest.from_file(str(APP))
    app.session_state["nav_pagina"] = page
    app.session_state["autenticado"] = True  # Legacy flag cannot bypass OIDC.
    app.query_params["carteira"] = "year=2026"
    app.run(timeout=20)
    assert not app.exception
    assert not calls and not app.radio
    app.run(timeout=20)
    assert not calls and not app.exception


@pytest.mark.parametrize("page", PAGES)
def test_authorized_employee_has_equal_access(monkeypatch, page):
    st.cache_data.clear()
    monkeypatch.setattr(st, "secrets", {"spreadsheet_id": "OFFLINE", "gcp_service_account": {}})
    monkeypatch.setattr(loader, "load_all_sheets", lambda *_: pd.DataFrame())
    monkeypatch.setattr(metas_loader, "load_metas", lambda *_: pd.DataFrame())
    renders = []
    for name, module in PAGES.items():
        monkeypatch.setattr(module, "render", lambda *_, _name=name, **__: renders.append(_name))
    app = AppTest.from_file(str(APP))
    app.session_state["nav_pagina"] = page
    app.run(timeout=20)
    assert not app.exception
    assert renders == [page]
    assert len(app.radio(key="nav_pagina").options) == 5
    assert all(any(option.endswith(name) for option in app.radio(key="nav_pagina").options) for name in PAGES)
    assert app.button(key="logout_google").label == "Sair"
    st.cache_data.clear()


def test_reload_revalidates_native_identity_and_expiry(monkeypatch):
    user = identity()
    monkeypatch.setattr(st, "user", user)
    for _ in range(2):  # New Streamlit sessions model browser reload.
        app = AppTest.from_function(gate_app).run()
        assert app.text[0].value == "PROTECTED"
    user["exp"] = time.time() - 1
    app.run()
    assert not app.text and not app.exception
    assert app.error


def test_logout_clears_state_and_calls_native_logout(monkeypatch):
    user = identity()
    monkeypatch.setattr(st, "user", user)
    calls = []
    def logout():
        calls.append(True)
        user.clear()
    monkeypatch.setattr(st, "logout", logout)
    def screen():
        import streamlit as st
        from src.auth.gate import exigir_autenticacao, encerrar_sessao
        exigir_autenticacao()
        st.session_state["private_filter"] = "private"
        st.button("Sair", on_click=encerrar_sessao)
    app = AppTest.from_function(screen).run()
    app.button[0].click().run()
    assert calls == [True]
    assert "private_filter" not in app.session_state
    app.run()
    assert app.button[0].label == "Entrar com Google"


def test_anonymous_login_uses_named_google_provider(monkeypatch):
    monkeypatch.setattr(st, "user", Identity())
    calls = []
    monkeypatch.setattr(st, "login", lambda provider: calls.append(provider))
    app = AppTest.from_function(gate_app).run()
    app.button[0].click().run()
    assert calls == ["google"] and not app.text
    assert not app.text_input


@pytest.mark.parametrize("secrets", [{}, {"auth": {}}, {"auth": {**CONFIG, "google": {**CONFIG["google"], "server_metadata_url": "https://evil.invalid"}}}])
def test_missing_or_wrong_provider_config_fails_closed(monkeypatch, secrets):
    monkeypatch.setattr(gate, "_config", REAL_CONFIG)
    monkeypatch.setattr(st, "secrets", secrets)
    app = AppTest.from_function(gate_app).run()
    assert not app.exception and not app.text and not app.button
    assert "Login Google não configurado" in app.error[0].value
