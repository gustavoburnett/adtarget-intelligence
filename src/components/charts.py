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

from src.components.design_tokens import COLOR, TYPOGRAPHY

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


def _aplicar_estilo_hero(
    fig: go.Figure, ano: int, mes_limite: Optional[int], *,
    design_performance: bool = True,
    rotulo_futuro: str = "<i>sem dado disponível</i>",
) -> None:
    """Apresentação da Evolução, exclusiva da Performance Comercial.

    A faixa de calendário e seus textos preservam o comportamento existente.
    Nenhum limite, unidade, hover ou lacuna é alterado pelo estilo.
    """
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#FFFFFF", bordercolor="#E3E6EA",
            font=dict(size=12, color="#14171C"),
        ),
        legend=dict(orientation="h", y=-0.16, font=dict(size=12.5, color="#5B6472")),
        margin=dict(t=24, b=8, l=8, r=8),
        height=392,
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(1, 13)),
            ticktext=MESES_ROTULOS,
            showgrid=False,
            zeroline=False,
            range=[0.5, 12.5],
            tickfont=dict(size=12.5, color="#5B6472"),
        ),
        yaxis=dict(
            gridcolor=_COR_GRID, zeroline=False,
            tickfont=dict(size=12, color="#8B93A1"),
        ),
    )
    if design_performance:
        # O caminho legado continua idêntico para a API pública da Meta.
        fig.update_layout(
            plot_bgcolor=COLOR["surface-card"],
            font=dict(family=TYPOGRAPHY["family"], size=12, color=COLOR["text-muted"]),
            hoverlabel=dict(
                bgcolor=COLOR["surface-card"], bordercolor=COLOR["line-card"],
                font=dict(family=TYPOGRAPHY["family"], size=12, color=COLOR["ink"]),
            ),
            legend=dict(
                x=0, xanchor="left", font=dict(size=13, color=COLOR["text-secondary"]),
            ),
            xaxis=dict(
                showline=True, linecolor=COLOR["chart-base"], linewidth=1,
                tickfont=dict(size=12, color=COLOR["text-muted"]),
            ),
            yaxis=dict(
                gridcolor=COLOR["chart-grid"], gridwidth=1,
                tickfont=dict(size=11, color=COLOR["text-muted"]),
            ),
        )
        # A versão mínima declarada pode não oferecer o traço da grade.
        # A aproximação sólida usa os tokens, sem atualizar dependências.
        if "griddash" in go.layout.YAxis()._valid_props:
            fig.update_yaxes(griddash="2px,5px")
    if mes_limite is not None and mes_limite < 12:
        fig.add_vrect(
            x0=mes_limite + 0.5, x1=12.5,
            fillcolor=COLOR["surface-page"] if design_performance else _COR_ZONA_FUTURA,
            opacity=0.9,
            layer="below", line_width=0,
        )
        fig.add_annotation(
            x=(mes_limite + 0.5 + 12.5) / 2, y=0.5, yref="paper",
            text=rotulo_futuro, showarrow=False,
            font=dict(
                size=11 if design_performance else 12,
                color=COLOR["text-muted"] if design_performance else "#8B93A1",
            ),
        )
        if design_performance:
            fig.layout.annotations[-1].xanchor = "right"


def _rotulo_meses_vendas(meses: list[int]) -> str:
    """Compacta meses consecutivos apenas para a nota de apresentação."""
    intervalos: list[str] = []
    inicio = fim = 0
    for mes in meses:
        if not intervalos or mes != fim + 1:
            inicio = mes
            intervalos.append(MESES_ROTULOS[mes - 1])
        else:
            intervalos[-1] = f"{MESES_ROTULOS[inicio - 1]}–{MESES_ROTULOS[mes - 1]}"
        fim = mes
    return ", ".join(intervalos)


def _contexto_calendario_vendas(comparativo: pd.DataFrame, mes_atual: int) -> str:
    """Distingue calendário e presença; saldo zero não implica ausência."""
    presentes = comparativo["atual"].notna()
    partes: list[str] = []
    if mes_atual > 1:
        partes.append(f"{_rotulo_meses_vendas(list(range(1, mes_atual)))}: meses encerrados")
    disponibilidade = "com registros de vendas" if presentes.loc[mes_atual] else "sem registros no recorte"
    partes.append(f"{MESES_ROTULOS[mes_atual - 1]}: em andamento, {disponibilidade}")
    futuros = list(range(mes_atual + 1, 13))
    for com_registros, rotulo in ((True, "com registros de vendas"), (False, "sem registros no recorte")):
        meses = [mes for mes in futuros if bool(presentes.loc[mes]) == com_registros]
        if meses:
            estado = "futuro" if len(meses) == 1 else "futuros"
            partes.append(f"{_rotulo_meses_vendas(meses)}: {estado} {rotulo}")
    ausentes_encerrados = [mes for mes in range(1, mes_atual) if not presentes.loc[mes]]
    if ausentes_encerrados:
        partes.append(f"Sem registros no recorte: {_rotulo_meses_vendas(ausentes_encerrados)}")
    return " · ".join(partes)


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
        mode="lines", line=dict(dash="dash", color=COLOR["chart-previous"], width=1.8),
        connectgaps=False, hovertemplate=_FORMATO_MOEDA_HOVER,
    ))
    fig.add_trace(go.Scatter(
        x=meses, y=list(comparativo["atual"]), name=f"{ano} (ano selecionado)",
        mode="lines+markers",
        line=dict(color=COLOR["brand"], width=3),
        marker=dict(
            size=7, color=COLOR["surface-card"],
            line=dict(color=COLOR["brand"], width=2),
        ),
        fill="tozeroy",
        fillcolor=COLOR["chart-highlight"],
        connectgaps=False, hovertemplate=_FORMATO_MOEDA_HOVER,
    ))
    # Gradiente é apresentação da área existente, sem mudar sua geometria.
    # O preenchimento discreto acima serve de aproximação em versões antigas.
    if "fillgradient" in go.Scatter()._valid_props:
        fig.data[1].fillgradient = dict(
            type="vertical",
            colorscale=[(0, COLOR["chart-area-end"]), (1, COLOR["chart-area-start"])],
        )
    atual = comparativo["atual"].dropna()
    if not atual.empty:
        from src.components.cards import formatar_moeda_executiva
        mes_pico = int(atual.idxmax())
        # pico destacado: marcador maior + rótulo com mais presença
        fig.add_trace(go.Scatter(
            x=[mes_pico], y=[float(atual.max())], mode="markers",
            marker=dict(size=13, color=COLOR["brand"],
                        line=dict(width=2.5, color=COLOR["surface-card"])),
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_annotation(
            x=mes_pico, y=float(atual.max()), yshift=16, showarrow=False,
            xanchor="left" if mes_pico <= 2 else "right" if mes_pico >= 11 else "center",
            text=f"<b>{formatar_moeda_executiva(float(atual.max()))}</b>",
            font=dict(size=13, color=COLOR["brand"]),
            bgcolor=COLOR["surface-card"], bordercolor=COLOR["line-card"],
            borderwidth=1, borderpad=5,
        )
        ultimo_mes = int(atual.index.max())
        if ultimo_mes != mes_pico:
            fig.add_annotation(
                x=ultimo_mes, y=float(atual.loc[ultimo_mes]), yshift=-18,
                showarrow=False,
                xanchor="left" if ultimo_mes <= 2 else "right" if ultimo_mes >= 11 else "center",
                text=f"<b>{formatar_moeda_executiva(float(atual.loc[ultimo_mes]))}</b>",
                font=dict(size=12, color=COLOR["brand"]),
                bgcolor=COLOR["surface-card"], bordercolor=COLOR["line-card"],
                borderwidth=1, borderpad=4,
            )
    _aplicar_estilo_hero(fig, ano, mes_limite, rotulo_futuro="<i>meses futuros</i>")
    if not atual.empty:
        fig.add_vrect(
            x0=mes_pico - 0.42, x1=mes_pico + 0.42,
            fillcolor=COLOR["chart-highlight"], opacity=1,
            layer="below", line_width=0,
        )
    st.plotly_chart(fig, width="stretch")
    if mes_limite is not None:
        st.caption(_contexto_calendario_vendas(comparativo, mes_limite))


def grafico_hero_ticket(
    por_mes: dict[int, float], ano: int, mes_limite: Optional[int]
) -> None:
    """Aba "Ticket Médio" do Gráfico Hero (linha única do ano, com lacunas)."""
    meses = list(range(1, 13))
    fig = go.Figure(go.Scatter(
        x=meses, y=[por_mes.get(m) for m in meses], name=f"{ano}",
        mode="lines+markers",
        line=dict(color=COLOR["brand"], width=3),
        marker=dict(
            size=7, color=COLOR["surface-card"],
            line=dict(color=COLOR["brand"], width=2),
        ),
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
