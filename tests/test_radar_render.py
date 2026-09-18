"""Renderização e regressão da Performance, sem conexão ou autenticação fictícia."""

import subprocess
from dataclasses import replace

import pytest
from streamlit.testing.v1 import AppTest

from src.components import cards
from tests.test_radar import avaliar, frame, linha, recorde


@pytest.mark.parametrize("status,texto", [
    ("silencio", "Nenhuma mudança"),
    ("dados_insuficientes", "Histórico insuficiente"),
    ("dados_desatualizados", "Dados desatualizados"),
])
def test_render_estados_sem_insights(monkeypatch, status, texto):
    estado = replace(avaliar(frame()), status=status)
    captions, html = [], []
    monkeypatch.setattr(cards.st, "caption", captions.append)
    monkeypatch.setattr(cards.st, "markdown", lambda value, **kwargs: html.append(value))
    cards.render_radar(estado)
    assert any(texto in c for c in captions)
    assert len(html) == 1
    assert 'class="atg-radar-title">Radar Executivo' in html[0]
    assert 'class="atg-radar-item"' not in html[0]


def test_render_um_insight_referencia_cta_e_escape(monkeypatch):
    estado = avaliar(frame(linha("2025-01-01", 100, "<Grupo>"), linha("2026-01-01", 120, "<Grupo>")))
    html = []
    monkeypatch.setattr(cards.st, "caption", lambda value: None)
    monkeypatch.setattr(cards.st, "markdown", lambda value, **kwargs: html.append(value))
    cards.render_radar(estado)
    assert html[1].count('class="atg-radar-item"') == 1
    assert "&lt;GRUPO&gt;" in html[1]
    assert "01/2025–09/2025" in html[1]
    assert "Acompanhe este parceiro." in html[1]
    assert 'class="atg-radar atg-radar-single"' in html[1]
    classes = ["atg-radar-category", "atg-radar-headline", "atg-radar-context", "atg-radar-cta"]
    assert [html[1].index(c) for c in classes] == sorted(html[1].index(c) for c in classes)
    assert "CRESCIMENTO · &lt;GRUPO&gt;" in html[1]
    assert "+20,0% vs. mesmo período de 2025" in html[1]
    assert "R$ 120,00 em 2026 · R$ 100,00 em 2025" in html[1]
    assert "<strong>+20,0% vs. mesmo período de 2025</strong>" in html[1]
    assert "<em>Acompanhe este parceiro.</em>" in html[1]


@pytest.mark.parametrize("ano,manchete", [(2025, "Sem vendas em 2025"),
                                         (2026, "Sem vendas em 2026")])
def test_queda_zero_copy_dinamica(monkeypatch, ano, manchete):
    estado = avaliar(frame(linha(f"{ano-1}-01-01", 117570, "Parceiro"),
                           linha(f"{ano}-01-01", 0, "Parceiro")), ano)
    html = []
    monkeypatch.setattr(cards.st, "caption", lambda value: None)
    monkeypatch.setattr(cards.st, "markdown", lambda value, **kwargs: html.append(value))
    cards.render_radar(estado)
    assert "QUEDA · PARCEIRO" in html[1]
    assert manchete in html[1]
    assert f"R$ 117,57 mil no mesmo período de {ano-1}" in html[1]
    assert "Verifique este parceiro." in html[1]
    assert "-100,0%" not in html[1]


def test_destaque_manchete_mes_e_referencia(monkeypatch):
    estado = avaliar(recorde())
    html = []
    monkeypatch.setattr(cards.st, "caption", lambda value: None)
    monkeypatch.setattr(cards.st, "markdown", lambda value, **kwargs: html.append(value))
    cards.render_radar(estado)
    assert "DESTAQUE · AGOSTO" in html[1]
    assert "Novo recorde mensal: R$ 120,00" in html[1]
    assert "20,0% acima do recorde anterior de R$ 100,00" in html[1]
    assert "08/2025–07/2026" in html[1]
    assert "Acompanhe esta tendência." in html[1]


def test_sufixo_mais_removido_apenas_do_cabecalho(monkeypatch):
    estado = avaliar(frame(linha("2025-01-01", 100, "CARREGA +"),
                           linha("2026-01-01", 120, "CARREGA +")))
    html = []
    monkeypatch.setattr(cards.st, "caption", lambda value: None)
    monkeypatch.setattr(cards.st, "markdown", lambda value, **kwargs: html.append(value))
    cards.render_radar(estado)
    assert 'class="atg-radar-category">CRESCIMENTO · CARREGA</div>' in html[1]
    assert "+20,0% vs. mesmo período de 2025" in html[1]
    assert estado.insights[0].entidade == "CARREGA +"


def test_multiplos_insights_preservam_ordem_sem_estilo_single(monkeypatch):
    dados = frame(linha("2025-01-01", 100, "Queda"), linha("2026-01-01", 80, "Queda"),
                  linha("2025-01-01", 100, "Crescimento"), linha("2026-01-01", 120, "Crescimento"))
    html = []
    monkeypatch.setattr(cards.st, "caption", lambda value: None)
    monkeypatch.setattr(cards.st, "markdown", lambda value, **kwargs: html.append(value))
    cards.render_radar(avaliar(dados))
    assert html[1].count('class="atg-radar-item"') == 2
    assert "atg-radar-single" not in html[1]
    assert 'class="atg-radar atg-radar-two"' in html[1]
    assert html[1].index("QUEDA") < html[1].index("CRESCIMENTO")


def test_render_nativo_sem_botoes_ou_navegacao():
    app = AppTest.from_string('''
import datetime as dt
from src.components.cards import render_radar
from tests.test_radar import avaliar, frame, linha
render_radar(avaliar(frame(linha("2025-01-01",100),linha("2026-01-01",120)),
                      sincronizado_em=dt.datetime(2026,9,18,12,30)))
''').run()
    assert not app.exception
    assert not app.button
    captions = [c.value for c in app.caption]
    assert "Última sincronização com a fonte: 18/09/2026 12:30" in captions
    assert any("Sem comparação disponível: Destaque" in c for c in captions)
    assert any("Valor Líquido" in m.value and "Veiculação" in m.value for m in app.markdown)
    assert all("dados atualizados" not in c.lower() for c in captions)


@pytest.mark.parametrize("valor", ["Valor Líquido", "Valor Bruto"])
@pytest.mark.parametrize("mes", ["Mês (Veiculação)", "Mês (Ganho)"])
def test_regressao_performance_contra_codigo_baseline(valor, mes):
    """Mesmo fixture, widgets, KPIs e gráficos no código db9bb09 e no atual."""
    baseline = subprocess.run(
        ["git", "show", "db9bb09:pages_content/performance_comercial.py"],
        check=True, capture_output=True, text=True,
    ).stdout
    setup = f'''
import streamlit as st
from tests.test_radar import recorde
st.session_state["perf_ano"] = 2026
st.session_state["perf_valor"] = {valor!r}
st.session_state["perf_mes"] = {mes!r}
'''
    antes = AppTest.from_string(setup + f'\nexec({baseline!r})\nrender(recorde())\n').run(timeout=20)
    depois = AppTest.from_string(setup + '''
import datetime as dt
from pages_content.performance_comercial import render
render(recorde(), sincronizado_em=dt.datetime(2026,9,18,12,30))
''').run(timeout=20)
    assert not antes.exception
    assert not depois.exception
    def kpis_rankings(app):
        return [m.value for m in app.markdown if 'class="atg-kpi-row"' in m.value
                or 'class="atg-card atg-rank"' in m.value]
    assert len(kpis_rankings(antes)) == 4
    assert kpis_rankings(antes) == kpis_rankings(depois)
    assert [p.proto.spec for p in antes.get("plotly_chart")] == [
        p.proto.spec for p in depois.get("plotly_chart")
    ]
    assert [(b.label, b.disabled) for b in antes.button] == [
        (b.label, b.disabled) for b in depois.button
    ]
    assert any('class="atg-radar-title">Radar Executivo' in m.value for m in depois.markdown)
    assert "Última sincronização com a fonte: 18/09/2026 12:30" in [c.value for c in depois.caption]
