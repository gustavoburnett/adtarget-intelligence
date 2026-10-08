"""Design 1E: apresentação e regressão contra o checkpoint 1D congelado.

Fixtures sintéticas e offline; a reconciliação comercial usa somente a fonte
real na auditoria separada. Dimensões e overflow são medidos no navegador.
"""

from copy import deepcopy
from functools import lru_cache
import subprocess
from types import ModuleType
import xml.etree.ElementTree as ET

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.components import cards
from src.data import cleaning, metrics
from tests.test_design_performance import _elementos, _rankings, _texto, _unico
from tests.test_performance_meta import (
    _entrada, _figuras, _isolamento, _pagina, _plano,
)


CHECKPOINT_1D = "86527ebd0823bfdc89db31730062a8cf4c02abf3"


@pytest.fixture(autouse=True)
def _relogio_e_cache(monkeypatch):
    yield from _isolamento.__wrapped__(monkeypatch)


@lru_cache
def _checkpoint():
    fonte = subprocess.run(
        ["git", "show", f"{CHECKPOINT_1D}:pages_content/performance_comercial.py"],
        check=True, capture_output=True, text=True,
    ).stdout
    modulo = ModuleType("performance_congelada_design_1d")
    exec(compile(fonte, f"<{CHECKPOINT_1D}:performance_comercial.py>", "exec"), modulo.__dict__)
    return modulo


def _render_checkpoint(vendas, plano):
    from pages_content import performance_comercial
    from tests.test_design_rankings import _checkpoint

    modulo = _checkpoint()
    modulo._dt = performance_comercial._dt
    modulo.render(vendas, carregar_metas=lambda: plano)


def _pagina_checkpoint(vendas, *, aba, valor, criterio, grupos):
    app = AppTest.from_function(_render_checkpoint, args=(vendas, _plano()))
    app.session_state["performance_evolucao_tab"] = aba
    app.session_state["perf_ano"] = 2026
    app.session_state["perf_valor"] = valor
    app.session_state["perf_mes"] = criterio
    if grupos is not None:
        app.session_state[f"perf_fc_{cleaning.COL_GRUPO}_aplicado"] = grupos
    return app.run(timeout=20)


def _hero_e_radar(app):
    return [elemento.value for elemento in app.markdown if any(
        marcador in elemento.value for marcador in (
            'class="atg-kpi-row"', 'class="atg-radar-header"', 'class="atg-radar ',
        )
    )]


@pytest.mark.parametrize("aba", ["Vendas", "Ticket Médio", "Meta"])
@pytest.mark.parametrize("valor,criterio,grupos", [
    ("Valor Líquido", "Mês (Veiculação)", None),
    ("Valor Bruto", "Mês (Veiculação)", ["G"]),
    ("Valor Líquido", "Mês (Ganho)", ["H"]),
    ("Valor Bruto", "Mês (Ganho)", []),
])
def test_design_1e_preserva_checkpoint_1d_fora_do_ranking_grupos(
    aba, valor, criterio, grupos,
):
    atual, vendas = _pagina(aba=aba, valor=valor, criterio=criterio, grupos=grupos)
    copia = vendas.copy(deep=True)
    congelada = _pagina_checkpoint(
        vendas, aba=aba, valor=valor, criterio=criterio, grupos=grupos,
    )
    assert not atual.exception and not congelada.exception
    assert _hero_e_radar(atual) == _hero_e_radar(congelada)
    # O render compartilhado tem o estilo 1E nos dois lados; a página
    # congelada garante igualdade integral dos registros e indicadores.
    assert _rankings(atual)[1:] == _rankings(congelada)[1:]
    assert _figuras(atual) == _figuras(congelada)
    assert [(b.key, b.label, b.disabled) for b in atual.button] == [
        (b.key, b.label, b.disabled) for b in congelada.button
    ]
    assert [t.label for t in atual.tabs] == [t.label for t in congelada.tabs]
    assert _texto(_unico(ET.fromstring(_rankings(atual)[0]), "atg-rank-title")) == "Top 5 Grupos"
    assert _texto(_unico(ET.fromstring(_rankings(congelada)[0]), "atg-rank-title")) == "Top 5 Veículos"
    pd.testing.assert_frame_equal(vendas, copia)


def _render_ranking(monkeypatch, linhas, titulo="Top 5 Grupos"):
    html = []
    copia = deepcopy(linhas)
    monkeypatch.setattr(cards.st, "markdown", lambda texto, **_: html.append(texto))
    cards.bloco_ranking(titulo, linhas)
    assert linhas == copia
    assert len(html) == 1
    return ET.fromstring(html[0])


@pytest.mark.parametrize("quantidade", range(7))
def test_ranking_renderiza_ate_cinco_posicoes_reais_sem_completar_lista(monkeypatch, quantidade):
    dados = [
        {"nome": f"GRUPO {n}", "valor": 100 - n, "pct": 20 - n, "tendencia": None}
        for n in range(quantidade)
    ]
    raiz = _render_ranking(monkeypatch, dados)
    assert _texto(_unico(raiz, "atg-rank-title")) == "Top 5 Grupos"
    titulo = _unico(raiz, "atg-rank-title")
    assert titulo.get("role") == "heading" and titulo.get("aria-level") == "3"
    linhas = _elementos(raiz, "atg-rank-row")
    assert len(linhas) == min(quantidade, 5)
    for posicao, (linha, esperado) in enumerate(zip(linhas, dados), start=1):
        assert linha.get("role") == "listitem"
        assert linha.get("aria-label") == f"Posição {posicao}"
        assert _texto(_unico(linha, "atg-rank-position")) == str(posicao)
        assert _texto(_unico(linha, "atg-rank-name")) == esperado["nome"]
    if quantidade:
        assert _unico(raiz, "atg-rank-list").get("role") == "list"
    else:
        assert cards.SEM_DADOS in _texto(raiz)
        assert not _elementos(raiz, "atg-rank-position")


def test_hierarquia_separa_nome_valor_de_barra_participacao_e_yoy(monkeypatch):
    raiz = _render_ranking(monkeypatch, [
        {"nome": "DISNEY", "valor": 150_000, "pct": 37.5, "tendencia": -25},
    ])
    linha = _unico(raiz, "atg-rank-row")
    topo = _unico(linha, "atg-rank-top")
    base = _unico(linha, "atg-rank-bottom")
    assert _unico(topo, "atg-rank-name").text == "DISNEY"
    assert _unico(topo, "atg-rank-value").get("title") == "R$ 150.000,00"
    assert _texto(_unico(topo, "atg-rank-value")) == "R$ 150,00 mil"
    assert _texto(_unico(base, "atg-rank-pct")) == "38%"
    assert _unico(base, "atg-rank-bar").get("style") == "width:100%"
    assert _texto(_unico(base, "atg-trend")) == "▼25%"
    assert not _elementos(topo, "atg-rank-pct")
    assert not _elementos(base, "atg-rank-value")


def test_barras_preservam_comparacao_relativa_e_denominador_de_participacao(monkeypatch):
    raiz = _render_ranking(monkeypatch, [
        {"nome": "A", "valor": 200, "pct": 20, "tendencia": -99},
        {"nome": "B", "valor": 100, "pct": 10, "tendencia": 9999},
        {"nome": "C", "valor": 1, "pct": .1, "tendencia": None},
    ])
    linhas = _elementos(raiz, "atg-rank-row")
    assert [_unico(l, "atg-rank-bar").get("style") for l in linhas] == [
        "width:100%", "width:50%", "width:2%",
    ]
    assert [_texto(_unico(l, "atg-rank-pct")) for l in linhas] == ["20%", "10%", "0%"]
    assert _unico(linhas[1], "atg-rank-barwrap").get("aria-label") == (
        "Participação no total: 10%; barra relativa ao maior valor do ranking"
    )


@pytest.mark.parametrize("variacao,texto,classe,acessivel", [
    (130.4, "▲130%", "alta", "Crescimento de 130% em relação ao ano anterior"),
    (-44.2, "▼44%", "queda", "Queda de 44% em relação ao ano anterior"),
    (0, "0%", "neutro", "Sem variação em relação ao ano anterior"),
    (None, "—", "neutro", "Sem base de comparação"),
])
def test_selo_yoy_preserva_sinal_e_diferencia_zero_de_sem_base(
    monkeypatch, variacao, texto, classe, acessivel,
):
    raiz = _render_ranking(monkeypatch, [
        {"nome": "G", "valor": 100, "pct": 100, "tendencia": variacao},
    ])
    selo = _unico(raiz, "atg-trend")
    assert _texto(selo) == texto
    assert classe in selo.get("class").split()
    assert selo.get("aria-label") == acessivel


def test_nomes_e_titulos_sao_escapados_e_nome_integral_permanece_acessivel(monkeypatch):
    nome = '<GRUPO "OFICIAL"> & NOME MUITO LONGO SEM CORTAR OS DADOS'
    titulo = 'Top 5 "Grupos" & <Oficiais>'
    raiz = _render_ranking(monkeypatch, [
        {"nome": nome, "valor": 100, "pct": 100, "tendencia": None},
    ], titulo)
    assert _texto(_unico(raiz, "atg-rank-title")) == titulo
    exibido = _unico(raiz, "atg-rank-name")
    assert _texto(exibido) == exibido.get("title") == exibido.get("aria-label") == nome
    assert raiz.find(".//GRUPO") is None


def test_cta_grupos_abre_destino_existente_com_vendas_consolidadas_por_grupo(monkeypatch):
    app, fonte, _, leituras = _entrada(monkeypatch)
    assert not app.exception
    app.button(key="perf_ver_veiculos").click().run(timeout=20)
    assert not app.exception
    assert app.session_state["nav_pagina"] == "Analítico Veículos"
    # Design 1H usa o título de seção fora do Plotly, sem duplicá-lo no gráfico.
    assert "Vendas por Grupo" in [titulo.value for titulo in app.subheader]
    figuras = _figuras(app)
    assert figuras[0]["layout"]["title"]["text"] == ""
    assert app.button_group(key="anvei_ano").value == 2026
    assert app.button_group(key="anvei_valor").value == "Valor Líquido"
    assert app.button_group(key="anvei_mes").value == "Mês (Veiculação)"
    base = cleaning.limpar_dataframe(fonte)
    recorte = base[base[cleaning.COL_MES_VEICULACAO_DATA].dt.year == 2026]
    esperado = metrics.agregado_por_dimensao(recorte, cleaning.COL_GRUPO, "liquido")
    assert figuras[0]["data"][0]["y"] == esperado[cleaning.COL_GRUPO].tolist()
    assert figuras[0]["data"][0]["x"] == pytest.approx(esperado["valor"].tolist())
    assert app.selectbox(key="anvei_drill").options == esperado[cleaning.COL_GRUPO].tolist()
    assert leituras == {"vendas": 1, "metas": 0}


def test_estilos_isolados_preservam_breakpoint_de_largura_util_e_conteudo_integral():
    from src.components.performance_styles import CSS_PERFORMANCE
    from src.components.ranking_styles import CSS_RANKING

    assert "container-name:atg-performance-rankings" in CSS_PERFORMANCE
    assert "@container atg-performance-rankings (width < 1200px)" in CSS_PERFORMANCE
    assert "grid-template-columns:minmax(0,1fr)" in CSS_PERFORMANCE
    assert ".st-key-design_performance_rankings" in CSS_RANKING
    assert "text-overflow:ellipsis" in CSS_RANKING
    assert "var(--atg-radius-card)" in CSS_RANKING
    assert "var(--atg-brand)" in CSS_RANKING
    assert ".atg-rank-value" in CSS_RANKING and ".atg-rank-pct" in CSS_RANKING
    # A responsividade troca os containers, sem esconder os indicadores.
    assert "display:none" not in CSS_RANKING.replace(" ", "")
    assert "@media(max-width:1200px)" not in CSS_RANKING.replace(" ", "")
