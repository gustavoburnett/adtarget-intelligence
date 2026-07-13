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

import pandas as pd
import streamlit as st

from src.components import cards, charts, filters
from src.data import metrics
from src.data.cleaning import COL_AGENCIA, COL_CLIENTE, COL_GRUPO, COL_VEICULO

_CHAVE = "perf"


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


def render(df: pd.DataFrame) -> None:
    hoje = _dt.date.today()

    # ---------------------------------------------------- barra de filtros
    col_ano, col_grupo, col_limpar = st.columns(
        [2.2, 2.2, 1], vertical_alignment="bottom"
    )
    with col_ano:
        ano = filters.selecionar_ano(df, _CHAVE)
    with col_grupo:
        df_dim = filters.filtro_grupo_recolhido(df, _CHAVE)
    with col_limpar:
        filters.botao_limpar_grupos(df, _CHAVE)

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

    # --------------------------------------------------- Insights (2B.6)
    cards.capsulas_insights(
        metrics.destaques_do_recorte(df_dim, ano, valor, criterio_mes)
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
            valor, criterio_mes = filters.selecionar_toggles(_CHAVE)

        mes_limite = hoje.month if ano == hoje.year else None
        aba_vendas, aba_ticket = st.tabs(["Vendas", "Ticket Médio"])
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
