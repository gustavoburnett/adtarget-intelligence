"""Design 1H: barras monetárias, sem transformação comercial ou temporal."""

import json

import pandas as pd
import pytest

from src.components import cards, charts
from src.components.design_tokens import COLOR, TYPOGRAPHY


def _figura(monkeypatch, dados, *, estilo=False, top_n=None):
    figuras = []
    parametros = []
    monkeypatch.setattr(
        charts.st, "plotly_chart",
        lambda fig, **kwargs: (figuras.append(fig), parametros.append(kwargs)),
    )
    charts.grafico_barra_horizontal(
        dados, "entidade", "valor", "Vendas por Grupo", top_n,
        estilo_veiculos=estilo,
    )
    assert parametros == [{"width": "stretch"}]
    return json.loads(figuras[0].to_json())


def _contrato(figura):
    serie = figura["data"][0]
    layout = figura["layout"]
    return {
        "serie": {campo: serie.get(campo) for campo in (
            "type", "x", "y", "orientation", "hovertemplate", "hoverinfo",
            "customdata", "name", "showlegend",
        )},
        "eixos": {
            eixo: {campo: layout.get(eixo, {}).get(campo) for campo in (
                "type", "range", "autorange", "rangemode", "categoryorder", "categoryarray",
            )}
            for eixo in ("xaxis", "yaxis")
        },
        "hovermode": layout.get("hovermode"),
    }


@pytest.mark.parametrize("valores", [
    [6_286_092.30, 5_666_035.24, 123_720.01],
    [0, 0, 0],
    [-10.55, -4_000.25, 0],
    [-10.55, 0, 123.456789],
    [1_000_000_000_000.99, 0.01, 0],
])
def test_estilo_preserva_series_ordem_tooltips_escala_e_fonte(monkeypatch, valores):
    dados = pd.DataFrame({
        "entidade": ["DISNEY", "TEADS", "GRUPO LONGO COM DIMENSÃO COMERCIAL INTEGRAL"],
        "valor": valores,
    })
    antes = dados.copy(deep=True)
    legado = _figura(monkeypatch, dados)
    estilo = _figura(monkeypatch, dados, estilo=True)

    assert _contrato(estilo) == _contrato(legado)
    assert estilo["data"][0]["x"] == valores
    assert estilo["data"][0]["y"] == list(dados["entidade"])
    assert estilo["layout"]["yaxis"]["autorange"] == "reversed"
    assert "range" not in estilo["layout"]["xaxis"]
    assert "range" not in estilo["layout"]["yaxis"]
    pd.testing.assert_frame_equal(dados, antes)


def test_estilo_optativo_preserva_exatamente_apresentacao_legada(monkeypatch):
    dados = pd.DataFrame({"entidade": ["TEADS"], "valor": [123.45]})
    legado = _figura(monkeypatch, dados)
    serie = legado["data"][0]
    assert "text" not in serie
    assert "textposition" not in serie
    assert serie["marker"]["color"] == charts.COR_SERIE_PRINCIPAL
    assert serie["hovertemplate"] == "R$ %{x:,.2f}<extra></extra>"
    assert legado["layout"]["title"] == {
        "text": "Vendas por Grupo", "font": {"size": 15, "color": "#14171C"},
    }
    assert legado["layout"]["margin"] == {"t": 52, "b": 16, "l": 8, "r": 8}
    assert legado["layout"]["bargap"] == 0.38
    assert "height" not in legado["layout"]
    assert "font" not in legado["layout"]


def test_rotulos_monetarios_completos_ptbr_sem_arredondar_valores_da_serie(monkeypatch):
    valores = [6_286_092.30, 123.456789, 0.0, -0.01]
    dados = pd.DataFrame({"entidade": ["DISNEY", "TEADS", "ZERO", "AJUSTE"], "valor": valores})
    estilo = _figura(monkeypatch, dados, estilo=True)
    serie = estilo["data"][0]
    assert serie["text"] == ["R$ 6.286.092,30", "R$ 123,46", "R$ 0,00", "R$ -0,01"]
    assert serie["x"] == valores
    assert serie["text"] == [cards.formatar_moeda(valor) for valor in valores]
    assert serie["textposition"] == ["auto", "auto", "outside", "auto"]
    assert serie["textangle"] == 0
    assert serie["cliponaxis"] is False
    assert estilo["layout"]["uniformtext"] == {"minsize": 11, "mode": "show"}


def test_grupos_e_veiculos_continuam_dimensoes_distintas_inclusive_disney(monkeypatch):
    entidades = ["DISNEY", "DISNEY+", "DISNEY — ESPN", "TEADS"]
    dados = pd.DataFrame({"entidade": entidades, "valor": [6_286_092.30, 4_800_000.0, 782_000.0, 5_666_035.24]})
    estilo = _figura(monkeypatch, dados, estilo=True)
    assert estilo["data"][0]["y"] == entidades
    assert estilo["layout"]["yaxis"]["tickvals"] == entidades
    assert sum(estilo["data"][0]["x"]) == sum(dados["valor"])


def test_ticks_quebram_nomes_longos_sem_truncar_ou_injetar_html(monkeypatch):
    nome = "GRUPO COM NOME COMERCIAL MUITO LONGO PRESERVADO"
    dados = pd.DataFrame({"entidade": [nome, "<b>DISNEY</b>"], "valor": [100, 200]})
    estilo = _figura(monkeypatch, dados, estilo=True)
    eixo = estilo["layout"]["yaxis"]
    assert eixo["tickvals"] == [nome, "<b>DISNEY</b>"]
    assert eixo["ticktext"][0].replace("<br>", " ") == nome
    assert eixo["ticktext"][1] == "&lt;b&gt;DISNEY&lt;/b&gt;"
    assert eixo["automargin"] is True


def test_tokens_inter_grade_e_titulo_gerenciado_pela_pagina(monkeypatch):
    dados = pd.DataFrame({"entidade": ["DISNEY"], "valor": [6_286_092.30]})
    estilo = _figura(monkeypatch, dados, estilo=True)
    assert estilo["layout"]["title"]["text"] == ""
    assert estilo["data"][0]["marker"]["color"] == COLOR["brand"]
    assert estilo["layout"]["font"]["family"] == TYPOGRAPHY["family"]
    assert estilo["layout"]["plot_bgcolor"] == COLOR["surface-card"]
    assert estilo["layout"]["paper_bgcolor"] == "rgba(0,0,0,0)"
    assert estilo["layout"]["xaxis"]["gridcolor"] == COLOR["chart-grid"]
    assert estilo["layout"]["margin"]["r"] >= 110


def test_todos_grupos_elegiveis_preservados_sem_top5_implicito(monkeypatch):
    dados = pd.DataFrame({"entidade": [f"GRUPO {i}" for i in range(20)], "valor": list(range(20, 0, -1))})
    estilo = _figura(monkeypatch, dados, estilo=True)
    assert estilo["data"][0]["y"] == list(dados["entidade"])
    assert estilo["data"][0]["x"] == list(dados["valor"])
    assert estilo["layout"]["height"] == 20 * 44 + 64


def test_top_n_existente_nao_altera_ordem_ou_fonte(monkeypatch):
    dados = pd.DataFrame({"entidade": ["A", "B", "C"], "valor": [3, 2, 1]})
    legado = _figura(monkeypatch, dados, top_n=2)
    estilo = _figura(monkeypatch, dados, estilo=True, top_n=2)
    assert _contrato(estilo) == _contrato(legado)
    assert estilo["data"][0]["y"] == ["A", "B"]
    assert len(dados) == 3


@pytest.mark.parametrize("estilo", [False, True])
def test_vazio_preserva_estado_existente_sem_criar_grafico(monkeypatch, estilo):
    mensagens = []
    dados = pd.DataFrame(columns=["entidade", "valor"])
    antes = dados.copy(deep=True)
    monkeypatch.setattr(charts.st, "info", mensagens.append)
    monkeypatch.setattr(charts.st, "plotly_chart", lambda *args, **kwargs: pytest.fail("Gráfico vazio"))
    charts.grafico_barra_horizontal(dados, "entidade", "valor", "Vendas por Grupo", estilo_veiculos=estilo)
    assert mensagens == ["Sem dados no recorte selecionado"]
    pd.testing.assert_frame_equal(dados, antes)
