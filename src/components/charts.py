"""Gráficos Plotly reutilizáveis.

Este módulo NÃO calcula métricas: recebe estruturas prontas de metrics.py
(dicionários mês->valor, DataFrames agregados) e apenas plota.

Regra obrigatória (documento 02): meses sem dado aparecem como LACUNA na
linha (None no Plotly interrompe a linha), nunca como valor zero.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

MESES_ROTULOS = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]

_FORMATO_MOEDA_HOVER = "R$ %{y:,.2f}"


def _serie_com_lacunas(por_mes: dict[int, float]) -> list[Optional[float]]:
    """Converte {mes: valor} em lista de 12 posições com None nas lacunas."""
    return [por_mes.get(mes) for mes in range(1, 13)]


def grafico_evolucao_comparativa(
    comparativo: pd.DataFrame, ano: int, titulo: str
) -> None:
    """Linha do ano selecionado + linha pontilhada do ano anterior
    (comparativo mês a mês do documento 04). Recebe o DataFrame de
    metrics.comparativo_mensal (índice 1-12, colunas atual/anterior)."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=MESES_ROTULOS,
            y=list(comparativo["anterior"]),
            name=str(ano - 1),
            mode="lines+markers",
            line=dict(dash="dot"),
            connectgaps=False,
            hovertemplate=_FORMATO_MOEDA_HOVER,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=MESES_ROTULOS,
            y=list(comparativo["atual"]),
            name=str(ano),
            mode="lines+markers",
            connectgaps=False,
            hovertemplate=_FORMATO_MOEDA_HOVER,
        )
    )
    fig.update_layout(
        title=titulo,
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1),
        margin=dict(t=60, b=20),
    )
    st.plotly_chart(fig, width="stretch")


def grafico_linha_mensal(por_mes: dict[int, float], titulo: str) -> None:
    """Linha simples de um ano (ex: evolução do Ticket Médio), com lacunas."""
    fig = go.Figure(
        go.Scatter(
            x=MESES_ROTULOS,
            y=_serie_com_lacunas(por_mes),
            mode="lines+markers",
            connectgaps=False,
            hovertemplate=_FORMATO_MOEDA_HOVER,
        )
    )
    fig.update_layout(title=titulo, margin=dict(t=60, b=20))
    st.plotly_chart(fig, width="stretch")


def grafico_barra_horizontal(
    dados: pd.DataFrame,
    coluna_rotulo: str,
    coluna_valor: str,
    titulo: str,
    top_n: Optional[int] = None,
) -> None:
    """Barra horizontal ordenada do maior para o menor (rankings)."""
    if dados.empty:
        st.info("Sem dados no recorte selecionado")
        return
    recorte = dados.head(top_n) if top_n else dados
    fig = go.Figure(
        go.Bar(
            x=list(recorte[coluna_valor]),
            y=list(recorte[coluna_rotulo]),
            orientation="h",
            hovertemplate="R$ %{x:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=titulo,
        yaxis=dict(autorange="reversed"),  # maior no topo
        margin=dict(t=60, b=20),
    )
    st.plotly_chart(fig, width="stretch")


def grafico_por_status(resumo: pd.DataFrame, titulo: str) -> None:
    """Barra por status com valor e contagem (saúde da carteira,
    documento 04). Recebe o DataFrame de metrics.resumo_por_status."""
    if resumo.empty:
        st.info("Sem dados no recorte selecionado")
        return
    fig = go.Figure(
        go.Bar(
            x=list(resumo["valor"]),
            y=list(resumo["STATUS"]),
            orientation="h",
            text=[f"{qtd} PIs" for qtd in resumo["qtd_pis"]],
            textposition="auto",
            hovertemplate="R$ %{x:,.2f} — %{text}<extra></extra>",
        )
    )
    fig.update_layout(
        title=titulo,
        yaxis=dict(autorange="reversed"),
        margin=dict(t=60, b=20),
    )
    st.plotly_chart(fig, width="stretch")
