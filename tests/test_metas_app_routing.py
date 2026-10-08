"""Integração da entrada: navegação e carga independente de METAS, offline."""

import datetime as dt
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from pages_content import (
    analitico_comercial,
    analitico_veiculos,
    auditoria_vendas,
    metas_resultados,
    performance_comercial,
)
from src.data import cleaning, loader, metas as metas_engine, metas_loader
from src.data.metas_schema import COLUNAS_METAS, ErroDeMetas
from src.components import shell
from tests.test_radar import recorde


APP = Path(__file__).resolve().parents[1] / "app.py"
PAGINAS_PRINCIPAIS = [
    "Performance Comercial", "Metas e Resultados", "Analítico Comercial",
    "Analítico Veículos",
]
PAGINAS_EXISTENTES = {
    "Performance Comercial": performance_comercial,
    "Analítico Comercial": analitico_comercial,
    "Analítico Veículos": analitico_veiculos,
    "🔧 Auditoria (dev)": auditoria_vendas,
}


@pytest.fixture(autouse=True)
def _cache_independente_por_teste():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def _entrada(monkeypatch, pagina, *, auditoria=False, erro_metas=None):
    vendas = recorde()
    for coluna in cleaning.COLUNAS_TEXTO + [cleaning.COL_NOTA_FISCAL]:
        if coluna not in vendas:
            vendas[coluna] = "TESTE"
    vendas[cleaning.COL_VENCIMENTO] = pd.NaT
    metas = pd.DataFrame(columns=COLUNAS_METAS)
    leituras = {"vendas": 0, "metas": 0}
    renders = []

    def ler_vendas(*_):
        leituras["vendas"] += 1
        return vendas

    def ler_metas(*_):
        leituras["metas"] += 1
        if erro_metas is not None:
            raise erro_metas
        return metas

    def render_performance(df, sincronizado_em=None, *, carregar_metas=None):
        renders.append(("Performance Comercial", df, sincronizado_em))

    def render_simples(nome):
        def render(df):
            renders.append((nome, df, None))
        return render

    def render_metas(df, *, metas_df=None, erro_metas=None):
        renders.append(("Metas e Resultados", df, (metas_df, erro_metas)))
        if erro_metas is not None:
            st.error(str(erro_metas))

    monkeypatch.setattr(st, "secrets", {
        "spreadsheet_id": "TESTE_OFFLINE",
        "gcp_service_account": {},
        "dev_auditoria": auditoria,
    })
    monkeypatch.setattr(loader, "load_all_sheets", ler_vendas)
    monkeypatch.setattr(metas_loader, "load_metas", ler_metas)
    monkeypatch.setattr(cleaning, "limpar_dataframe", lambda df: df)
    for nome, modulo in PAGINAS_EXISTENTES.items():
        monkeypatch.setattr(
            modulo, "render",
            render_performance if nome == "Performance Comercial" else render_simples(nome),
        )
    monkeypatch.setattr(metas_resultados, "render", render_metas)
    app = AppTest.from_file(str(APP))
    app.session_state["autenticado"] = True
    app.session_state["nav_pagina"] = pagina
    app.run(timeout=20)
    return app, vendas, metas, leituras, renders


@pytest.mark.parametrize("auditoria", [False, True])
def test_navegacao_tem_quarto_item_permanente_e_preserva_auditoria(monkeypatch, auditoria):
    app, _, _, _, _ = _entrada(
        monkeypatch, "Performance Comercial", auditoria=auditoria,
    )
    assert not app.exception
    esperado = PAGINAS_PRINCIPAIS + (["🔧 Auditoria (dev)"] if auditoria else [])
    assert app.radio(key="nav_pagina").options == [shell.navigation_label(nome) for nome in esperado]
    assert app.radio(key="nav_pagina").value == "Performance Comercial"


@pytest.mark.parametrize("pagina", PAGINAS_EXISTENTES)
def test_paginas_existentes_nao_carregam_metas_e_preservam_argumentos(monkeypatch, pagina):
    app, vendas, _, leituras, renders = _entrada(monkeypatch, pagina, auditoria=True)
    assert not app.exception
    assert leituras == {"vendas": 1, "metas": 0}
    assert len(renders) == 1
    nome, recebidas, sincronizado_em = renders[0]
    assert nome == pagina
    pd.testing.assert_frame_equal(recebidas, vendas)
    assert (sincronizado_em is not None) == (pagina == "Performance Comercial")


def test_nova_pagina_recebe_base_completa_e_metas_por_argumento_nomeado(monkeypatch):
    app, vendas, metas, leituras, renders = _entrada(monkeypatch, "Metas e Resultados")
    assert not app.exception
    assert leituras == {"vendas": 1, "metas": 1}
    assert len(renders) == 1
    nome, recebidas, (metas_recebidas, erro) = renders[0]
    assert nome == "Metas e Resultados"
    pd.testing.assert_frame_equal(recebidas, vendas)
    pd.testing.assert_frame_equal(metas_recebidas, metas)
    assert erro is None


def test_metas_so_sao_lidas_ao_navegar_e_reutilizam_cache_independente(monkeypatch):
    app, _, _, leituras, _ = _entrada(monkeypatch, "Performance Comercial")
    assert leituras == {"vendas": 1, "metas": 0}
    app.radio(key="nav_pagina").set_value("Metas e Resultados").run(timeout=20)
    assert not app.exception
    assert leituras == {"vendas": 1, "metas": 1}
    app.run(timeout=20)
    app.radio(key="nav_pagina").set_value("Analítico Comercial").run(timeout=20)
    app.radio(key="nav_pagina").set_value("Metas e Resultados").run(timeout=20)
    assert not app.exception
    assert leituras == {"vendas": 1, "metas": 1}


def test_atualizar_na_visao_metas_recarrega_ambas_as_fontes(monkeypatch):
    app, _, _, leituras, _ = _entrada(monkeypatch, "Metas e Resultados")
    app.button(key="masthead_refresh").click().run(timeout=20)
    assert not app.exception
    assert leituras == {"vendas": 2, "metas": 2}
    assert app.toast[0].value == "Dados atualizados"


def test_atualizar_outra_pagina_invalida_metas_sem_carrega_las(monkeypatch):
    app, _, _, leituras, _ = _entrada(monkeypatch, "Metas e Resultados")
    app.radio(key="nav_pagina").set_value("Performance Comercial").run(timeout=20)
    app.button(key="masthead_refresh").click().run(timeout=20)
    assert not app.exception
    assert leituras == {"vendas": 2, "metas": 1}
    app.radio(key="nav_pagina").set_value("Metas e Resultados").run(timeout=20)
    assert not app.exception
    assert leituras == {"vendas": 2, "metas": 2}


def test_ambas_as_fontes_tem_cache_independente_de_quinze_minutos(monkeypatch):
    cache_original = st.cache_data
    decoradores = []

    def observar_cache(*args, **kwargs):
        decoradores.append(kwargs)
        return cache_original(*args, **kwargs)

    monkeypatch.setattr(st, "cache_data", observar_cache)
    app, _, _, _, _ = _entrada(monkeypatch, "Metas e Resultados")
    assert not app.exception
    assert len(decoradores) == 2
    assert all(decorador["ttl"] == 900 for decorador in decoradores)
    assert len({decorador["show_spinner"] for decorador in decoradores}) == 2


@pytest.mark.parametrize("categoria", ["fonte", "estrutura", "validacao"])
def test_falha_de_metas_e_entregue_somente_a_nova_pagina(monkeypatch, categoria):
    erro = ErroDeMetas("METAS indisponível no teste offline.", categoria)
    app, vendas, _, leituras, renders = _entrada(
        monkeypatch, "Metas e Resultados", erro_metas=erro,
    )
    assert not app.exception
    assert leituras == {"vendas": 1, "metas": 1}
    assert len(renders) == 1
    _, recebidas, (metas_recebidas, erro_recebido) = renders[0]
    pd.testing.assert_frame_equal(recebidas, vendas)
    assert metas_recebidas is None
    assert erro_recebido is erro
    assert app.error[0].value == "METAS indisponível no teste offline."


@pytest.mark.parametrize("pagina", PAGINAS_EXISTENTES)
def test_outros_destinos_continuam_operacionais_apos_erro_metas(monkeypatch, pagina):
    app, vendas, _, leituras, renders = _entrada(
        monkeypatch, "Metas e Resultados", auditoria=True,
        erro_metas=ErroDeMetas("A aba METAS não existe no teste.", "fonte"),
    )
    app.radio(key="nav_pagina").set_value(pagina).run(timeout=20)
    assert not app.exception
    assert not app.error
    assert leituras == {"vendas": 1, "metas": 1}
    assert renders[-1][0] == pagina
    pd.testing.assert_frame_equal(renders[-1][1], vendas)


def test_erro_inesperado_do_loader_nao_e_ocultado(monkeypatch):
    app, _, _, _, renders = _entrada(
        monkeypatch, "Metas e Resultados",
        erro_metas=RuntimeError("FALHA_DE_PROGRAMACAO_OFFLINE"),
    )
    assert len(app.exception) == 1
    assert app.exception[0].message == "FALHA_DE_PROGRAMACAO_OFFLINE"
    assert not renders


def test_gate_de_autenticacao_impede_leitura_de_metas(monkeypatch):
    app, _, _, leituras, renders = _entrada(monkeypatch, "Performance Comercial")
    leituras.update(vendas=0, metas=0)
    renders.clear()
    st.cache_data.clear()
    app.session_state["autenticado"] = False
    app.session_state["nav_pagina"] = "Metas e Resultados"
    app.run(timeout=20)
    assert not app.exception
    assert leituras == {"vendas": 0, "metas": 0}
    assert not renders
    assert "Senha do aplicativo não configurada" in app.error[0].value


def test_pagina_real_integra_loader_schema_engine_e_estado_de_ano_sem_metas(monkeypatch):
    render_original = metas_resultados.render
    load_metas_original = metas_loader.load_metas
    app, _, _, _, _ = _entrada(monkeypatch, "Metas e Resultados")
    leituras_fonte = []
    valores = [list(COLUNAS_METAS)] + [
        ["GRUPO", "G", "", 2026, mes, 100, "SIM", 1,
         "2026-10-05T12:00:00-03:00", "TESTE OFFLINE"]
        for mes in range(1, 13)
    ]

    class FonteMetas:
        def open_by_key(self, spreadsheet_id):
            assert spreadsheet_id == "TESTE_OFFLINE"
            return self

        def worksheet(self, nome):
            assert nome == "METAS"
            return self

        def get(self, **opcoes):
            leituras_fonte.append(opcoes)
            return valores

    monkeypatch.setattr(loader, "criar_cliente", lambda _: FonteMetas())
    monkeypatch.setattr(metas_loader, "load_metas", load_metas_original)
    monkeypatch.setattr(metas_resultados, "render", render_original)
    monkeypatch.setattr(metas_engine, "data_local", lambda _: dt.date(2026, 10, 5))
    st.cache_data.clear()
    app.run(timeout=20)
    assert not app.exception
    assert not app.error
    assert leituras_fonte == [{"value_render_option": "UNFORMATTED_VALUE"}]
    html = "\n".join(element.value for element in app.markdown)
    assert "RITMO FECHADO" in html
    assert "91,1%" in html
    assert "Jan a Set/2026" in html
    assert "META ANUAL · 2026" in html
    assert "R$ 1.200,00" in html
    assert "FORECAST" in html
    assert not app.expander

    app.button_group(key="metas_ano").set_value(2025).run(timeout=20)
    assert not app.exception
    assert not app.error
    html = "\n".join(element.value for element in app.markdown)
    assert "Não há metas cadastradas para 2025" in html
    assert "RITMO FECHADO" not in html
    assert "FORECAST" not in html
    assert leituras_fonte == [{"value_render_option": "UNFORMATTED_VALUE"}]
