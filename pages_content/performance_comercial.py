"""Página 1: Performance Comercial — Sprint 2B (visual executivo premium).

Ordem vertical do Wireframe Executivo (doc 09 §6): filtros -> KPIs (Hero
YTD + 4 secundários) -> Insights -> Gráfico Hero (abas Vendas / Ticket
Médio) -> Rankings Top 5 com badge de tendência.

Nada é calculado aqui: métricas de metrics.py; esta página filtra,
formata e exibe. Nomenclatura oficial v0.3+ (adendo C1-C3 do doc 09).
Os toggles Líquido/Bruto e Ganho/Veiculação são renderizados no cabeçalho
do Gráfico Hero (posição do mockup), mas o ESTADO é único da página —
todos os blocos monetários reagem juntos, como sempre (toggles_do_estado).
"""

from __future__ import annotations

import datetime as _dt
from typing import Callable

import pandas as pd
import streamlit as st

from src.components import cards, charts, filters, metas_charts
from src.data import metas, metrics, radar
from src.data.cleaning import COL_AGENCIA, COL_CLIENTE, COL_GRUPO, COL_VEICULO
from src.data.metas_schema import ErroDeMetas

_CHAVE = "perf"

# A troca visual acompanha a aba no frontend, sem rerun dos KPIs/Radar.
# Os controles originais mantêm estado; os espelhos são nativos e desabilitados.
_CONTROLES_META_CSS = """<style>
[data-testid="stLayoutWrapper"]:has(> :is(
    .st-key-performance_grupo_meta, .st-key-performance_toggles_meta)) {
    display: none;
}
:root:has(.st-key-performance_evolucao_tab [role="tab"][data-key="2"][aria-selected="true"])
[data-testid="stLayoutWrapper"]:has(> :is(
    .st-key-performance_grupo_original, .st-key-performance_toggles_original)) {
    display: none;
}
:root:has(.st-key-performance_evolucao_tab [role="tab"][data-key="2"][aria-selected="true"])
[data-testid="stLayoutWrapper"]:has(> :is(
    .st-key-performance_grupo_meta, .st-key-performance_toggles_meta)) {
    display: flex;
}
.st-key-performance_meta_grupo button:disabled,
.st-key-performance_meta_grupo button:disabled:hover {
    color: #8B93A1;
    background: transparent;
    cursor: not-allowed;
}
</style>"""


def _navegar(destino: str) -> None:
    """Navegação cruzada (2B): troca a página ativa da sidebar."""
    st.session_state["nav_pagina"] = destino


def _linhas_ranking_dimensao(
    df_ano: pd.DataFrame, coluna: str, valor: str, tendencias: dict
) -> list[dict]:
    agg = metrics.agregado_por_dimensao(df_ano, coluna, valor)
    if agg.empty:
        return []
    total = float(agg["valor"].sum()) or 1.0
    return [
        {
            "nome": linha[coluna],
            "valor": float(linha["valor"]),
            "pct": float(linha["valor"]) / total * 100.0,
            "tendencia": tendencias.get(linha[coluna]),
        }
        for _, linha in agg.head(5).iterrows()
    ]


def _render_meta(
    df: pd.DataFrame, ano: int, carregar_metas: Callable[[], pd.DataFrame] | None,
) -> None:
    st.caption(
        "Meta · Valor Líquido · Mês de Veiculação · Consolidado AdTarget"
    )
    if carregar_metas is None:
        st.info("A fonte METAS não está disponível nesta visualização.")
    else:
        try:
            metas_df = carregar_metas()
            resultado = metas.avaliar_metas(df, metas_df, ano)
            pulso = metas.avaliar_pulso(
                df, metas_df, ano, data_referencia=resultado.data_referencia,
            )
        except ErroDeMetas:
            st.error(
                "Não foi possível carregar ou validar a aba METAS. "
                "Verifique a estrutura e o acesso à fonte. "
                "Vendas, Ticket Médio e os demais indicadores continuam disponíveis."
            )
        else:
            if resultado.estado == "sem_metas":
                st.info(f"Não há metas cadastradas para {ano}.")
            else:
                st.plotly_chart(
                    metas_charts.evolucao_performance_meta(resultado, pulso),
                    width="stretch", key="perf_meta",
                    config={"displayModeBar": False, "responsive": True},
                )
    st.caption("Ver análise completa em Metas e Resultados, na navegação lateral.")


@st.fragment
def _abas_evolucao(
    df: pd.DataFrame, df_dim: pd.DataFrame, ano: int, valor: str,
    criterio_mes: str, mes_limite: int | None,
    carregar_metas: Callable[[], pd.DataFrame] | None,
) -> None:
    # A troca de aba reexecuta somente os gráficos, preservando o restante
    # da Performance. Os controles permanecem fora deste fragmento.
    aba_vendas, aba_ticket, aba_meta = st.tabs(
        ["Vendas", "Ticket Médio", "Meta"],
        key="performance_evolucao_tab", on_change="rerun",
    )
    with aba_vendas:
        charts.grafico_hero_vendas(
            metrics.comparativo_mensal(df_dim, ano, valor, criterio_mes),
            ano,
            mes_limite,
        )
    with aba_ticket:
        charts.grafico_hero_ticket(
            metrics.evolucao_mensal_ticket_medio(
                df_dim, ano, valor, criterio_mes
            ),
            ano,
            mes_limite,
        )
    if aba_meta.open:
        with aba_meta:
            _render_meta(df, ano, carregar_metas)


def render(
    df: pd.DataFrame, sincronizado_em: _dt.datetime | None = None, *,
    carregar_metas: Callable[[], pd.DataFrame] | None = None,
) -> None:
    agora = _dt.datetime.now()
    hoje = agora.date()
    st.html(_CONTROLES_META_CSS)

    # ---------------------------------------------------- barra de filtros
    with st.container(
        key="design_performance_filters", horizontal=True,
        vertical_alignment="center", gap="medium",
    ):
        with st.container(key="design_performance_year", width="content"):
            ano = filters.selecionar_ano(df, _CHAVE)
        with st.container(key="design_performance_group", width=260):
            with st.container(key="performance_grupo_original", border=False, gap=None):
                df_dim = filters.filtro_compacto(df, COL_GRUPO, "Grupo", _CHAVE, "grupos")
            with st.container(key="performance_grupo_meta", border=False, gap=None):
                with st.popover(
                    "Grupo · Consolidado AdTarget", width="stretch", disabled=True,
                    key="performance_meta_grupo",
                ):
                    pass
        with st.container(key="design_performance_clear", width="content"):
            filters.botao_limpar_filtros(_CHAVE)

    # Estado global dos toggles (widgets renderizados no Gráfico Hero)
    valor, criterio_mes = filters.toggles_do_estado(_CHAVE)
    df_ano = filters.recorte_do_ano(df_dim, ano, criterio_mes)

    # ------------------------------------------------------- KPIs (2B.5)
    cards.linha_kpis(
        metrics.ytd(df_dim, ano, valor, criterio_mes),
        ano,
        df_ano.empty,
        metrics.vendas_detalhado(df_ano, valor),
        metrics.em_aberto(df_ano, valor),
        metrics.ticket_medio(df_ano, valor),
        metrics.quantidade_campanhas(df_ano),
    )

    # --------------------------------------------------- Radar Executivo
    cards.render_radar(
        radar.avaliar_radar(
            df_dim, ano, agora=agora, valor=valor, criterio_mes=criterio_mes,
            sincronizado_em=sincronizado_em,
        )
    )

    # ----------------------------------------------- Gráfico Hero (2B.7)
    with st.container(border=True):
        col_titulo, col_toggles = st.columns([1.2, 2], vertical_alignment="center")
        with col_titulo:
            st.markdown(
                '<div class="atg-rank-title" style="margin:0">Evolução</div>',
                unsafe_allow_html=True,
            )
        with col_toggles:
            # Controles secundários (peso menor que as abas — doc 09 §6.4)
            with st.container(key="performance_toggles_original", border=False, gap=None):
                valor, criterio_mes = filters.selecionar_toggles(_CHAVE)
            with st.container(key="performance_toggles_meta", border=False, gap=None):
                col_valor, col_mes = st.columns(2)
                with col_valor:
                    st.segmented_control(
                        "Métrica de valor", ["Valor Líquido", "Valor Bruto"],
                        default="Valor Líquido", disabled=True,
                        key="performance_meta_valor",
                    )
                with col_mes:
                    st.segmented_control(
                        "Critério de mês", ["Mês (Ganho)", "Mês (Veiculação)"],
                        default="Mês (Veiculação)", disabled=True,
                        key="performance_meta_mes",
                    )

        mes_limite = hoje.month if ano == hoje.year else None
        _abas_evolucao(df, df_dim, ano, valor, criterio_mes, mes_limite, carregar_metas)

    # -------------------------------------------------- Rankings (2B.8)
    tend_veic = metrics.tendencia_grupo_veiculo(df_dim, ano, valor, criterio_mes)
    tend_agencia = metrics.tendencia_por_dimensao(
        df_dim, COL_AGENCIA, ano, valor, criterio_mes
    )
    tend_cliente = metrics.tendencia_por_dimensao(
        df_dim, COL_CLIENTE, ano, valor, criterio_mes
    )

    agg_veic = metrics.agregado_por_grupo_veiculo(df_ano, valor)
    coluna_ref = "vendas_liquido" if valor == "liquido" else "vendas_bruto"
    linhas_veic: list[dict] = []
    if not agg_veic.empty:
        total_v = float(agg_veic[coluna_ref].sum()) or 1.0
        for _, linha in agg_veic.head(5).iterrows():
            par = (linha[COL_GRUPO], linha[COL_VEICULO])
            linhas_veic.append({
                "nome": f"{linha[COL_GRUPO]}{filters.SEPARADOR_PAR}{linha[COL_VEICULO]}",
                "valor": float(linha[coluna_ref]),
                "pct": float(linha[coluna_ref]) / total_v * 100.0,
                "tendencia": tend_veic.get(par),
            })

    with st.container(key="design_performance_rankings", border=False, gap=None):
        r1, r2, r3 = st.columns(3)
    with r1:
        cards.bloco_ranking("Top 5 Veículos", linhas_veic)
        st.button(
            "ver tudo →", key=f"{_CHAVE}_ver_veiculos",
            on_click=_navegar, args=("Analítico Veículos",), type="tertiary",
        )
    with r2:
        cards.bloco_ranking(
            "Top 5 Agências",
            _linhas_ranking_dimensao(df_ano, COL_AGENCIA, valor, tend_agencia),
        )
        st.button(
            "ver tudo →", key=f"{_CHAVE}_ver_agencias",
            on_click=_navegar, args=("Analítico Comercial",), type="tertiary",
        )
    with r3:
        cards.bloco_ranking(
            "Top 5 Clientes",
            _linhas_ranking_dimensao(df_ano, COL_CLIENTE, valor, tend_cliente),
        )
        st.button(
            "ver tudo →", key=f"{_CHAVE}_ver_clientes",
            on_click=_navegar, args=("Analítico Comercial",), type="tertiary",
        )
