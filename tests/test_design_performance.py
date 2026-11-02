"""Apresentação dos indicadores da Performance, com valores sintéticos."""

from copy import deepcopy
import xml.etree.ElementTree as ET

import pandas as pd
import pytest

from src.components import cards
from src.data.cleaning import COL_GRUPO
from tests.test_metas_app_routing import _entrada
from tests.test_performance_meta import _pagina


def _elementos(raiz, classe):
    return [elemento for elemento in raiz.iter()
            if classe in elemento.get("class", "").split()]


def _unico(raiz, classe):
    elementos = _elementos(raiz, classe)
    assert len(elementos) == 1
    return elementos[0]


def _texto(elemento):
    return "".join(elemento.itertext())


def _indicadores(monkeypatch, *, ytd=None, vazio=False, total=7_654_321.25,
                 faturado=5_432_123.47, aberto=2_222_197.78,
                 ticket=76_543.21, campanhas=1_234):
    html = []
    monkeypatch.setattr(cards.st, "markdown", lambda texto, **_: html.append(texto))
    resultado = ytd if ytd is not None else {
        "atual": 6_500_000, "anterior": 5_000_000,
        "variacao_pct": 30.0, "mes_limite": 9,
    }
    vendas = {"total": total, "faturado": faturado}
    antes = deepcopy((resultado, vendas))
    cards.linha_kpis(resultado, 2026, vazio, vendas, aberto, ticket, campanhas)
    assert (resultado, vendas) == antes
    assert len(html) == 1
    return ET.fromstring(html[0])


@pytest.mark.parametrize("valores,esperados", [
    ({}, [
        ("Vendas", "R$ 7,65 Mi", "R$ 7.654.321,25", "R$ 5,43 Mi já faturado"),
        ("Em Aberto", "R$ 2,22 Mi", "R$ 2.222.197,78", "vendido, ainda não faturado"),
        ("Ticket Médio", "R$ 76,54 mil", "R$ 76.543,21", "Vendas ÷ PIs da base"),
        ("Campanhas", "1.234", None, "Cliente + Campanha"),
    ]),
    ({"total": 123.45, "faturado": 0, "aberto": 0, "ticket": 12.34, "campanhas": 3}, [
        ("Vendas", "R$ 123,45", "R$ 123,45", "R$ 0,00 já faturado"),
        ("Em Aberto", "R$ 0,00", "R$ 0,00", "vendido, ainda não faturado"),
        ("Ticket Médio", "R$ 12,34", "R$ 12,34", "Vendas ÷ PIs da base"),
        ("Campanhas", "3", None, "Cliente + Campanha"),
    ]),
    ({"total": -1_500_000, "faturado": -1_234.56, "aberto": 0.25,
      "ticket": None, "campanhas": 0}, [
        ("Vendas", "-R$ 1,50 Mi", "R$ -1.500.000,00", "-R$ 1,23 mil já faturado"),
        ("Em Aberto", "R$ 0,25", "R$ 0,25", "vendido, ainda não faturado"),
        ("Ticket Médio", "Sem dados no recorte selecionado", "", "Vendas ÷ PIs da base"),
        ("Campanhas", "0", None, "Cliente + Campanha"),
    ]),
])
def test_cinco_indicadores_preservam_valores_dinamicos_formatos_e_contextos(
    monkeypatch, valores, esperados,
):
    raiz = _indicadores(monkeypatch, **valores)
    assert len(_elementos(raiz, "atg-kpi-hero")) == 1
    kpis = _elementos(raiz, "atg-kpi-card")
    assert len(kpis) == 4
    assert _unico(raiz, "atg-kpi-row") in list(raiz)
    for kpi, (rotulo, valor, completo, contexto) in zip(kpis, esperados, strict=True):
        assert _texto(_unico(kpi, "atg-kpi-label")) == rotulo
        exibido = _unico(kpi, "atg-kpi-value")
        assert _texto(exibido) == valor
        if completo is not None:
            assert exibido.get("title") == completo
        assert _texto(_unico(kpi, "atg-kpi-caption")) == contexto
    assert _unico(kpis[-1], "atg-kpi-caption").get("title") == (
        "Combinações distintas de Cliente + Campanha (base Vendas)"
    )


@pytest.mark.parametrize("atual,anterior,variacao,vazio,numero,seta,estado,contexto", [
    (6_500_000, 5_000_000, 30, False, "30,0%", "▲", "alta",
     "R$ 6,50 Mi este ano · R$ 5,00 Mi no mesmo período de 2025"),
    (3_500_000, 5_000_000, -30, False, "30,0%", "▼", "queda",
     "R$ 3,50 Mi este ano · R$ 5,00 Mi no mesmo período de 2025"),
    (5_000_000, 5_000_000, 0, False, "0,0%", "", "neutro",
     "R$ 5,00 Mi este ano · R$ 5,00 Mi no mesmo período de 2025"),
    (6_500_000, None, None, False, "R$ 6,50 Mi", "", "neutro",
     "Sem comparativo disponível para este ano."),
    (6_500_000, 0, None, False, "—", "", "neutro",
     "R$ 6,50 Mi este ano · R$ 0,00 no mesmo período de 2025"),
    (0, None, None, True, "—", "", "neutro",
     "Sem dados no recorte selecionado."),
])
def test_hero_preserva_sinal_percentual_referencia_e_estados_existentes(
    monkeypatch, atual, anterior, variacao, vazio, numero, seta, estado, contexto,
):
    ytd = {"atual": atual, "anterior": anterior, "variacao_pct": variacao, "mes_limite": 9}
    valores = {"total": 0, "faturado": 0, "aberto": 0, "ticket": None, "campanhas": 0} if vazio else {}
    raiz = _indicadores(monkeypatch, ytd=ytd, vazio=vazio, **valores)
    hero = _unico(raiz, "atg-kpi-hero")
    assert f"atg-hero-{estado}" in hero.get("class").split()
    assert _texto(_unico(hero, "atg-eyebrow")) == "KPI Principal · YTD vs Ano Anterior"
    assert _texto(_unico(hero, "atg-hero-number")) == numero
    assert _texto(_unico(hero, "atg-hero-caption")) == contexto
    sinais = _elementos(hero, "atg-hero-arrow")
    if seta:
        assert len(sinais) == 1
        assert _texto(sinais[0]) == seta
        triangulo = sinais[0].find("svg")
        assert triangulo is not None
        assert triangulo.get("fill") == "currentColor"
        assert triangulo.get("aria-hidden") == "true"
        assert triangulo.get("focusable") == "false"
        assert triangulo.get("width") == triangulo.get("height") == "22"
    else:
        assert sinais == []


def test_quatro_icones_sao_vetoriais_lineares_distintos_e_decorativos(monkeypatch):
    raiz = _indicadores(monkeypatch)
    kpis = _elementos(raiz, "atg-kpi-card")
    desenhos = []
    for kpi in kpis:
        icone = _unico(kpi, "atg-kpi-icon")
        assert len(list(icone)) == 1
        svg = list(icone)[0]
        assert svg.tag == "svg"
        assert svg.get("width") == svg.get("height") == "22"
        assert svg.get("viewBox") == "0 0 24 24"
        assert svg.get("fill") == "none"
        assert svg.get("stroke") == "currentColor"
        assert svg.get("stroke-width") == "1.9"
        assert svg.get("stroke-linecap") == svg.get("stroke-linejoin") == "round"
        assert svg.get("aria-hidden") == "true" and svg.get("focusable") == "false"
        desenhos.append(tuple((elemento.tag, tuple(sorted(elemento.attrib.items())))
                              for elemento in list(svg)))
    assert len(set(desenhos)) == 4
    assert list(_unico(kpis[1], "atg-kpi-icon"))[0].find("rect") is not None
    assert list(_unico(kpis[2], "atg-kpi-icon"))[0].find("circle") is not None


def test_cabecalho_tem_titulo_unico_e_preserva_controles_e_atualizacao(monkeypatch):
    app, _, _, leituras, _ = _entrada(monkeypatch, "Performance Comercial")
    assert not app.exception
    titulos = []
    for elemento in app.main.markdown:
        if 'class="atg-h1"' in elemento.value:
            titulos.append(_texto(ET.fromstring(elemento.value)))
    assert titulos == ["Performance Comercial"]
    assert app.button(key="masthead_tema").proto.disabled
    assert leituras == {"vendas": 1, "metas": 0}
    app.button(key="masthead_refresh").click().run(timeout=20)
    assert not app.exception
    assert leituras == {"vendas": 2, "metas": 0}
    assert app.toast[0].value == "Dados atualizados"


def _rankings(app):
    return [elemento.value for elemento in app.markdown
            if 'class="atg-card atg-rank"' in elemento.value]


def _linhas_ranking(html):
    raiz = ET.fromstring(html)
    return [
        (_texto(_unico(linha, "atg-rank-name")),
         _unico(linha, "atg-rank-value").get("title"),
         _texto(_unico(linha, "atg-rank-pct")),
         _unico(linha, "atg-rank-bar").get("style"))
        for linha in _elementos(raiz, "atg-rank-row")
    ]


def test_tres_rankings_preservam_numeros_ordem_barras_e_limpeza_dos_filtros():
    app, vendas = _pagina()
    assert not app.exception
    antes = _rankings(app)
    assert [_texto(_unico(ET.fromstring(html), "atg-rank-title")) for html in antes] == [
        "Top 5 Grupos", "Top 5 Agências", "Top 5 Clientes",
    ]
    assert [_linhas_ranking(html) for html in antes] == [
        [("FORA", "R$ 4.000,00", "57%", "width:100%"),
         ("H", "R$ 2.100,00", "30%", "width:52%"),
         ("G", "R$ 920,00", "13%", "width:23%")],
        [("TESTE", "R$ 7.020,00", "100%", "width:100%")],
        [("CLIENTE H", "R$ 6.100,00", "87%", "width:100%"),
         ("CLIENTE G", "R$ 920,00", "13%", "width:15%")],
    ]
    vendas_antes = vendas.copy(deep=True)
    for grupo in ("FORA", "H"):
        app.checkbox(key=f"perf_fc_{COL_GRUPO}_r_{grupo}").uncheck().run(timeout=20)
        assert not app.exception
        assert _rankings(app) == antes  # O rascunho não é um filtro aplicado.
    app.button(key=f"perf_fc_{COL_GRUPO}_aplicar").click().run(timeout=20)
    assert not app.exception
    assert app.session_state[f"perf_fc_{COL_GRUPO}_aplicado"] == ["G"]
    assert [_linhas_ranking(html) for html in _rankings(app)] == [
        [("G", "R$ 920,00", "100%", "width:100%")],
        [("TESTE", "R$ 920,00", "100%", "width:100%")],
        [("CLIENTE G", "R$ 920,00", "100%", "width:100%")],
    ]
    app.button(key="perf_limpar_filtros").click().run(timeout=20)
    assert not app.exception
    assert _rankings(app) == antes  # Inclui textos, valores, selos e estilos internos.
    pd.testing.assert_frame_equal(vendas, vendas_antes)


def test_tres_ctas_dos_rankings_preservam_destinos_conteudo_e_recorte():
    for chave, destino in (("perf_ver_veiculos", "Analítico Veículos"),
                           ("perf_ver_agencias", "Analítico Comercial"),
                           ("perf_ver_clientes", "Analítico Comercial")):
        app, _ = _pagina(grupos=["G"])
        assert not app.exception
        antes = _rankings(app)
        app.button(key=chave).click().run(timeout=20)
        assert not app.exception
        assert app.session_state["nav_pagina"] == destino
        assert app.session_state[f"perf_fc_{COL_GRUPO}_aplicado"] == ["G"]
        assert app.session_state["perf_valor"] == "Valor Líquido"
        assert app.session_state["perf_mes"] == "Mês (Veiculação)"
        assert _rankings(app) == antes
