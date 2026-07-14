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

#: Cores de série (Sprint 2B, adendo C10): ano corrente na COR DE MARCA
#: (identidade, sem carga de sentimento); ano anterior em cinza tracejado.
#: A paleta padrão do Plotly nunca é usada (2º trace seria vermelho).
COR_SERIE_PRINCIPAL = "#0B7A66"    # cor de marca AdTarget
COR_SERIE_COMPARATIVA = "#9AA2AC"  # cinza (ano anterior, tracejado)
_COR_GRID = "#EDEFF2"
_COR_ZONA_FUTURA = "#F2F4F6"

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
            line=dict(dash="dot", color=COR_SERIE_COMPARATIVA),
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
            line=dict(color=COR_SERIE_PRINCIPAL),
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
            line=dict(color=COR_SERIE_PRINCIPAL),
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
            marker=dict(color=COR_SERIE_PRINCIPAL),  # 2B.1: cor de marca
            hovertemplate="R$ %{x:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=15, color="#14171C")),
        yaxis=dict(autorange="reversed",
                   tickfont=dict(size=12, color="#5B6472")),
        xaxis=dict(gridcolor=_COR_GRID,
                   tickfont=dict(size=11.5, color="#8B93A1")),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=52, b=16, l=8, r=8),
        bargap=0.38,
    )
    st.plotly_chart(fig, width="stretch")


def _aplicar_estilo_hero(fig: go.Figure, ano: int, mes_limite: Optional[int]) -> None:
    """Estilo do Gráfico Hero (2B.7): grid sutil, fundo branco, zona de
    meses futuros esmaecida com rótulo "sem dado disponível"."""
    # Sprint 2B.1 (1.5): o gráfico é o protagonista — mais altura,
    # tipografia maior e contraste melhor. Dados/escalas intocados.
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.16, font=dict(size=12.5, color="#5B6472")),
        margin=dict(t=20, b=8, l=8, r=8),
        height=390,
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(1, 13)),
            ticktext=MESES_ROTULOS,
            showgrid=False,
            range=[0.5, 12.5],
            tickfont=dict(size=12.5, color="#5B6472"),
        ),
        yaxis=dict(
            gridcolor=_COR_GRID, zerolinecolor=_COR_GRID,
            tickfont=dict(size=12, color="#8B93A1"),
        ),
    )
    if mes_limite is not None and mes_limite < 12:
        fig.add_vrect(
            x0=mes_limite + 0.5, x1=12.5,
            fillcolor=_COR_ZONA_FUTURA, opacity=0.9,
            layer="below", line_width=0,
        )
        fig.add_annotation(
            x=(mes_limite + 0.5 + 12.5) / 2, y=0.5, yref="paper",
            text="<i>sem dado disponível</i>", showarrow=False,
            font=dict(size=12, color="#8B93A1"),
        )


def grafico_hero_vendas(
    comparativo: pd.DataFrame, ano: int, mes_limite: Optional[int]
) -> None:
    """Aba "Vendas" do Gráfico Hero: ano corrente sólido em cor de marca,
    ano anterior tracejado cinza, rótulos no pico e no último mês com dado.
    Recebe o DataFrame de metrics.comparativo_mensal (nenhum cálculo aqui).
    """
    meses = list(range(1, 13))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=meses, y=list(comparativo["anterior"]), name=f"{ano - 1} (ano anterior)",
        mode="lines", line=dict(dash="dash", color=COR_SERIE_COMPARATIVA, width=2),
        connectgaps=False, hovertemplate=_FORMATO_MOEDA_HOVER,
    ))
    fig.add_trace(go.Scatter(
        x=meses, y=list(comparativo["atual"]), name=f"{ano} (ano selecionado)",
        mode="lines+markers",
        line=dict(color=COR_SERIE_PRINCIPAL, width=3),
        marker=dict(size=8),
        connectgaps=False, hovertemplate=_FORMATO_MOEDA_HOVER,
    ))
    atual = comparativo["atual"].dropna()
    if not atual.empty:
        from src.components.cards import formatar_moeda_executiva
        mes_pico = int(atual.idxmax())
        # pico destacado: marcador maior + rótulo com mais presença
        fig.add_trace(go.Scatter(
            x=[mes_pico], y=[float(atual.max())], mode="markers",
            marker=dict(size=11, color=COR_SERIE_PRINCIPAL,
                        line=dict(width=2, color="#FFFFFF")),
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_annotation(
            x=mes_pico, y=float(atual.max()), yshift=16, showarrow=False,
            text=f"<b>{formatar_moeda_executiva(float(atual.max()))}</b>",
            font=dict(size=13, color=COR_SERIE_PRINCIPAL),
        )
        ultimo_mes = int(atual.index.max())
        if ultimo_mes != mes_pico:
            fig.add_annotation(
                x=ultimo_mes, y=float(atual.loc[ultimo_mes]), yshift=-18,
                showarrow=False,
                text=f"<b>{formatar_moeda_executiva(float(atual.loc[ultimo_mes]))}</b>",
                font=dict(size=11, color=COR_SERIE_PRINCIPAL),
            )
    _aplicar_estilo_hero(fig, ano, mes_limite)
    st.plotly_chart(fig, width="stretch")


def grafico_hero_ticket(
    por_mes: dict[int, float], ano: int, mes_limite: Optional[int]
) -> None:
    """Aba "Ticket Médio" do Gráfico Hero (linha única do ano, com lacunas)."""
    meses = list(range(1, 13))
    fig = go.Figure(go.Scatter(
        x=meses, y=[por_mes.get(m) for m in meses], name=f"{ano}",
        mode="lines+markers",
        line=dict(color=COR_SERIE_PRINCIPAL, width=2.5), marker=dict(size=7),
        connectgaps=False, hovertemplate=_FORMATO_MOEDA_HOVER,
    ))
    _aplicar_estilo_hero(fig, ano, mes_limite)
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
