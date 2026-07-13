"""Página 1: Performance Comercial — visão executiva.

Cards: Vendas (com decomposição Faturado), YTD vs Ano Anterior, Ticket
Médio, Quantidade de Campanhas, Em Aberto.
Gráficos: evolução mensal das Vendas (comparativa) e evolução do Ticket
Médio. Rankings: Top 5 Veículos (Grupo+Veículo), Agências e Clientes.
Filtros: Ano e Grupo (filtros finos ficam nas páginas analíticas).

Toda métrica vem de metrics.py; esta página só filtra, formata e exibe.
Regra de indicadores vigente: Vendas / Faturado / Em Aberto (2026-07-09),
com Em Aberto = Vendas − Faturado.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.components import cards, charts, filters
from src.data import metrics
from src.data.cleaning import COL_AGENCIA, COL_CLIENTE, COL_GRUPO, COL_VEICULO

_CHAVE = "perf"


def render(df: pd.DataFrame) -> None:
    # ------------------------------------------------------------- filtros
    with st.container():
        col_ano, col_grupo = st.columns([1, 3])
        with col_ano:
            ano = filters.selecionar_ano(df, _CHAVE)
        with col_grupo:
            df_dim = filters.filtro_multiplo(df, COL_GRUPO, "Grupo", _CHAVE)
        valor, criterio_mes = filters.selecionar_toggles(_CHAVE)

    # df_dim: filtros de dimensão, SEM corte de ano (comparativos precisam
    # do ano anterior). df_ano: recorte do ano para cards e rankings.
    df_ano = filters.recorte_do_ano(df_dim, ano, criterio_mes)

    # --------------------------------------------------------------- cards
    # Ordem por afinidade (v0.5 Sprint 1): YTD (KPI de destaque) ->
    # financeiros (Vendas, Em Aberto) -> operacionais (Ticket, Campanhas).
    # Mesma grade, mesma largura, mesmo alinhamento dos 5 cards.
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        cards.card_ytd(
            "YTD vs Ano Anterior",
            metrics.ytd(df_dim, ano, valor, criterio_mes),
            ano,
            sem_dados=df_ano.empty,
        )
    with c2:
        detalhado = metrics.vendas_detalhado(df_ano, valor)
        cards.card_moeda(
            "Vendas",
            detalhado["total"],
            legenda=(
                "sendo "
                f"{cards.formatar_moeda_executiva(detalhado['faturado'])} "
                "já faturado"
            ),
        )
    with c3:
        cards.card_moeda(
            "Em Aberto",
            metrics.em_aberto(df_ano, valor),
            legenda="vendido, ainda não faturado",
        )
    with c4:
        cards.card_moeda("Ticket Médio", metrics.ticket_medio(df_ano, valor))
    with c5:
        cards.card_numero(
            "Campanhas",
            metrics.quantidade_campanhas(df_ano),
            legenda="Cliente + Campanha distintos (base Vendas)",
        )

    st.divider()

    # ------------------------------------------------------------ gráficos
    charts.grafico_evolucao_comparativa(
        metrics.comparativo_mensal(df_dim, ano, valor, criterio_mes),
        ano,
        "Evolução das Vendas",
    )
    charts.grafico_linha_mensal(
        metrics.evolucao_mensal_ticket_medio(df_dim, ano, valor, criterio_mes),
        "Evolução mensal do Ticket Médio",
    )

    st.divider()

    # ------------------------------------------------------------ rankings
    r1, r2, r3 = st.columns(3)
    with r1:
        top_veiculos = metrics.agregado_por_grupo_veiculo(df_ano, valor).copy()
        if not top_veiculos.empty:
            top_veiculos["rotulo"] = (
                top_veiculos[COL_GRUPO]
                + filters.SEPARADOR_PAR
                + top_veiculos[COL_VEICULO]
            )
            coluna_ref = (
                "vendas_liquido" if valor == "liquido" else "vendas_bruto"
            )
            charts.grafico_barra_horizontal(
                top_veiculos, "rotulo", coluna_ref, "Top 5 Veículos", top_n=5
            )
        else:
            st.info(cards.SEM_DADOS)
    with r2:
        charts.grafico_barra_horizontal(
            metrics.agregado_por_dimensao(df_ano, COL_AGENCIA, valor),
            COL_AGENCIA,
            "valor",
            "Top 5 Agências",
            top_n=5,
        )
    with r3:
        charts.grafico_barra_horizontal(
            metrics.agregado_por_dimensao(df_ano, COL_CLIENTE, valor),
            COL_CLIENTE,
            "valor",
            "Top 5 Clientes",
            top_n=5,
        )
