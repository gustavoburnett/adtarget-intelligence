"""Comunicação de calendário e registros em Vendas, sem mudar as séries."""

import json

import pandas as pd
import pytest

from src.components import charts, metas_charts
from tests.test_performance_meta_chart import _resultados


@pytest.fixture
def apresentacao(monkeypatch):
    figuras, notas = [], []
    monkeypatch.setattr(charts.st, "plotly_chart", lambda fig, **kwargs: figuras.append(json.loads(fig.to_json())))
    monkeypatch.setattr(charts.st, "caption", notas.append)
    return figuras, notas


def _vendas(apresentacao, *, futuros=(120, 80), atual=50, ausente_encerrado=None, limite=10):
    valores = [50] * 9 + [atual, *futuros]
    if ausente_encerrado is not None:
        valores[ausente_encerrado - 1] = None
    dados = pd.DataFrame({"atual": valores, "anterior": [60] * 12}, index=range(1, 13), dtype=float)
    copia = dados.copy(deep=True)
    charts.grafico_hero_vendas(dados, 2026, limite)
    pd.testing.assert_frame_equal(dados, copia)
    figura = apresentacao[0][-1]
    assert figura["data"][0]["y"] == [60] * 12
    principal = figura["data"][1]
    assert principal["x"] == list(range(1, 13))
    assert principal["y"] == [None if pd.isna(v) else v for v in dados["atual"]]
    assert principal["connectgaps"] is False
    assert principal["hovertemplate"] == charts._FORMATO_MOEDA_HOVER
    assert figura["layout"]["xaxis"]["range"] == [0.5, 12.5]
    assert figura["layout"]["hovermode"] == "x unified"
    return figura


@pytest.mark.parametrize("futuros,esperado", [
    ((120, 80), "Nov–Dez: futuros com registros de vendas"),
    ((0, 0), "Nov–Dez: futuros com registros de vendas"),
    ((-120, -80), "Nov–Dez: futuros com registros de vendas"),
    ((None, None), "Nov–Dez: futuros sem registros no recorte"),
    ((120, None), "Nov: futuro com registros de vendas · Dez: futuro sem registros no recorte"),
    ((None, 80), "Dez: futuro com registros de vendas · Nov: futuro sem registros no recorte"),
])
def test_vendas_distingue_registros_futuros_de_ausencia(apresentacao, futuros, esperado):
    figura = _vendas(apresentacao, futuros=futuros)
    assert apresentacao[1] == [
        "Jan–Set: meses encerrados · Out: em andamento, com registros de vendas · " + esperado
    ]
    anotacoes = figura["layout"]["annotations"]
    assert any(a["text"] == "<i>meses futuros</i>" for a in anotacoes)
    assert all("sem dado disponível" not in a["text"] for a in anotacoes)
    faixa = next(f for f in figura["layout"]["shapes"] if f["x1"] == 12.5)
    assert faixa["x0"] == 10.5


@pytest.mark.parametrize("atual,disponibilidade", [
    (0, "com registros de vendas"),
    (None, "sem registros no recorte"),
])
def test_mes_atual_nao_e_encerrado_nem_ausente_por_saldo_zero(apresentacao, atual, disponibilidade):
    _vendas(apresentacao, atual=atual)
    assert f"Out: em andamento, {disponibilidade}" in apresentacao[1][0]


def test_lacuna_encerrada_identificada_sem_confundir_historico_anterior(apresentacao):
    _vendas(apresentacao, ausente_encerrado=2)
    assert apresentacao[1][0].endswith("Sem registros no recorte: Fev")


@pytest.mark.parametrize("limite", [1, 12])
def test_limites_de_calendario_nao_inventam_meses(apresentacao, limite):
    figura = _vendas(apresentacao, limite=limite)
    nota = apresentacao[1][0]
    if limite == 1:
        assert nota.startswith("Jan: em andamento, com registros de vendas")
        assert "encerrados" not in nota
    else:
        assert nota == "Jan–Nov: meses encerrados · Dez: em andamento, com registros de vendas"
        assert all("futuros" not in a["text"] for a in figura["layout"]["annotations"])


def test_sem_limite_nao_inventa_calendario_do_ano_selecionado(apresentacao):
    figura = _vendas(apresentacao, limite=None)
    assert not apresentacao[1]
    assert all("futuros" not in a["text"] for a in figura["layout"]["annotations"])


def test_chamar_vendas_nao_altera_ticket_nem_meta(apresentacao):
    resultado, pulso = _resultados()
    meta_antes = metas_charts.evolucao_performance_meta(resultado, pulso, design_performance=True).to_json()
    charts.grafico_hero_ticket({1: 50, 10: 60, 11: 70, 12: 80}, 2026, 10)
    ticket_antes = apresentacao[0][-1]
    _vendas(apresentacao)
    apresentacao[1].clear()
    charts.grafico_hero_ticket({1: 50, 10: 60, 11: 70, 12: 80}, 2026, 10)
    assert apresentacao[0][-1] == ticket_antes
    assert any(a["text"] == "<i>sem dado disponível</i>" for a in ticket_antes["layout"]["annotations"])
    assert not apresentacao[1]
    assert metas_charts.evolucao_performance_meta(resultado, pulso, design_performance=True).to_json() == meta_antes
