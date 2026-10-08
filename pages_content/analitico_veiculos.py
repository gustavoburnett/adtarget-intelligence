"""Página 3: Analítico Veículos.

Cards: Vendas do recorte, Ticket Médio, Veículos Ativos.
Gráficos: Vendas por Grupo (barra), drill-down Vendas por Veículo dentro
do grupo, rankings completos (Veículos, Agências, Clientes).
Ranking agregado por Grupo + Veículo com % do total.
Filtros: Ano, Grupo, Agência, Cliente.

Agregação SEMPRE por Grupo + Veículo (decisão 15). Métricas de metrics.py.
Regra de indicadores vigente: base Vendas (2026-07-09).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.components import cards, charts, filters
from src.components.kpi_icons import ICONES_KPI
from src.components.veiculos_tables import (
    configuracao_colunas_ranking, preparar_ranking_dimensao, preparar_ranking_veiculos,
)
from src.data import metrics
from src.data.cleaning import COL_AGENCIA, COL_CLIENTE, COL_GRUPO, COL_VEICULO

_CHAVE = "anvei"


def render(df: pd.DataFrame) -> None:
    # ------------------------------------------------------------- filtros
    with st.container(key="design_veiculos_filters"):
        with st.container(key="design_veiculos_filter_top"):
            col_ano, col_resto, col_limpar = st.columns(
                [1, 2.6, 0.7], vertical_alignment="bottom"
            )
        with col_ano, st.container(key="design_veiculos_year"):
            ano = filters.selecionar_ano(df, _CHAVE)
        with col_resto, st.container(key="design_veiculos_toggles"):
            valor, criterio_mes = filters.selecionar_toggles(_CHAVE)
        with col_limpar, st.container(key="design_veiculos_clear"):
            filters.botao_limpar_filtros(_CHAVE)
        with st.container(key="design_veiculos_filter_dimensions"):
            f1, f2, f3 = st.columns(3)
        with f1:
            df_dim = filters.filtro_compacto(
                df, COL_GRUPO, "Grupo", _CHAVE, "grupos"
            )
        with f2:
            df_dim = filters.filtro_compacto(
                df_dim, COL_AGENCIA, "Agência", _CHAVE, "agências", genero="a"
            )
        with f3:
            df_dim = filters.filtro_compacto(
                df_dim, COL_CLIENTE, "Cliente", _CHAVE, "clientes"
            )

    df_ano = filters.recorte_do_ano(df_dim, ano, criterio_mes)
    agregado = metrics.agregado_por_grupo_veiculo(df_ano, valor)
    coluna_ref = "vendas_liquido" if valor == "liquido" else "vendas_bruto"

    # --------------------------------------------------------------- cards
    with st.container(key="design_veiculos_kpis"):
        c1, c2, c3 = st.columns(3)
    with c1, st.container(key="design_veiculos_kpi_vendas"):
        st.markdown(f'<div class="atg-analytic-kpi-icon">{ICONES_KPI["vendas"]}</div>', unsafe_allow_html=True)
        cards.card_moeda("Vendas", metrics.vendas(df_ano, valor))
    with c2, st.container(key="design_veiculos_kpi_ticket"):
        st.markdown(f'<div class="atg-analytic-kpi-icon">{ICONES_KPI["ticket"]}</div>', unsafe_allow_html=True)
        cards.card_moeda(
            "Ticket Médio",
            metrics.ticket_medio(df_ano, valor),
            legenda="detalhe por veículo na tabela abaixo",
        )
    with c3, st.container(key="design_veiculos_kpi_ativos"):
        st.markdown(f'<div class="atg-analytic-kpi-icon">{ICONES_KPI["veiculos"]}</div>', unsafe_allow_html=True)
        cards.card_numero(
            "Veículos Ativos",
            metrics.veiculos_ativos(df_ano),
            legenda="pares Grupo+Veículo com PI na base Vendas",
        )

    # ------------------------------------------------------ vendas por grupo
    por_grupo = metrics.agregado_por_dimensao(df_ano, COL_GRUPO, valor)
    with st.container(key="design_veiculos_groups"):
        st.subheader("Vendas por Grupo")
        charts.grafico_barra_horizontal(
            por_grupo, COL_GRUPO, "valor", "Vendas por Grupo", estilo_veiculos=True,
        )

    # ------------------------------------------------ drill-down por veículo
    if not agregado.empty:
        grupos_com_dado = list(por_grupo[COL_GRUPO])
        with st.container(key="design_veiculos_detail"):
            grupo_escolhido = st.selectbox(
                "Detalhar veículos do grupo",
                grupos_com_dado,
                key=f"{_CHAVE}_drill",
            )
            detalhe = agregado[agregado[COL_GRUPO] == grupo_escolhido]
            st.subheader(f"Vendas por Veículo — {grupo_escolhido}")
            charts.grafico_barra_horizontal(
                detalhe, COL_VEICULO, coluna_ref,
                f"Vendas por Veículo — {grupo_escolhido}", estilo_veiculos=True,
            )

    # --------------------------------------------------- rankings completos
    with st.container(key="design_veiculos_rankings"):
        st.subheader("Rankings completos")
        aba_veic, aba_agencia, aba_cliente = st.tabs(["Veículos", "Agências", "Clientes"])
    with aba_veic:
        tabela_veiculos = preparar_ranking_veiculos(agregado)
        st.dataframe(
            tabela_veiculos, width="stretch", hide_index=True, row_height=40,
            column_config=configuracao_colunas_ranking(tabela_veiculos.data),
        )
        if agregado.empty:
            st.info(cards.SEM_DADOS)
    with aba_agencia:
        tabela_agencias = preparar_ranking_dimensao(
            metrics.agregado_por_dimensao(df_ano, COL_AGENCIA, valor).rename(
                columns={"valor": "Vendas", "qtd_pis": "Qtd PIs"}
            )
        )
        st.dataframe(
            tabela_agencias, width="stretch", hide_index=True, row_height=40,
            column_config=configuracao_colunas_ranking(tabela_agencias.data),
        )
    with aba_cliente:
        tabela_clientes = preparar_ranking_dimensao(
            metrics.agregado_por_dimensao(df_ano, COL_CLIENTE, valor).rename(
                columns={"valor": "Vendas", "qtd_pis": "Qtd PIs"}
            )
        )
        st.dataframe(
            tabela_clientes, width="stretch", hide_index=True, row_height=40,
            column_config=configuracao_colunas_ranking(tabela_clientes.data),
        )
