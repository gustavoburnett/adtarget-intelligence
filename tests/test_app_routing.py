"""Entrada completa: roteamento e diagnóstico, sem fonte ou secrets reais."""

from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from pages_content import (
    analitico_comercial, analitico_veiculos, auditoria_vendas, performance_comercial,
)
from src.data import cleaning, loader
from tests.test_radar import recorde

APP = Path(__file__).resolve().parents[1] / "app.py"
PAGES = {
    "Performance Comercial": performance_comercial,
    "Analítico Comercial": analitico_comercial,
    "Analítico Veículos": analitico_veiculos,
    "🔧 Auditoria (dev)": auditoria_vendas,
}


def run_app(monkeypatch, page):
    df = recorde()
    for column in cleaning.COLUNAS_TEXTO + [cleaning.COL_NOTA_FISCAL]:
        if column not in df:
            df[column] = "TESTE"
    df[cleaning.COL_VENCIMENTO] = pd.NaT
    monkeypatch.setattr(st, "secrets", {
        "spreadsheet_id": "TEST_ONLY", "gcp_service_account": {},
        "dev_auditoria": True,
    })
    monkeypatch.setattr(loader, "load_all_sheets", lambda *args: df)
    monkeypatch.setattr(cleaning, "limpar_dataframe", lambda value: value)
    app = AppTest.from_file(str(APP))
    app.session_state["autenticado"] = True
    app.session_state["nav_pagina"] = page
    return app.run(timeout=20), df


@pytest.mark.parametrize("page", PAGES)
def test_entry_routes_arguments_only_to_selected_page(monkeypatch, page):
    calls = []

    def performance(df, sincronizado_em=None):
        calls.append(("Performance Comercial", df, sincronizado_em))

    def simple(name):
        def render(df):
            calls.append((name, df, None))
        return render

    for name, module in PAGES.items():
        monkeypatch.setattr(module, "render", performance if name == "Performance Comercial" else simple(name))
    app, df = run_app(monkeypatch, page)
    assert not app.exception
    assert len(calls) == 1
    assert calls[0][0] == page
    pd.testing.assert_frame_equal(calls[0][1], df)
    assert (calls[0][2] is not None) == (page == "Performance Comercial")


def test_incompatible_performance_signature_is_not_hidden(monkeypatch):
    def render(df):
        raise AssertionError("Não deve entrar na função com assinatura incompatível")

    monkeypatch.setattr(performance_comercial, "render", render)
    app, _ = run_app(monkeypatch, "Performance Comercial")
    assert len(app.exception) == 1
    assert "unexpected keyword argument 'sincronizado_em'" in app.exception[0].message


def test_routing_uses_page_even_when_functions_share_identity(monkeypatch):
    calls = []

    def render(df, sincronizado_em=None):
        calls.append(sincronizado_em)

    monkeypatch.setattr(performance_comercial, "render", render)
    monkeypatch.setattr(analitico_comercial, "render", render)
    app, _ = run_app(monkeypatch, "Analítico Comercial")
    assert not app.exception
    assert calls == [None]


@pytest.mark.parametrize("page", PAGES)
def test_real_pages_through_entry(monkeypatch, page):
    app, _ = run_app(monkeypatch, page)
    assert not app.exception
