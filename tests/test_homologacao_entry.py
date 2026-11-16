"""Synthetic acceptance app must preserve native gate and never connect Sheets."""
from pathlib import Path
from types import SimpleNamespace

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


def test_synthetic_mode_blocks_real_client():
    with pytest.raises(RuntimeError, match="não permite"):
        app_homologacao.bloquear_cliente_real({})


@pytest.mark.parametrize(("value", "expected"), [
    (None, False),
    ("synthetic", False),
    ("real", False),
    ("Real_Readonly", False),
    ("real_readonly", True),
])
def test_real_mode_requires_exact_explicit_value(value, expected):
    secrets = {} if value is None else {"homologation_data_mode": value}
    assert app_homologacao.modo_dados_realmente_configurado(secrets) is expected


def test_real_mode_loads_only_approved_year_tabs():
    planilha = SimpleNamespace(worksheets=lambda: [
        SimpleNamespace(title=nome) for nome in
        ("2023", "2024", "2025", "2026", "2027", "METAS", "REPRESENTACOES")
    ])
    assert [
        aba.title for aba in app_homologacao.descobrir_abas_reais_permitidas(planilha)
    ] == ["2024", "2025", "2026"]


def test_real_mode_keeps_real_loaders_and_readonly_scope(monkeypatch):
    from src.data import loader, metas_loader, representacoes

    monkeypatch.setattr(st, "secrets", {"homologation_data_mode": "real_readonly"})
    originais = {
        "vendas": loader.load_all_sheets,
        "cliente": loader.criar_cliente,
        "metas": metas_loader.load_metas,
        "representacoes": representacoes.load_representacoes,
        "descoberta": app_homologacao._descobrir_abas_de_ano_original,
    }
    observado = {}

    def interceptar_app(*args, **kwargs):
        observado["load_all_sheets"] = loader.load_all_sheets
        observado["criar_cliente"] = loader.criar_cliente
        observado["load_metas"] = metas_loader.load_metas
        observado["load_representacoes"] = representacoes.load_representacoes
        observado["scope"] = list(loader._SCOPES)
        planilha = SimpleNamespace(worksheets=lambda: [
            SimpleNamespace(title=nome) for nome in ("2024", "2026", "2027")
        ])
        observado["anos"] = [
            aba.title for aba in loader.descobrir_abas_de_ano(planilha)
        ]

    monkeypatch.setattr(app_homologacao.runpy, "run_path", interceptar_app)
    app_homologacao.executar_app()

    assert observado["load_all_sheets"] is originais["vendas"]
    assert observado["criar_cliente"] is originais["cliente"]
    assert observado["load_metas"] is originais["metas"]
    assert observado["load_representacoes"] is originais["representacoes"]
    assert observado["scope"] == [app_homologacao.ESCOPO_SHEETS_SOMENTE_LEITURA]
    assert observado["anos"] == ["2024", "2026"]
    assert loader.descobrir_abas_de_ano is originais["descoberta"]


def test_synthetic_dates_survive_real_cleaning():
    from src.data.cleaning import limpar_dataframe, COL_MES_VEICULACAO_DATA
    frame = limpar_dataframe(app_homologacao.vendas_sinteticas())
    assert len(frame) == 48
    assert frame[COL_MES_VEICULACAO_DATA].notna().all()
    assert frame["VALOR PI LIQUIDO"].sum() > 0


def test_carteira_links_remain_in_acceptance_environment():
    html = app_homologacao.documento_homologacao({"reference": "2026-11-02", "unassignedMonth": 0})
    assert "https://adtarget-intelligence-homologacao.streamlit.app/" in html
    assert "https://adtarget-intelligence-e7ftyu8hg9jcek5gaguhpm.streamlit.app/" not in html
