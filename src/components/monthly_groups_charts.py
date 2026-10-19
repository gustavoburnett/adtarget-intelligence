"""Figuras mensais por grupo: apresentação pura dos contratos existentes.

Os valores vêm do adaptador, sem rateio, projeção ou recálculo financeiro.
``customdata[0]`` identifica o mês tanto no desktop quanto no mobile.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from html import escape
from typing import TYPE_CHECKING

import plotly.graph_objects as go

from src.components.cards import formatar_moeda, formatar_moeda_executiva
from src.components.design_tokens import COLOR, TYPOGRAPHY

if TYPE_CHECKING:
    from src.components.monthly_groups_data import GrupoMensal, MesGrupo

PERSPECTIVAS = ("Vendas × Meta", "Atingimento", "Desvio")
_MESES = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")
_MESES_COMPLETOS = (
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)
_ESTADOS = {"encerrado": "Mês encerrado", "em_andamento": "Mês em andamento", "futuro": "Mês futuro"}


def _moeda(valor: Decimal) -> str:
    return formatar_moeda(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _pct(valor: Decimal) -> str:
    return f"{valor.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP):.1f}".replace(".", ",") + "%"


def _hover(model: GrupoMensal, mes: MesGrupo) -> str:
    fechado = mes.estado_mes == "encerrado"
    partes = [
        f"<b>{escape(model.grupo)} · {_MESES_COMPLETOS[mes.mes - 1]} {model.ano}</b>",
        _ESTADOS[mes.estado_mes],
    ]
    if mes.registros:
        partes.append(f"{'Realizado' if fechado else 'Já vendido'}: {_moeda(mes.vendido)}")
    if mes.estado_meta == "inativa":
        partes.append("Fora de vigência · meta inativa neste mês")
    elif mes.estado_meta == "ausente":
        partes.append("Sem meta cadastrada neste mês")
    else:
        partes.append(f"Meta mensal vigente: {_moeda(mes.meta)}")
        if mes.estado_meta == "zero_ativa":
            partes.append("Meta ativa com valor zero · percentual não calculável")
    if mes.registros == 0:
        partes.append("Sem registros elegíveis no perímetro selecionado. "
                      "Isso não comprova venda zero e não gera atingimento nem desvio.")
    else:
        partes.append(f"Registros de vendas: {mes.registros}")
        if mes.vendido == 0:
            partes.append("Saldo de vendas zerado com registros")
    if mes.atingimento_pct is not None:
        partes.append(f"{'Atingimento mensal' if fechado else 'Cobertura já vendida'}: {_pct(mes.atingimento_pct)}")
    if mes.desvio is not None:
        if mes.desvio < 0:
            rotulo = "Déficit mensal" if fechado else "Falta cobrir (não é déficit)"
        elif mes.desvio == 0:
            rotulo = "Na meta" if fechado else "Meta já coberta"
        else:
            rotulo = "Acima da meta" if fechado else "Cobertura acima da meta"
        partes.append(f"{rotulo}: {_moeda(abs(mes.desvio))}")
    if mes.fora_perimetro != 0:
        partes.append(f"Vendas fora do perímetro de metas: {_moeda(mes.fora_perimetro)}")
    if mes.veiculos:
        partes.append("<b>Contribuição dos veículos nas vendas</b>")
        for veiculo in mes.veiculos:
            participacao = f" · {_pct(veiculo.percentual)} das vendas" if veiculo.percentual is not None else ""
            partes.append(f"{escape(veiculo.veiculo)}: {_moeda(veiculo.valor)}{participacao}")
    return "<br>".join(partes)


def _rotulo_mes(mes: MesGrupo) -> str:
    sufixo = "*" if mes.estado_mes == "em_andamento" else "°" if mes.estado_mes == "futuro" else ""
    return _MESES[mes.mes - 1] + sufixo


def _faixa_inativa(fig: go.Figure, mes: int, mobile: bool) -> None:
    """Hachura decorativa em coordenadas paper, sem inventar pontos ou escala."""
    if mobile:
        fig.add_shape(type="rect", x0=0, x1=1, y0=mes - .43, y1=mes + .43,
                      xref="paper", yref="y", fillcolor=COLOR["surface-muted"], line_width=0, layer="below")
        for parte in range(8):
            inicio = parte / 8
            fig.add_shape(type="line", x0=inicio, x1=inicio + .10, y0=mes - .43, y1=mes + .43,
                          xref="paper", yref="y", line=dict(color=COLOR["chart-hatch"], width=1), layer="below")
    else:
        fig.add_shape(type="rect", x0=mes - .43, x1=mes + .43, y0=0, y1=1,
                      xref="x", yref="paper", fillcolor=COLOR["surface-muted"], line_width=0, layer="below")
        for parte in range(8):
            inicio = parte / 8
            fig.add_shape(type="line", x0=mes - .43, x1=mes + .43, y0=inicio, y1=inicio + .10,
                          xref="x", yref="paper", line=dict(color=COLOR["chart-hatch"], width=1), layer="below")


def figura_mensal(
    model: GrupoMensal, perspectiva: str = "Vendas × Meta", *,
    mobile: bool = False, mes_selecionado: int | None = None,
) -> go.Figure:
    """Doze meses com orientação responsiva e seleção nativa por mês inteiro.

    Ausência de base permanece ``None``; percentuais acima de 100% e desvios
    negativos são preservados. O hover distingue realizado e cobertura futura.
    """
    if perspectiva not in PERSPECTIVAS:
        raise ValueError("Perspectiva mensal inválida")
    if mes_selecionado is not None and (type(mes_selecionado) is not int or not 1 <= mes_selecionado <= 12):
        raise ValueError("Mês selecionado deve estar entre 1 e 12")
    meses = sorted(model.meses, key=lambda item: item.mes)
    numeros = [mes.mes for mes in meses]
    customdata = [[mes.mes, _hover(model, mes)] for mes in meses]
    selecionados = [numeros.index(mes_selecionado)] if mes_selecionado in numeros else None
    fig = go.Figure()

    def barra(valores, nome, cores, *, meta=False, percentuais=False):
        numericos = [float(valor) if valor is not None else None for valor in valores]
        rotulos = [
            "" if valor is None else _pct(valor) if percentuais
            else ("+" if perspectiva == "Desvio" and valor > 0 else "") + formatar_moeda_executiva(valor)
            for valor in valores
        ]
        marcador = dict(color=cores, line=dict(color=COLOR["chart-hatch"] if meta else cores, width=1))
        if meta:
            marcador["pattern"] = dict(shape="/", fgcolor=COLOR["chart-hatch"], bgcolor=COLOR["surface-card"], size=6, solidity=.13)
        fig.add_trace(go.Bar(
            x=numericos if mobile else numeros, y=numeros if mobile else numericos,
            orientation="h" if mobile else "v", name=nome, marker=marcador,
            width=.72 if meta else .46,
            text=None if meta or perspectiva == "Vendas × Meta" else rotulos,
            textposition="outside", textangle=0, cliponaxis=False,
            textfont=dict(size=11, color=COLOR["ink"]),
            customdata=customdata, hovertemplate="%{customdata[1]}<extra></extra>",
            selectedpoints=selecionados, selected=dict(marker=dict(opacity=1)),
            unselected=dict(marker=dict(opacity=.55)),
        ))

    if perspectiva == "Vendas × Meta":
        barra([mes.meta for mes in meses], "Meta mensal", COLOR["surface-card"], meta=True)
        barra([mes.vendido if mes.estado_mes == "encerrado" else None for mes in meses], "Realizado", COLOR["brand"])
        barra([mes.vendido if mes.estado_mes != "encerrado" else None for mes in meses], "Já vendido", COLOR["chart-previous"])
        for mes in meses:
            if mes.atingimento_pct is not None:
                fig.add_annotation(
                    x=1.03 if mobile else mes.mes, y=mes.mes if mobile else 1.03,
                    xref="paper" if mobile else "x", yref="y" if mobile else "paper",
                    xanchor="left" if mobile else "center", yanchor="middle" if mobile else "bottom",
                    text=_pct(mes.atingimento_pct), showarrow=False,
                    font=dict(size=11, color=COLOR["text-muted"] if mes.estado_mes != "encerrado" else COLOR["ink"]),
                )
    else:
        percentual = perspectiva == "Atingimento"
        valores = [mes.atingimento_pct if percentual else mes.desvio for mes in meses]
        cores = [
            COLOR["chart-previous"] if mes.estado_mes != "encerrado"
            else COLOR["negative"] if valor is not None and valor < (100 if percentual else 0)
            else COLOR["positive"]
            for mes, valor in zip(meses, valores)
        ]
        barra(valores, "Atingimento / cobertura" if percentual else "Desvio / falta cobrir", cores, percentuais=percentual)
        if percentual and any(mes.meta is not None and mes.meta > 0 for mes in meses):
            referencia = dict(line=dict(color=COLOR["text-muted"], dash="dash", width=1))
            if mobile:
                fig.add_vline(x=100, **referencia)
            else:
                fig.add_hline(y=100, **referencia)

    eixo_meses = dict(
        tickmode="array", tickvals=numeros, ticktext=[_rotulo_mes(mes) for mes in meses],
        range=[12.6, .4] if mobile else [.4, 12.6], showgrid=False, zeroline=False,
        tickfont=dict(size=11, color=COLOR["text-secondary"]), automargin=True, fixedrange=True,
    )
    eixo_valor = dict(
        gridcolor=COLOR["chart-grid"], gridwidth=1, rangemode="tozero", nticks=5,
        zeroline=perspectiva == "Desvio", zerolinecolor=COLOR["chart-base"],
        tickfont=dict(size=10, color=COLOR["text-muted"]), automargin=True, fixedrange=True,
        ticksuffix="%" if perspectiva == "Atingimento" else "", tickformat="~s",
    )
    fig.update_layout(
        height=700 if mobile else 390, autosize=True, barmode="overlay", bargap=.25,
        font=dict(family=TYPOGRAPHY["family"], color=COLOR["text-secondary"], size=12),
        plot_bgcolor=COLOR["surface-card"], paper_bgcolor="rgba(0,0,0,0)", separators=",.",
        hovermode="closest", clickmode="event+select", dragmode=False,
        hoverlabel=dict(bgcolor=COLOR["surface-card"], bordercolor=COLOR["line-card"],
                        font=dict(family=TYPOGRAPHY["family"], color=COLOR["ink"], size=11)),
        legend=dict(orientation="h", x=0, y=1.04 if mobile else 1.14, yanchor="bottom", font=dict(size=11)),
        showlegend=perspectiva == "Vendas × Meta", margin=dict(t=40 if mobile else 64, b=36, l=8, r=70 if mobile else 18),
        xaxis=eixo_valor if mobile else eixo_meses, yaxis=eixo_meses if mobile else eixo_valor,
        uirevision=f"{model.grupo}:{model.ano}:{perspectiva}:{mobile}",
    )
    for mes in meses:
        if mes.estado_meta == "inativa":
            _faixa_inativa(fig, mes.mes, mobile)
    return fig
