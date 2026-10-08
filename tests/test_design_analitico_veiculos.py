"""Design 1H: regressão dos contratos da página contra o Design 1G congelado."""

from functools import lru_cache
import json
from pathlib import Path
import subprocess
from types import ModuleType

import pandas as pd
import pyarrow as pa
import pytest
from streamlit.testing.v1 import AppTest

from src.components import cards
from src.data import cleaning, metrics
from tests.test_design_analitico_comercial import _fonte as _fonte_comercial


BASELINE = "133efd0caef061a932c70f9893d6f47df7bea68d"
RAIZ = Path(__file__).resolve().parents[1]
COLUNAS_VEICULOS = [
    "Veículo", "Vendas (Bruto)", "Vendas (Líquido)", "Ticket Médio", "Qtd PIs", "% do Total",
]


@lru_cache
def _congelada():
    caminho = "pages_content/analitico_veiculos.py"
    fonte = subprocess.run(
        ["git", "show", f"{BASELINE}:{caminho}"],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout
    modulo = ModuleType("analitico_veiculos_design_1g_congelado")
    exec(compile(fonte, f"<{BASELINE}:{caminho}>", "exec"), modulo.__dict__)
    return modulo


def _fonte():
    df = _fonte_comercial()
    meses = df[cleaning.COL_MES_VEICULACAO_DATA].dt.month
    g = df[cleaning.COL_GRUPO].eq("G")
    h = df[cleaning.COL_GRUPO].eq("H")
    veiculos_disney = {1: "DISNEY+", 2: "ESPN", 9: "ESPN 2", 10: "DISNEY+", 11: "ESPN 4", 12: "ESPN 3"}
    df.loc[g & df[cleaning.COL_VEICULO].ne("HOMÔNIMO"), cleaning.COL_VEICULO] = meses.map(veiculos_disney)
    df.loc[h & df[cleaning.COL_VEICULO].ne("HOMÔNIMO"), cleaning.COL_VEICULO] = "TEADS"
    df.loc[g, cleaning.COL_GRUPO] = "DISNEY"
    df.loc[h, cleaning.COL_GRUPO] = "TEADS"
    df.loc[g, cleaning.COL_AGENCIA] = "AGÊNCIA DISNEY"
    df.loc[h, cleaning.COL_AGENCIA] = "AGÊNCIA TEADS"
    return df


def _render_atual(df):
    from pages_content.analitico_veiculos import render
    render(df)


def _render_congelada(df):
    from tests.test_design_analitico_veiculos import _congelada
    _congelada().render(df)


def _pagina(executar=_render_atual, *, fonte=None, ano=2026, valor="Valor Líquido",
            criterio="Mês (Veiculação)", grupos=None, agencias=None, clientes=None, drill=None):
    df = _fonte() if fonte is None else fonte
    app = AppTest.from_function(executar, args=(df,))
    for chave, selecionado in (("ano", ano), ("valor", valor), ("mes", criterio)):
        app.session_state[f"anvei_{chave}"] = selecionado
    for chave, selecionados in ((cleaning.COL_GRUPO, grupos), (cleaning.COL_AGENCIA, agencias), (cleaning.COL_CLIENTE, clientes)):
        if selecionados is not None:
            app.session_state[f"anvei_fc_{chave}_aplicado"] = selecionados
    if drill is not None:
        app.session_state["anvei_drill"] = drill
    app.run(timeout=20)
    assert not app.exception
    return app


def _raw(tabela):
    return pa.ipc.open_stream(tabela.proto.arrow_data.data).read_all().to_pandas()


def _display(tabela):
    return pa.ipc.open_stream(tabela.proto.arrow_data.styler.display_values).read_all().to_pandas()


def _metricas(app):
    return [(el.label, el.value, el.proto.help) for el in app.metric]


def _filtros(app):
    return [(el.proto.popover.label, el.proto.popover.disabled) for el in app.get("popover")]


def _seletores(app):
    return [(el.key, el.label, el.options, el.value, el.proto.disabled) for el in app.button_group]


def _figuras(app):
    return [json.loads(el.proto.spec) for el in app.get("plotly_chart")]


def _contrato(figura):
    return [{campo: serie.get(campo) for campo in ("x", "y", "orientation", "customdata", "hovertemplate")}
            for serie in figura["data"]]


def _comparar(**opcoes):
    atual, anterior = [_pagina(executar, **opcoes) for executar in (_render_atual, _render_congelada)]
    assert _metricas(atual) == _metricas(anterior)
    assert _seletores(atual) == _seletores(anterior)
    assert _filtros(atual) == _filtros(anterior)
    assert [el.label for el in atual.tabs] == [el.label for el in anterior.tabs] == ["Veículos", "Agências", "Clientes"]
    assert [_contrato(fig) for fig in _figuras(atual)] == [_contrato(fig) for fig in _figuras(anterior)]
    for a, b in zip(_figuras(atual), _figuras(anterior), strict=True):
        assert a["layout"]["yaxis"]["autorange"] == b["layout"]["yaxis"]["autorange"]
        assert "range" not in a["layout"]["xaxis"] and "range" not in b["layout"]["xaxis"]
    assert len(atual.dataframe) == 3
    for pos in (1, 2):
        pd.testing.assert_frame_equal(_raw(atual.dataframe[pos]), anterior.dataframe[pos].value)
    return atual, anterior


@pytest.mark.parametrize("ano", [2024, 2025, 2026])
@pytest.mark.parametrize("valor,criterio", [
    ("Valor Líquido", "Mês (Veiculação)"), ("Valor Bruto", "Mês (Veiculação)"),
    ("Valor Líquido", "Mês (Ganho)"), ("Valor Bruto", "Mês (Ganho)"),
])
def test_anos_toggles_metricas_series_e_tres_rankings_preservados(ano, valor, criterio):
    atual, anterior = _comparar(ano=ano, valor=valor, criterio=criterio)
    raw, exibida = _raw(atual.dataframe[0]), _display(atual.dataframe[0])
    legado = anterior.dataframe[0].value
    assert list(raw.columns) == list(legado.columns) == COLUNAS_VEICULOS
    assert len(raw) == len(legado)
    for coluna in ("Vendas (Bruto)", "Vendas (Líquido)", "Ticket Médio", "% do Total"):
        assert pd.api.types.is_numeric_dtype(raw[coluna])
        assert exibida[coluna].tolist() == legado[coluna].tolist()
    assert raw["Qtd PIs"].tolist() == legado["Qtd PIs"].tolist()
    assert all("TEADS — TEADS" != entidade for entidade in exibida["Veículo"])
    assert all(entidade in exibida["Veículo"].tolist() for entidade in legado["Veículo"] if not entidade.startswith("TEADS — TEADS"))


@pytest.mark.parametrize("grupos,agencias,clientes", [
    (["DISNEY"], None, None), (["TEADS"], None, None),
    (["DISNEY"], ["AGÊNCIA DISNEY"], None),
    (["DISNEY"], ["AGÊNCIA TEADS"], None),
    (None, None, ["CLIENTE G"]), ([], None, None),
])
def test_cascata_e_recortes_vazios_preservados(grupos, agencias, clientes):
    _comparar(grupos=grupos, agencias=agencias, clientes=clientes)


@pytest.mark.parametrize("grupo", ["DISNEY", "TEADS", "FORA"])
def test_seletor_de_drill_preserva_opcoes_estado_e_veiculos_do_grupo(grupo):
    atual, anterior = _comparar(drill=grupo)
    for app in (atual, anterior):
        seletor = app.selectbox(key="anvei_drill")
        assert seletor.value == grupo
    assert atual.selectbox[0].options == anterior.selectbox[0].options
    if grupo == "DISNEY":
        assert "DISNEY+" in _figuras(atual)[1]["data"][0]["y"]
        assert "DISNEY" not in _figuras(atual)[1]["data"][0]["y"]


@pytest.mark.parametrize("grupos", [None, []])
def test_consolidado_redundante_eliminado_sem_perda_de_dados_ou_estado_vazio(grupos):
    atual, anterior = _comparar(grupos=grupos)
    assert "Consolidado por Grupo + Veículo" not in [el.value for el in atual.subheader]
    if grupos is None:
        assert len(anterior.dataframe) == 4
        pd.testing.assert_frame_equal(anterior.dataframe[0].value, anterior.dataframe[-1].value)
    else:
        assert [el.value for el in atual.info] == [el.value for el in anterior.info]


def test_disney_consolidado_e_homonimos_preservam_financeiro_e_denominadores():
    fonte = _fonte()
    antes = fonte.copy(deep=True)
    atual, _ = _comparar(fonte=fonte)
    recorte = fonte[fonte[cleaning.COL_MES_VEICULACAO_DATA].dt.year.eq(2026)]
    agregado = metrics.agregado_por_grupo_veiculo(recorte)
    raw = _raw(atual.dataframe[0])
    assert raw["Vendas (Bruto)"].tolist() == agregado["vendas_bruto"].tolist()
    assert raw["Vendas (Líquido)"].tolist() == agregado["vendas_liquido"].tolist()
    assert raw["Ticket Médio"].tolist() == agregado["ticket_medio"].tolist()
    assert raw["% do Total"].tolist() == agregado["pct_do_total"].tolist()
    assert raw["Vendas (Líquido)"].sum() == pytest.approx(metrics.vendas(recorte))
    assert raw["Qtd PIs"].sum() == int(metrics.mascara_vendas(recorte).sum())
    assert len(raw) == metrics.veiculos_ativos(recorte)
    assert {"DISNEY — HOMÔNIMO", "TEADS — HOMÔNIMO"}.issubset(raw["Veículo"])
    grupo = metrics.agregado_por_dimensao(recorte, cleaning.COL_GRUPO)
    total_disney = agregado.loc[agregado[cleaning.COL_GRUPO].eq("DISNEY"), "vendas_liquido"].sum()
    assert grupo.loc[grupo[cleaning.COL_GRUPO].eq("DISNEY"), "valor"].iloc[0] == pytest.approx(total_disney)
    assert atual.metric[1].value == cards.formatar_moeda_executiva(metrics.ticket_medio(recorte))
    pd.testing.assert_frame_equal(fonte, antes)


def test_limpar_filtros_preserva_ano_toggles_e_seletor_de_drill():
    atual, anterior = _comparar(ano=2025, valor="Valor Bruto", criterio="Mês (Ganho)", grupos=["DISNEY"], drill="DISNEY")
    for app in (atual, anterior):
        app.button(key="anvei_limpar_filtros").click().run(timeout=20)
        assert not app.exception
        assert app.button_group(key="anvei_ano").value == 2025
        assert app.button_group(key="anvei_valor").value == "Valor Bruto"
        assert app.button_group(key="anvei_mes").value == "Mês (Ganho)"
        assert app.selectbox(key="anvei_drill").value == "DISNEY"
        assert "anvei_fc_GRUPO_aplicado" not in app.session_state
    assert _metricas(atual) == _metricas(anterior)


def test_defaults_e_tres_dimensoes_permanecem_os_mesmos():
    apps = [AppTest.from_function(executar, args=(_fonte(),)).run(timeout=20)
            for executar in (_render_atual, _render_congelada)]
    atual, anterior = apps
    assert not atual.exception and not anterior.exception
    assert _seletores(atual) == _seletores(anterior)
    assert _filtros(atual) == _filtros(anterior) and len(_filtros(atual)) == 3
    assert atual.button_group(key="anvei_ano").value == 2026
    assert atual.button_group(key="anvei_valor").value == "Valor Líquido"
    assert atual.button_group(key="anvei_mes").value == "Mês (Veiculação)"
