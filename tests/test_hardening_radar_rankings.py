"""Hardening: identidades e estados extremos, com dados somente sintéticos."""

from copy import deepcopy
import re
import xml.etree.ElementTree as ET

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pages_content.performance_comercial import _linhas_ranking_dimensao
from src.components import cards
from src.components.design_styles import CSS_SHELL
from src.components.design_tokens import COLOR
from src.components.metas_styles import CSS_METAS
from src.components.performance_styles import CSS_PERFORMANCE
from src.data.cleaning import COL_AGENCIA, COL_CLIENTE, COL_GRUPO
from src.data import radar
from tests.test_design_foundation import _luminancia
from tests.test_design_performance import _elementos, _texto, _unico
from tests.test_radar import avaliar, frame, linha
from tests.test_ranking_groups import _ranking


def _queda(estado):
    return next(i for i in estado.insights if i.tipo == "queda")


def _radar_html(monkeypatch, dados):
    html = []
    monkeypatch.setattr(cards.st, "markdown", lambda texto, **_: html.append(texto))
    monkeypatch.setattr(cards.st, "caption", lambda _: None)
    cards.render_radar(avaliar(dados))
    return html[1]


def test_alias_entre_anos_corrige_queda_sem_mutar_fonte_ou_valores():
    dados = frame(linha("2025-01-01", 100, "CARREGA +"),
                  linha("2026-01-01", 25, "CARREGA+"))
    original = dados.copy(deep=True)
    queda = _queda(avaliar(dados))
    assert (queda.entidade, queda.valor_atual, queda.valor_anterior) == ("CARREGA+", 25, 100)
    assert queda.variacao_pct == -75
    pd.testing.assert_frame_equal(dados, original)


def test_aliases_coexistentes_somam_cada_registro_uma_vez():
    dados = frame(linha("2025-01-01", 60, "CARREGA +"),
                  linha("2025-02-01", 40, "CARREGA+"),
                  linha("2026-01-01", 10, "CARREGA +"),
                  linha("2026-02-01", 15, "CARREGA+"))
    estado = avaliar(dados)
    assert len(estado.insights) == 1
    assert (_queda(estado).valor_atual, _queda(estado).valor_anterior) == (25, 100)


@pytest.mark.parametrize("distinto", ["CARREGA", "CARREGA  +", "CARREGA++"])
def test_nomes_nao_aprovados_permanecem_distintos(distinto):
    dados = frame(linha("2025-01-01", 100, "CARREGA +"),
                  linha("2026-01-01", 25, "CARREGA+"),
                  linha("2025-01-01", 100, distinto),
                  linha("2026-01-01", 150, distinto))
    estado = avaliar(dados)
    assert _queda(estado).valor_atual == 25
    assert next(i for i in estado.insights if i.tipo == "crescimento").entidade == distinto


def test_maior_queda_continua_dinamica_e_outros_grupos_nao_mudam():
    dados = frame(linha("2025-01-01", 100, "CARREGA +"),
                  linha("2026-01-01", 25, "CARREGA+"),
                  linha("2025-01-01", 100, "OUTRO"),
                  linha("2026-01-01", 20, "OUTRO"),
                  linha("2025-01-01", 100, "CRESCE"),
                  linha("2026-01-01", 150, "CRESCE"))
    estado = avaliar(dados)
    assert [(i.tipo, i.entidade, i.variacao_pct) for i in estado.insights] == [
        ("queda", "OUTRO", -80), ("crescimento", "CRESCE", 50),
    ]
    sem_alias = dados.loc[dados.GRUPO.isin(["OUTRO", "CRESCE"])]
    assert estado.insights == avaliar(sem_alias).insights


def test_alias_reutiliza_equivalencia_tambem_de_melodia():
    estado = avaliar(frame(linha("2025-01-01", 100, "RÁDIO MELODIA"),
                           linha("2026-01-01", 120, "MELODIA")))
    assert [(i.entidade, i.variacao_pct) for i in estado.insights] == [("MELODIA", 20)]


@pytest.mark.parametrize("grupos", [["CARREGA+"], ["CARREGA +"], ["CARREGA+", "CARREGA +"]])
def test_filtro_radar_recupera_alias_anterior_sem_ampliar_outros_grupos(grupos):
    dados = frame(linha("2025-01-01", 100, "CARREGA +"),
                  linha("2026-01-01", 25, "CARREGA+"),
                  linha("2026-01-01", 999, "CARREGA"))
    original = dados.copy(deep=True)
    recorte = radar.recorte_por_grupos(dados, grupos)
    assert len(recorte) == 2
    assert _queda(avaliar(recorte)).variacao_pct == -75
    assert radar.recorte_por_grupos(dados, []).empty
    pd.testing.assert_frame_equal(dados, original)


@pytest.mark.parametrize("grupo", ["CARREGA +", "CARREGA+"])
def test_integracao_filtro_preserva_kpis_literais_e_comparacao_radar_canonica(grupo):
    from tests.test_performance_meta import _render_pagina
    from src.data import metrics

    dados = frame(linha("2025-01-01", 100, "CARREGA +"),
                  linha("2026-01-01", 25, "CARREGA+"))
    original = dados.copy(deep=True)
    app = AppTest.from_function(_render_pagina, args=(dados, None, None))
    app.session_state["perf_ano"] = 2026
    app.session_state["perf_fc_GRUPO_aplicado"] = [grupo]
    app.run(timeout=20)
    assert not app.exception
    html = "\n".join(m.value for m in app.markdown)
    assert "QUEDA · CARREGA+" in html and "-75,0% vs." in html
    literal = dados.loc[(dados.GRUPO == grupo) & (dados.MES_VEICULACAO_DATA.dt.year == 2026)]
    kpi = next(m.value for m in app.markdown if 'class="atg-kpi-row"' in m.value)
    assert cards.formatar_moeda_executiva(metrics.vendas(literal)) in kpi
    pd.testing.assert_frame_equal(dados, original)


def test_vendas_futuras_nao_sao_descritas_como_ausencia_no_ano(monkeypatch):
    dados = frame(linha("2025-01-01", 100, "CARREGA +"),
                  linha("2026-11-01", 120, "CARREGA+"),
                  linha("2026-01-01", 100, "OUTRO"))
    assert _queda(avaliar(dados)).valor_atual == 0
    html = _radar_html(monkeypatch, dados)
    assert "Saldo de vendas zero em Jan–Set/2026" in html
    assert "Sem vendas" not in html


def test_saldo_zero_com_registros_nao_afirma_ausencia(monkeypatch):
    dados = frame(linha("2025-01-01", 100, "CARREGA +"),
                  linha("2026-01-01", 50, "CARREGA+"),
                  linha("2026-02-01", -50, "CARREGA +"))
    html = _radar_html(monkeypatch, dados)
    assert "QUEDA · CARREGA+" in html
    assert "Saldo de vendas zero em Jan–Set/2026" in html
    assert "Sem vendas" not in html


def test_queda_com_vendas_positivas_mostra_variacao_e_periodos(monkeypatch):
    html = _radar_html(monkeypatch, frame(linha("2025-01-01", 100, "CARREGA +"),
                                        linha("2026-01-01", 25, "CARREGA+")))
    assert "QUEDA · CARREGA+" in html
    assert "-75,0% vs. Jan–Set/2025" in html
    assert "R$ 25,00 em Jan–Set/2026 · R$ 100,00 em Jan–Set/2025" in html


@pytest.mark.parametrize("valores", [
    [200, 100, 1], [-100, -200, -400], [100, -200], [100, -100],
    [0], [100, 0], [100, -50], [1e12, 1e11], [100, -99.99],
])
@pytest.mark.parametrize("dimensao", [COL_GRUPO, COL_AGENCIA, COL_CLIENTE])
def test_rankings_preservam_valores_e_ordem_com_geometria_segura(monkeypatch, valores, dimensao):
    dados = frame(*[linha("2026-01-01", valor, f"G{n}") for n, valor in enumerate(valores)])
    dados[dimensao] = [f"G{n}" for n in range(len(valores))]
    original = dados.copy(deep=True)
    linhas = (_ranking(dados) if dimensao == COL_GRUPO
              else _linhas_ranking_dimensao(dados, dimensao, "liquido", {}))
    assert [item["valor"] for item in linhas] == sorted(valores, reverse=True)
    total = sum(valores)
    for item in linhas:
        assert item["pct"] == (pytest.approx(item["valor"] / total * 100) if total > 0 else None)
    copia = deepcopy(linhas)
    html = []
    monkeypatch.setattr(cards.st, "markdown", lambda texto, **_: html.append(texto))
    cards.bloco_ranking("Teste", linhas)
    rows = _elementos(ET.fromstring(html[0]), "atg-rank-row")
    for item, row in zip(linhas, rows, strict=True):
        largura = int(_unico(row, "atg-rank-bar").get("style").removeprefix("width:").removesuffix("%"))
        assert 0 <= largura <= 100
        if item["valor"] <= 0:
            assert largura == 0
        else:
            assert largura >= 2
        assert _unico(row, "atg-rank-value").get("title") == cards.formatar_moeda(item["valor"])
        if total <= 0:
            assert _texto(_unico(row, "atg-rank-pct")) == "—"
            assert "total de vendas zero ou negativo" in _unico(row, "atg-rank-pct").get("title")
        else:
            assert _texto(_unico(row, "atg-rank-pct")) == f"{item['pct']:.0f}%"
    assert linhas == copia
    pd.testing.assert_frame_equal(dados, original)


@pytest.mark.parametrize("css,seletor", [
    (CSS_PERFORMANCE, ".st-key-design_performance_header .atg-updated"),
    (CSS_METAS, ".st-key-design_metas_header .atg-updated"),
    (CSS_METAS, ".st-key-design_metas_content .atg-metas-footer"),
])
def test_metadados_usam_token_existente_com_contraste_na_superficie_da_pagina(css, seletor):
    regra = re.search(re.escape(seletor) + r"\s*\{([^}]+)\}", css).group(1)
    token = re.search(r"color:var\(--atg-([\w-]+)\)", regra).group(1)
    assert "background:var(--atg-surface-page)" in CSS_SHELL
    for superficie in ("surface-page", "surface-card"):
        luminosidades = sorted((_luminancia(COLOR[token]), _luminancia(COLOR[superficie])))
        assert (luminosidades[1] + .05) / (luminosidades[0] + .05) >= 4.5
