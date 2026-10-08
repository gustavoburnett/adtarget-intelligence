"""Figuras puras de Metas: apresentam os resultados sem recalcular o negócio.

O realizado oficial termina no último mês encerrado. A carteira dos demais
meses aparece somente na visão mensal e recebe o nome ``Já vendido``.
Contornos são shapes porque o contorno de uma barra Plotly não aceita dash.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

import plotly.graph_objects as go

from src.components.cards import (
    COR_BORDA_SUAVE,
    COR_MARCA,
    COR_MARCA_SUAVE,
    COR_NEUTRO,
    COR_TEXTO,
    COR_TEXTO_SECUNDARIO,
    formatar_moeda,
    formatar_moeda_executiva,
)
from src.components.design_tokens import COLOR
from src.data.metas import (
    MesMetas,
    MesPulso,
    ResultadoMetas,
    ResultadoPulso,
    cobertura_mensal_pulso,
)

_MESES = (
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
)
_MESES_COMPLETOS = (
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)
_ESTADOS = {
    "encerrado": "Mês encerrado",
    "em_andamento": "Mês em andamento",
    "futuro": "Mês futuro",
}


def _moeda(valor: Decimal | None) -> str:
    if valor is None:
        return "sem base de comparação"
    return formatar_moeda(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _pct(valor: Decimal | None, *, sinal: bool = False) -> str:
    if valor is None:
        return "sem base de comparação"
    valor = valor.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return (f"{valor:+.1f}" if sinal else f"{valor:.1f}").replace(".", ",") + "%"


def _sem_percentual(mes: MesMetas) -> str:
    if mes.estado_meta == "zero_ativa":
        return "Meta ativa com valor zero · sem base para percentual"
    if mes.estado_meta == "ausente":
        return "Sem meta cadastrada neste mês"
    return "Sem meta ativa neste mês"


def _saldo(valor: Decimal | None) -> str:
    if valor is None:
        return ""
    rotulo = "Superávit" if valor >= 0 else "Déficit"
    return f"{rotulo}: {_moeda(abs(valor))}"


def _hover_acumulado(mes: MesMetas, ano: int) -> str:
    partes = [
        f"<b>{_MESES_COMPLETOS[mes.mes - 1].upper()} {ano}</b>",
        _ESTADOS[mes.estado_mes],
        f"Meta acumulada: {_moeda(mes.meta_acumulada)}",
    ]
    if mes.estado_mes == "encerrado":
        partes.extend([
            f"Realizado acumulado: {_moeda(mes.realizado_acumulado)}",
            f"Atingimento: {_pct(mes.atingimento_acumulado_pct)}",
            _saldo(mes.saldo_acumulado),
        ])
        if mes.meta_acumulada_centavos == 0:
            partes[-2] = "Sem meta acumulada positiva · sem base para percentual"
    partes.append(
        f"{ano - 1}, mesmo perímetro: {_moeda(mes.realizado_anterior_acumulado)}"
    )
    if mes.estado_mes == "encerrado":
        partes.append(f"YoY: {_pct(mes.yoy_acumulado_pct, sinal=True)}")
    return "<br>".join(parte for parte in partes if parte)


def _hover_mensal(mes: MesMetas, pulso: MesPulso, ano: int) -> str:
    partes = [
        f"<b>{_MESES_COMPLETOS[mes.mes - 1].upper()} {ano}</b>",
        _ESTADOS[mes.estado_mes],
    ]
    if mes.estado_mes == "encerrado":
        partes.extend([
            f"Realizado: {_moeda(mes.realizado)}",
            f"Meta: {_moeda(mes.meta)}",
            (
                f"Atingimento: {_pct(mes.atingimento_pct)}"
                if mes.meta_centavos > 0 else _sem_percentual(mes)
            ),
            _saldo(mes.saldo),
            f"{_MESES_COMPLETOS[mes.mes - 1]}/{ano - 1}: {_moeda(mes.realizado_anterior)}",
            f"YoY: {_pct(mes.yoy_pct, sinal=True)}",
        ])
    else:
        partes.extend([
            f"Já vendido: {_moeda(pulso.vendido)}",
            f"Meta: {_moeda(mes.meta)}",
            (
                f"Cobertura atual: {_pct(cobertura_mensal_pulso(pulso))}"
                if mes.meta_centavos > 0 else _sem_percentual(mes)
            ),
        ])
    return "<br>".join(parte for parte in partes if parte)


def _eixo_meses(resultado: ResultadoMetas) -> list[str]:
    return [
        f"<b>{_MESES[mes.mes - 1]}*</b>" if mes.estado_mes == "em_andamento"
        else f"{_MESES[mes.mes - 1]}°" if mes.estado_mes == "futuro"
        else _MESES[mes.mes - 1]
        for mes in resultado.meses
    ]


def _estilo(fig: go.Figure, resultado: ResultadoMetas, *, altura: int) -> None:
    fig.update_layout(
        height=altura,
        autosize=True,
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12, color=COR_TEXTO_SECUNDARIO),
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="#FFFFFF", bordercolor=COR_BORDA_SUAVE,
            font=dict(size=12, color=COR_TEXTO),
        ),
        legend=dict(
            orientation="h", x=0, y=1.08, yanchor="bottom",
            font=dict(size=11, color=COR_TEXTO_SECUNDARIO),
            traceorder="normal",
        ),
        margin=dict(t=50, b=64, l=8, r=8),
        separators=",.",
        xaxis=dict(
            tickmode="array", tickvals=list(range(1, 13)),
            ticktext=_eixo_meses(resultado),
            range=[0.5, 12.5], showgrid=False, zeroline=False,
            tickfont=dict(size=11, color=COR_TEXTO_SECUNDARIO),
            fixedrange=True,
        ),
        yaxis=dict(
            gridcolor=COR_BORDA_SUAVE, zeroline=False, nticks=4,
            rangemode="tozero", tickformat="~s",
            tickfont=dict(size=11, color=COLOR["text-muted"]),
            fixedrange=True,
        ),
    )
    estados = {mes.estado_mes for mes in resultado.meses}
    legenda_estados = []
    if "em_andamento" in estados:
        legenda_estados.append("<b>*</b> Em andamento")
    if "futuro" in estados:
        legenda_estados.append("<b>°</b> Futuro")
    if legenda_estados:
        fig.add_annotation(
            x=0, y=-0.20, xref="paper", yref="paper", xanchor="left",
            text=" · ".join(legenda_estados), showarrow=False,
            font=dict(size=10, color=COLOR["text-muted"]),
        )


def _rotulo_final(
    fig: go.Figure, meses: list[int], valores: list[Decimal | None],
    rotulo: str, cor: str, deslocamento: int,
) -> None:
    disponiveis = [(mes, valor) for mes, valor in zip(meses, valores) if valor is not None]
    if not disponiveis:
        return
    mes, valor = disponiveis[-1]
    fig.add_annotation(
        x=mes, y=float(valor), text=f"<b>{rotulo} · {formatar_moeda_executiva(valor)}</b>",
        xanchor="right", xshift=-5, yshift=deslocamento, showarrow=False,
        font=dict(size=11, color=cor),
    )


def evolucao_acumulada(resultado: ResultadoMetas) -> go.Figure:
    """Meta e anterior completos; realizado oficial sem prolongar meses abertos."""
    meses = [mes.mes for mes in resultado.meses]
    metas = [mes.meta_acumulada for mes in resultado.meses]
    realizados = [mes.realizado_acumulado for mes in resultado.meses]
    anteriores = [mes.realizado_anterior_acumulado for mes in resultado.meses]
    hovers = [_hover_acumulado(mes, resultado.ano) for mes in resultado.meses]
    fig = go.Figure()
    for valores, nome, cor, dash, largura, modo in (
        (metas, "Meta acumulada", COR_TEXTO_SECUNDARIO, "dashdot", 1.8, "lines"),
        (anteriores, f"{resultado.ano - 1} · mesmo perímetro", COR_NEUTRO, "dash", 1.5, "lines"),
        (realizados, f"Realizado {resultado.ano} · fechado", COR_MARCA, "solid", 3, "lines+markers"),
    ):
        fig.add_trace(go.Scatter(
            x=meses, y=[float(valor) if valor is not None else None for valor in valores],
            name=nome, mode=modo, line=dict(color=cor, dash=dash, width=largura),
            marker=dict(size=7, color=cor), connectgaps=False,
            customdata=hovers, hovertemplate="%{customdata}<extra></extra>",
        ))
    _estilo(fig, resultado, altura=430)
    _rotulo_final(fig, meses, metas, "Meta", COR_TEXTO_SECUNDARIO, 14)
    _rotulo_final(fig, meses, anteriores, str(resultado.ano - 1), COLOR["text-muted"], -16)
    _rotulo_final(fig, meses, realizados, "Realizado", COR_MARCA, 15)
    for mes in resultado.meses:
        if mes.estado_mes == "em_andamento":
            fig.add_vrect(
                x0=mes.mes - 0.45, x1=mes.mes + 0.45,
                fillcolor=COR_MARCA_SUAVE, opacity=0.6,
                line=dict(color=COR_NEUTRO, dash="dash", width=1), layer="below",
            )
    return fig


def _rotulo_barra(valor: Decimal) -> str:
    if abs(valor) >= 1_000_000:
        return f"{valor / Decimal(1_000_000):.2f}".replace(".", ",") + " Mi"
    if abs(valor) >= 1_000:
        return f"{valor / Decimal(1_000):.0f}".replace(".", ",") + " mil"
    return f"{valor:.0f}"


def evolucao_mensal(resultado: ResultadoMetas, pulso: ResultadoPulso) -> go.Figure:
    """Meta completa desde zero, com realizado/carteira sobrepostos sem empilhar."""
    if (
        resultado.ano != pulso.ano
        or resultado.data_referencia != pulso.data_referencia
        or resultado.meses_encerrados != pulso.meses_encerrados
        or [mes.mes for mes in resultado.meses] != [mes.mes for mes in pulso.meses]
    ):
        raise ValueError("As séries mensal e comercial devem usar o mesmo ano e referência.")
    meses = [mes.mes for mes in resultado.meses]
    hovers = [
        _hover_mensal(mes, mes_pulso, resultado.ano)
        for mes, mes_pulso in zip(resultado.meses, pulso.meses)
    ]
    # Os saldos já calculados selecionam os extremos relevantes. A seleção
    # muda somente os rótulos; todos os valores permanecem na figura e hover.
    fechados = [
        mes for mes in resultado.meses
        if mes.estado_mes == "encerrado" and mes.saldo is not None
    ]
    maiores_superacoes = sorted(
        (mes for mes in fechados if mes.saldo > 0),
        key=lambda mes: (-mes.saldo, mes.mes),
    )
    maiores_deficits = sorted(
        (mes for mes in fechados if mes.saldo < 0),
        key=lambda mes: (mes.saldo, mes.mes),
    )
    meses_rotulados = {
        mes.mes for mes in maiores_superacoes[:1] + maiores_deficits[:1]
    } | {
        mes.mes for mes in pulso.meses if mes.estado_mes == "em_andamento"
    }
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=meses, y=[float(mes.meta) for mes in resultado.meses],
        name="Meta", width=0.64, base=0,
        marker=dict(
            color="#FFFFFF", line=dict(width=0),
            pattern=dict(
                shape="/", fillmode="overlay", fgcolor=COR_NEUTRO,
                bgcolor="#FFFFFF", size=5, solidity=0.12,
            ),
        ),
        customdata=hovers, hovertemplate="%{customdata}<extra></extra>",
    ))
    vendido_em_aberto = False
    for estado, nome, opacidade in (
        ("encerrado", "Realizado", 1),
        ("em_andamento", "Já vendido", 0.85),
        ("futuro", "Já vendido", 0.6),
    ):
        pares = [
            (mes, mes_pulso, hover)
            for mes, mes_pulso, hover in zip(resultado.meses, pulso.meses, hovers)
            if mes.estado_mes == estado
        ]
        if not pares:
            continue
        fig.add_trace(go.Bar(
            x=[mes.mes for mes, _, _ in pares],
            y=[float(mes_pulso.vendido) for _, mes_pulso, _ in pares],
            name=nome, legendgroup="fechado" if estado == "encerrado" else "ja_vendido",
            showlegend=estado == "encerrado" or not vendido_em_aberto,
            # A meta permanece visível nas laterais desde a mesma origem,
            # evitando a leitura equivocada de barras empilhadas.
            width=0.42, base=0,
            marker=dict(color=COR_MARCA, opacity=opacidade, line=dict(width=0)),
            text=[
                _rotulo_barra(mes_pulso.vendido) if mes.mes in meses_rotulados else ""
                for mes, mes_pulso, _ in pares
            ] if estado != "futuro" else None,
            textposition="outside", textfont=dict(size=10, color=COR_TEXTO_SECUNDARIO),
            cliponaxis=False,
            customdata=[hover for _, _, hover in pares],
            hovertemplate="%{customdata}<extra></extra>",
        ))
        if estado != "encerrado":
            vendido_em_aberto = True
    _estilo(fig, resultado, altura=330)
    # Respiro fixo para a nota, inclusive quando os meses giram no mobile.
    fig.update_annotations(yshift=-12, selector=dict(yref="paper", y=-0.20))
    fig.update_layout(barmode="overlay", bargap=0.36)
    fig.update_xaxes(ticklabeloverflow="allow")
    for mes in resultado.meses:
        if mes.meta_centavos <= 0:
            continue
        dash = {"encerrado": "solid", "em_andamento": "dash", "futuro": "dot"}[mes.estado_mes]
        fig.add_shape(
            type="rect", x0=mes.mes - 0.32, x1=mes.mes + 0.32,
            y0=0, y1=float(mes.meta),
            fillcolor="rgba(0,0,0,0)",
            line=dict(color=COR_NEUTRO, width=1.3 if dash == "dash" else 0.8, dash=dash),
            layer="above",
        )
    return fig


def evolucao_performance_meta(
    resultado: ResultadoMetas, pulso: ResultadoPulso, *,
    design_performance: bool = False,
) -> go.Figure:
    """Resumo acumulado: realizado fechado e continuação da carteira já vendida.

    O trecho fechado conserva os acumulados oficiais. Somente a transformação
    gráfica da carteira mensal em acumulado acontece aqui, com Decimal; não há
    nova apuração de vendas, percentuais, saldo ou forecast.
    """
    from src.components.charts import _aplicar_estilo_hero

    if (
        resultado.ano != pulso.ano
        or resultado.data_referencia != pulso.data_referencia
        or resultado.meses_encerrados != pulso.meses_encerrados
        or [mes.mes for mes in resultado.meses] != [mes.mes for mes in pulso.meses]
        or any(
            mes.estado_mes != comercial.estado_mes
            or mes.meta_centavos != comercial.meta_centavos
            or (mes.estado_mes == "encerrado" and mes.realizado != comercial.vendido)
            for mes, comercial in zip(resultado.meses, pulso.meses)
        )
    ):
        raise ValueError("As séries de metas e carteira devem usar o mesmo snapshot.")

    meses = [mes.mes for mes in resultado.meses]
    fechados = [mes for mes in resultado.meses if mes.estado_mes == "encerrado"]
    abertos = [
        (mes, comercial)
        for mes, comercial in zip(resultado.meses, pulso.meses)
        if mes.estado_mes != "encerrado"
    ]
    acumulado = fechados[-1].realizado_acumulado if fechados else Decimal(0)
    carteira_acumulada: dict[int, Decimal] = {}
    hovers = {
        mes.mes: _hover_acumulado(mes, resultado.ano) for mes in fechados
    }
    for mes, comercial in abertos:
        acumulado += comercial.vendido
        carteira_acumulada[mes.mes] = acumulado
        andamento = mes.estado_mes == "em_andamento"
        referencia_meta = "Meta acumulada" if andamento else "Meta acumulada planejada"
        detalhe = (
            "Inclui carteira já vendida para" if andamento
            else "Inclui vendas já fechadas para"
        )
        hovers[mes.mes] = "<br>".join([
            f"<b>{_MESES_COMPLETOS[mes.mes - 1].upper()} {resultado.ano}</b>",
            f"{referencia_meta}: {_moeda(mes.meta_acumulada)}",
            f"Total já vendido acumulado: {_moeda(acumulado)}",
            f"{detalhe} {_MESES_COMPLETOS[mes.mes - 1].lower()}",
            _ESTADOS[mes.estado_mes],
        ])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=meses, y=[float(mes.meta_acumulada) for mes in resultado.meses],
        name="Meta acumulada", mode="lines",
        line=dict(color=COR_TEXTO_SECUNDARIO, dash="dashdot", width=1.8),
        customdata=[hovers[mes] for mes in meses],
        hovertemplate="%{customdata}<extra></extra>",
        connectgaps=False,
    ))
    if fechados:
        fig.add_trace(go.Scatter(
            x=meses,
            y=[
                float(mes.realizado_acumulado) if mes.estado_mes == "encerrado" else None
                for mes in resultado.meses
            ],
            name="Realizado acumulado · fechado", mode="lines+markers",
            line=dict(color=COR_MARCA, dash="solid", width=3),
            marker=dict(size=7, color=COR_MARCA, symbol="circle"),
            customdata=[hovers[mes] for mes in meses],
            hovertemplate="%{customdata}<extra></extra>",
            connectgaps=False,
        ))
    if abertos:
        origem = [fechados[-1]] if fechados else []
        meses_carteira = [mes.mes for mes in origem] + [mes.mes for mes, _ in abertos]
        valores_carteira = (
            [fechados[-1].realizado_acumulado] if fechados else []
        ) + [carteira_acumulada[mes.mes] for mes, _ in abertos]
        fig.add_trace(go.Scatter(
            x=meses_carteira, y=[float(valor) for valor in valores_carteira],
            name="Já vendido acumulado", mode="lines+markers",
            line=dict(color=COR_MARCA, dash="dash", width=3),
            marker=dict(
                size=([0] if fechados else []) + [8] * len(abertos),
                color=COR_MARCA, symbol="circle-open",
                line=dict(color=COR_MARCA, width=1.5),
            ),
            customdata=[hovers[mes] for mes in meses_carteira],
            hovertemplate="%{customdata}<extra></extra>",
            connectgaps=False,
        ))

    _aplicar_estilo_hero(fig, resultado.ano, None, design_performance=design_performance)
    fig.update_layout(autosize=True, hovermode="closest")
    for mes in resultado.meses:
        if mes.estado_mes == "em_andamento":
            fig.add_vrect(
                x0=mes.mes - 0.45, x1=mes.mes + 0.45,
                fillcolor=COR_MARCA_SUAVE, opacity=0.6,
                line=dict(color=COR_NEUTRO, dash="dash", width=1), layer="below",
            )
            fig.add_annotation(
                x=mes.mes, y=1, yref="paper", yshift=12,
                text="Mês em andamento", showarrow=False,
                font=dict(size=10, color=COR_NEUTRO),
            )
    if design_performance:
        # A paleta aprovada é opt-in na página; o contrato legado da figura
        # continua disponível sem modificar constantes de cards compartilhados.
        fig.update_traces(
            line_color=COLOR["text-secondary"], selector=dict(name="Meta acumulada"),
        )
        fig.update_traces(
            line_color=COLOR["brand"], marker_color=COLOR["surface-card"],
            marker_line=dict(color=COLOR["brand"], width=2),
            selector=dict(name="Realizado acumulado · fechado"),
        )
        fig.update_traces(
            line_color=COLOR["brand"], marker_color=COLOR["brand"],
            marker_line=dict(color=COLOR["brand"], width=2),
            selector=dict(name="Já vendido acumulado"),
        )
        fig.update_shapes(fillcolor=COLOR["brand-tint"], line_color=COLOR["chart-previous"])
        fig.update_annotations(font_size=11, font_color=COLOR["text-muted"])
    return fig
