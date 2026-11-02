"""Deep links through the real entry point, with isolated offline sessions."""
from urllib.parse import urlencode, parse_qs
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest
from tests.test_metas_app_routing import APP, PAGINAS_PRINCIPAIS
from pages_content import carteira_vendas, performance_comercial, metas_resultados, analitico_comercial, analitico_veiculos
from src.data import cleaning, loader, metas_loader

@pytest.fixture
def session(monkeypatch):
    st.cache_data.clear()
    monkeypatch.setattr(st, "secrets", {"spreadsheet_id":"OFFLINE", "gcp_service_account":{}})
    monkeypatch.setattr(loader, "load_all_sheets", lambda *_: pd.DataFrame())
    monkeypatch.setattr(cleaning, "limpar_dataframe", lambda df: df)
    monkeypatch.setattr(metas_loader, "load_metas", lambda *_: pd.DataFrame())
    for module in [carteira_vendas, performance_comercial, metas_resultados, analitico_comercial, analitico_veiculos]:
        monkeypatch.setattr(module, "render", lambda *_, **kw: st.text(st.query_params.get("carteira", "")))
    def new(context=None, authenticated=True):
        app=AppTest.from_file(str(APP))
        app.session_state["autenticado"]=authenticated
        if context is not None:
            app.query_params["carteira"]=context
        app.run(timeout=20)
        assert not app.exception
        return app
    yield new
    st.cache_data.clear()

CONTEXT=urlencode({"grain":3,"year":2026,"month":4,"partner":"Água & O'Neill + 日本 / %", "detail":"", "client":"A&B", "status":"FATURADO"})

def test_new_session_direct_link_selects_wallet(session):
    app=session(CONTEXT)
    assert app.radio(key="nav_pagina").value == "Carteira de Vendas"
    assert app.text[0].value == CONTEXT

@pytest.mark.parametrize("context", [CONTEXT, "status=undefined", "", "grain=NaN&year=-1&month=99&partner=%3Cscript%3E", "https://evil.invalid/", "%", ["grain=1", CONTEXT]])
def test_present_legacy_or_invalid_context_routes_without_redirect_or_error(session, context):
    app=session(context)
    assert app.radio(key="nav_pagina").value == "Carteira de Vendas"
    # AppTest serializes its result with parse_qs (lists, blank values omitted).
    # Assert the in-app read separately: blank is present on entry and selects
    # Carteira, and repeated keys follow Streamlit's last-value semantics.
    expected = context[-1] if isinstance(context, list) else context
    assert app.text[0].value == expected
    assert app.query_params == parse_qs(urlencode({"carteira": context}, doseq=True))

@pytest.mark.parametrize("page", PAGINAS_PRINCIPAIS)
def test_navigation_and_return_do_not_get_overridden_on_rerun(session, page):
    app=session(CONTEXT)
    app.radio(key="nav_pagina").set_value(page).run(timeout=20)
    app.run(timeout=20)
    assert not app.exception
    assert app.radio(key="nav_pagina").value == page
    assert app.query_params["carteira"] == [CONTEXT]
    app.radio(key="nav_pagina").set_value("Carteira de Vendas").run(timeout=20)
    assert app.text[0].value == CONTEXT

def test_refresh_and_independent_sessions(session):
    for _ in range(3):
        app=session(CONTEXT)
        assert app.radio(key="nav_pagina").value == "Carteira de Vendas"
        app.button(key="masthead_refresh").click().run(timeout=20)
        assert not app.exception
        assert app.text[0].value == CONTEXT
        plain=session()
        assert plain.radio(key="nav_pagina").value == "Performance Comercial"

def test_encoded_context_roundtrip(session):
    outer=urlencode({"carteira":CONTEXT})
    decoded=parse_qs(outer)["carteira"][0]
    app=session(decoded)
    assert parse_qs(app.text[0].value)["partner"] == ["Água & O'Neill + 日本 / %"]

def test_gate_still_precedes_routing(session):
    app=session(CONTEXT, authenticated=False)
    assert not app.radio
    app.session_state["autenticado"]=True
    app.run(timeout=20)
    assert app.radio(key="nav_pagina").value == "Carteira de Vendas"

@pytest.mark.parametrize("context", ["", "%", "status=undefined", CONTEXT])
def test_raw_query_values_survive_rerun_and_refresh(session, context):
    app = session(context)
    for refresh in (False, True):
        if refresh:
            app.button(key="masthead_refresh").click()
        app.run(timeout=20)
        assert not app.exception
        assert app.radio(key="nav_pagina").value == "Carteira de Vendas"
        assert app.text[0].value == context


def test_other_query_keys_are_preserved(session):
    app = session(CONTEXT)
    app.query_params["tracking"] = ["A&B", "日本 + %"]
    app.run(timeout=20)
    assert app.query_params["tracking"] == ["A&B", "日本 + %"]
    assert app.text[0].value == CONTEXT
