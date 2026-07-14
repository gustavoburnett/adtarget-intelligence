"""Página 3: Analítico Veículos.

Cards: Vendas do recorte, Ticket Médio, Veículos Ativos.
Gráficos: Vendas por Grupo (barra), drill-down Vendas por Veículo dentro
do grupo, rankings completos (Veículos, Agências, Clientes).
Tabela agregada por Grupo + Veículo com % do total.
Filtros: Ano, Grupo, Agência, Cliente.

Agregação SEMPRE por Grupo + Veículo (decisão 15). Métricas de metrics.py.
Regra de indicadores vigente: base Vendas (2026-07-09).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.components import cards, charts, filters
from src.data import metrics
from src.data.cleaning import COL_AGENCIA, COL_CLIENTE, COL_GRUPO, COL_VEICULO

_CHAVE = "anvei"


def _tabela_formatada(agregado: pd.DataFrame) -> pd.DataFrame:
    """Formata a tabela agregada para exibição (moeda pt-BR, % com vírgula)."""
    tabela = agregado.copy()
    tabela["Veículo"] = tabela[COL_GRUPO] + filters.SEPARADOR_PAR + tabela[COL_VEICULO]
    tabela["Vendas (Bruto)"] = tabela["vendas_bruto"].map(cards.formatar_moeda)
    tabela["Vendas (Líquido)"] = tabela["vendas_liquido"].map(cards.formatar_moeda)
    tabela["Ticket Médio"] = tabela["ticket_medio"].map(cards.formatar_moeda)
    tabela["Qtd PIs"] = tabela["qtd_pis"]
    tabela["% do Total"] = tabela["pct_do_total"].map(
        lambda v: f"{v:.1f}".replace(".", ",") + "%"
    )
    return tabela[
        ["Veículo", "Vendas (Bruto)", "Vendas (Líquido)",
         "Ticket Médio", "Qtd PIs", "% do Total"]
    ]


def render(df: pd.DataFrame) -> None:
    # ------------------------------------------------------------- filtros
    with st.container():
        col_ano, col_resto = st.columns([1, 3])
        with col_ano:
            ano = filters.selecionar_ano(df, _CHAVE)
        with col_resto:
            valor, criterio_mes = filters.selecionar_toggles(_CHAVE)
        df_dim = filters.filtro_multiplo(df, COL_GRUPO, "Grupo", _CHAVE)
        c1, c2 = st.columns(2)
        with c1:
            df_dim = filters.filtro_multiplo(df_dim, COL_AGENCIA, "Agência", _CHAVE)
        with c2:
            df_dim = filters.filtro_multiplo(df_dim, COL_CLIENTE, "Cliente", _CHAVE)

    df_ano = filters.recorte_do_ano(df_dim, ano, criterio_mes)
    agregado = metrics.agregado_por_grupo_veiculo(df_ano, valor)
    coluna_ref = "vendas_liquido" if valor == "liquido" else "vendas_bruto"

    # --------------------------------------------------------------- cards
    c1, c2, c3 = st.columns(3)
    with c1:
        cards.card_moeda("Vendas", metrics.vendas(df_ano, valor))
    with c2:
        cards.card_moeda(
            "Ticket Médio",
            metrics.ticket_medio(df_ano, valor),
            legenda="detalhe por veículo na tabela abaixo",
        )
    with c3:
        cards.card_numero(
            "Veículos Ativos",
            metrics.veiculos_ativos(df_ano),
            legenda="pares Grupo+Veículo com PI na base Vendas",
        )

    st.divider()

    # ------------------------------------------------------ vendas por grupo
    por_grupo = metrics.agregado_por_dimensao(df_ano, COL_GRUPO, valor)
    charts.grafico_barra_horizontal(
        por_grupo, COL_GRUPO, "valor", "Vendas por Grupo"
    )

    # ------------------------------------------------ drill-down por veículo
    if not agregado.empty:
        grupos_com_dado = list(por_grupo[COL_GRUPO])
        grupo_escolhido = st.selectbox(
            "Detalhar veículos do grupo",
            grupos_com_dado,
            key=f"{_CHAVE}_drill",
        )
        detalhe = agregado[agregado[COL_GRUPO] == grupo_escolhido]
        charts.grafico_barra_horizontal(
            detalhe,
            COL_VEICULO,
            coluna_ref,
            f"Vendas por Veículo — {grupo_escolhido}",
        )

    st.divider()

    # --------------------------------------------------- rankings completos
    st.subheader("Rankings completos")
    aba_veic, aba_agencia, aba_cliente = st.tabs(["Veículos", "Agências", "Clientes"])
    with aba_veic:
        st.dataframe(
            _tabela_formatada(agregado), width="stretch", hide_index=True,
            row_height=40,
        )
    with aba_agencia:
        st.dataframe(
            metrics.agregado_por_dimensao(df_ano, COL_AGENCIA, valor).rename(
                columns={"valor": "Vendas", "qtd_pis": "Qtd PIs"}
            ),
            width="stretch",
            hide_index=True,
            row_height=40,
            column_config={
                "Vendas": st.column_config.NumberColumn(format="R$ %.2f")
            },
        )
    with aba_cliente:
        st.dataframe(
            metrics.agregado_por_dimensao(df_ano, COL_CLIENTE, valor).rename(
                columns={"valor": "Vendas", "qtd_pis": "Qtd PIs"}
            ),
            width="stretch",
            hide_index=True,
            row_height=40,
            column_config={
                "Vendas": st.column_config.NumberColumn(format="R$ %.2f")
            },
        )

    st.divider()

    # ------------------------------------------- tabela agregada consolidada
    st.subheader("Consolidado por Grupo + Veículo")
    if agregado.empty:
        st.info(cards.SEM_DADOS)
    else:
        st.dataframe(
            _tabela_formatada(agregado), width="stretch", hide_index=True,
            row_height=40,
        )
