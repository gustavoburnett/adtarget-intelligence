"""Design 1G: apresentação da Carteira por Status sem mudar seu contrato."""

from copy import deepcopy
import json

import pandas as pd
import pytest

from src.components import charts
from src.components.design_tokens import COLOR, TYPOGRAPHY


def _figura(monkeypatch, dados, *, estilo=False):
    figuras = []
    monkeypatch.setattr(charts.st, "plotly_chart", lambda fig, **kwargs: figuras.append(fig))
    charts.grafico_por_status(dados, "Carteira por status", estilo_analitico=estilo)
    assert len(figuras) == 1
    return json.loads(figuras[0].to_json())


def _contrato(figura):
    serie = figura["data"][0]
    layout = figura["layout"]
    return {
        "serie": {chave: serie.get(chave) for chave in (
            "type", "x", "y", "orientation", "text", "hovertemplate", "hoverinfo",
            "customdata", "name", "showlegend",
        )},
        "eixos": {
            eixo: {chave: layout.get(eixo, {}).get(chave) for chave in (
                "type", "range", "autorange", "rangemode", "categoryorder", "categoryarray",
            )}
            for eixo in ("xaxis", "yaxis")
        },
        "hovermode": layout.get("hovermode"),
    }


@pytest.mark.parametrize("valores", [
    [1000.25, 9000000.44, 10.01],
    [0, 0, 0],
    [-25.50, -4000.25, 0],
    [-10.50, 0, 123.45],
])
def test_estilo_preserva_valores_contagens_ordem_hover_e_escalas(monkeypatch, valores):
    dados = pd.DataFrame({
        "STATUS": ["EM VEICULAÇÃO", "FATURADO", "STATUS COM NOME MUITO LONGO SEM ALTERAÇÃO"],
        "valor": valores, "qtd_pis": [6, 150, 2],
    })
    antes = dados.copy(deep=True)
    padrao = _figura(monkeypatch, dados)
    estilizada = _figura(monkeypatch, dados, estilo=True)

    assert _contrato(estilizada) == _contrato(padrao)
    assert estilizada["data"][0]["text"] == ["6 PIs", "150 PIs", "2 PIs"]
    assert estilizada["layout"]["yaxis"]["autorange"] == "reversed"
    assert "range" not in estilizada["layout"]["xaxis"]
    assert "range" not in estilizada["layout"]["yaxis"]
    pd.testing.assert_frame_equal(dados, antes)


def test_estilo_e_optativo_e_usa_tokens_sem_duplicar_titulo(monkeypatch):
    dados = pd.DataFrame({"STATUS": ["FATURADO"], "valor": [123.45], "qtd_pis": [3]})
    padrao = _figura(monkeypatch, dados)
    estilo = _figura(monkeypatch, dados, estilo=True)

    assert padrao["layout"]["title"]["text"] == "Carteira por status"
    assert padrao["data"][0]["textposition"] == "auto"
    assert "marker" not in padrao["data"][0]
    # O frontend precisa receber texto vazio explícito; título sem ``text``
    # já resultou em "undefined" na renderização nativa do Streamlit.
    assert estilo["layout"]["title"]["text"] == ""
    assert estilo["data"][0]["marker"]["color"] == COLOR["brand"]
    assert estilo["layout"]["font"]["family"] == TYPOGRAPHY["family"]
    assert estilo["layout"]["plot_bgcolor"] == COLOR["surface-card"]


def test_rotulos_zero_negativos_e_longos_continuam_visiveis_sem_renomear_status(monkeypatch):
    status = ["STATUS LONGO COM MAIS DE VINTE CARACTERES", "ZERO", "NEGATIVO"]
    dados = pd.DataFrame({"STATUS": status, "valor": [100, 0, -25], "qtd_pis": [2, 0, 1]})
    estilo = _figura(monkeypatch, dados, estilo=True)

    assert estilo["data"][0]["y"] == status
    assert estilo["layout"]["yaxis"]["tickvals"] == status
    assert estilo["layout"]["yaxis"]["ticktext"][0].replace("<br>", " ") == status[0]
    assert estilo["data"][0]["textposition"] == ["auto", "outside", "auto"]
    assert estilo["data"][0]["cliponaxis"] is False
    assert estilo["layout"]["uniformtext"]["mode"] == "show"


def test_rotulo_de_status_desconhecido_nao_injeta_html(monkeypatch):
    dados = pd.DataFrame({"STATUS": ["<b>STATUS</b>"], "valor": [123.45], "qtd_pis": [1]})
    estilo = _figura(monkeypatch, dados, estilo=True)
    assert estilo["data"][0]["y"] == ["<b>STATUS</b>"]
    assert estilo["layout"]["yaxis"]["ticktext"] == ["&lt;b&gt;STATUS&lt;/b&gt;"]


def test_altura_acomoda_status_adicionais_sem_alterar_coordenadas(monkeypatch):
    dados = pd.DataFrame({
        "STATUS": [f"STATUS {numero}" for numero in range(12)],
        "valor": list(range(12)), "qtd_pis": list(range(12)),
    })
    estilo = _figura(monkeypatch, dados, estilo=True)
    assert estilo["layout"]["height"] == 12 * 42 + 76
    assert estilo["data"][0]["x"] == list(range(12))
    assert estilo["data"][0]["y"] == list(dados["STATUS"])


@pytest.mark.parametrize("estilo", [False, True])
def test_vazio_preserva_mensagem_e_nao_cria_figura(monkeypatch, estilo):
    mensagens = []
    dados = pd.DataFrame(columns=["STATUS", "valor", "qtd_pis"])
    antes = deepcopy(dados)
    monkeypatch.setattr(charts.st, "info", mensagens.append)
    monkeypatch.setattr(charts.st, "plotly_chart", lambda *args, **kwargs: pytest.fail("Gráfico vazio"))
    charts.grafico_por_status(dados, "Carteira por status", estilo_analitico=estilo)
    assert mensagens == ["Sem dados no recorte selecionado"]
    pd.testing.assert_frame_equal(dados, antes)
