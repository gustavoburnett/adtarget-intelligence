"""Visão executiva de metas, somente leitura e sem cálculos comerciais próprios.

A engine fornece todos os indicadores. Esta página só seleciona o ano,
formata valores e trata os estados de apresentação da visão de metas.
"""

from __future__ import annotations

import datetime as dt
from decimal import ROUND_HALF_UP, Decimal
from html import escape

import pandas as pd
import streamlit as st

from src.components import cards, filters, metas_charts
from src.data.metas import (
    ParceiroMetas, ResultadoMetas, ResultadoPulso,
    avaliar_metas, avaliar_parceiros, avaliar_pulso, vigencia,
)
from src.data.metas_quality import coexistencia_niveis, revisoes_retroativas
from src.data.metas_schema import (
    COL_LINHA_ORIGEM,
    ErroDeMetas,
    validar_metas,
)
from src.data.quality_checks import AlertaQualidade

_MESES = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")
_SEM_META = "Sem meta lançada para o período"
_AGUARDANDO = "Aguardando o primeiro mês encerrado"
_SEM_BASE = "Sem base de comparação"

# Reutiliza as superfícies e cores da Release 1.0; nenhum seletor global novo.
_CSS = f"""
<style>
.atg-metas{{color:{cards.COR_TEXTO};margin:8px 0 24px;}}
.atg-metas-hero{{padding:24px;margin-bottom:16px;}}
.atg-metas-hero-grid{{display:grid;grid-template-columns:minmax(220px,.8fr) minmax(0,1.8fr);gap:24px;align-items:center;}}
.atg-metas-label{{font-size:11px;font-weight:600;color:{cards.COR_NEUTRO};letter-spacing:.04em;line-height:1.5;}}
.atg-metas-eyebrow{{color:{cards.COR_MARCA};font-weight:700;letter-spacing:.08em;}}
.atg-metas-number{{font-size:38px;font-weight:700;letter-spacing:-.02em;line-height:1.15;margin-top:8px;}}
.atg-metas-context{{font-size:12px;color:{cards.COR_TEXTO_SECUNDARIO};line-height:1.5;margin-top:8px;}}
.atg-metas-support{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px 24px;}}
.atg-metas-support-value{{font-size:20px;font-weight:600;line-height:1.3;margin-top:4px;}}
.atg-metas-annual{{padding:20px 24px;margin-bottom:24px;}}
.atg-metas-annual-grid{{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:32px;align-items:center;}}
.atg-metas-annual-sold{{font-size:22px;font-weight:600;line-height:1.3;}}
.atg-metas-annual-pct{{display:flex;justify-content:space-between;gap:12px;align-items:center;font-size:12px;color:{cards.COR_TEXTO_SECUNDARIO};margin-top:14px;}}
.atg-metas-annual-pct strong{{font-size:16px;color:{cards.COR_TEXTO};}}
.atg-metas-annual-progress{{height:6px;border-radius:3px;background:{cards.COR_BORDA_SUAVE};margin:6px 0 12px;overflow:hidden;}}
.atg-metas-annual-fill{{height:100%;background:{cards.COR_MARCA};}}
.atg-metas-annual-gap{{font-size:28px;font-weight:700;line-height:1.3;}}
.atg-metas-annual-gap-copy{{font-size:16px;font-weight:500;margin-top:4px;}}
.atg-metas-projection{{container-type:inline-size;}}
.atg-metas-band{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));padding:20px 0;margin-bottom:16px;}}
.atg-metas-band-cell{{padding:0 24px;min-width:0;}}
.atg-metas-band-cell+.atg-metas-band-cell{{border-left:1px solid {cards.COR_BORDA_SUAVE};}}
.atg-metas-partners{{padding:4px 24px;}}
.atg-metas-partner{{padding:12px 0;border-bottom:1px solid {cards.COR_BORDA_SUAVE};}}
.atg-metas-partner:last-child{{border-bottom:0;}}
.atg-metas-partner-head{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:start;}}
.atg-metas-partner-heading{{display:flex;flex-wrap:wrap;gap:4px 16px;align-items:center;}}
.atg-metas-partner-name{{font-size:14px;font-weight:700;}}
.atg-metas-partner-pct{{font-size:18px;font-weight:700;line-height:1.2;}}
.atg-metas-partner-status{{font-size:11px;}}
.atg-metas-partner-comparison{{font-size:12px;color:{cards.COR_TEXTO_SECUNDARIO};line-height:1.5;margin-top:4px;}}
.atg-metas-progress{{position:relative;height:4px;background:{cards.COR_BORDA_SUAVE};border-radius:3px;margin-top:8px;}}
.atg-metas-progress-fill{{height:100%;background:{cards.COR_MARCA};}}
.atg-metas-progress-reference{{position:absolute;left:80%;width:1px;height:10px;top:-3px;background:{cards.COR_TEXTO_SECUNDARIO};}}
.atg-metas-scale{{position:relative;height:16px;font-size:10px;color:{cards.COR_NEUTRO};margin-top:12px;}}
.atg-metas-scale span{{position:absolute;left:80%;transform:translateX(-50%);white-space:nowrap;}}
.atg-metas h3.atg-metas-partner-group{{font-size:12px;font-weight:600;margin:16px 0 8px;padding:0;}}
.atg-metas-partner-inactive .atg-metas-progress-fill{{background:{cards.COR_NEUTRO};}}
.atg-metas-partner-inactive .atg-metas-partner-status{{color:{cards.COR_TEXTO_SECUNDARIO};}}
.atg-metas-partner details{{margin-top:6px;font-size:11px;color:{cards.COR_TEXTO_SECUNDARIO};}}
.atg-metas-partner summary{{cursor:pointer;width:fit-content;padding:0;}}
.atg-metas-partner summary:focus-visible{{outline:2px solid {cards.COR_MARCA};outline-offset:3px;}}
.atg-metas-partner-details{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px 20px;padding:14px 0 4px;}}
.atg-metas-detail-value{{font-size:14px;font-weight:600;color:{cards.COR_TEXTO};margin-top:4px;}}
.atg-metas-value{{font-size:24px;font-weight:600;letter-spacing:-.01em;line-height:1.35;margin-top:8px;}}
.atg-metas-state{{font-size:16px;font-weight:600;line-height:1.4;}}
.atg-metas-positive{{color:{cards.COR_POSITIVO};}}
.atg-metas-negative{{color:{cards.COR_NEGATIVO};}}
.atg-metas-neutral{{color:{cards.COR_TEXTO};}}
.atg-metas h2.atg-metas-title{{font-size:14px;font-weight:700;margin:0 0 12px;padding:0;}}
.atg-metas-insight{{font-size:12px;color:{cards.COR_TEXTO_SECUNDARIO};line-height:1.5;margin:0 0 24px;padding:0 4px;}}
.atg-metas-empty{{padding:24px;margin:8px 0 24px;}}
.atg-metas-footer{{font-size:11px;color:{cards.COR_NEUTRO};line-height:1.6;margin-top:24px;}}
.atg-metas [title]{{font-variant-numeric:tabular-nums;}}
.atg-metas,.atg-metas *{{box-sizing:border-box;overflow-wrap:anywhere;}}
@media(max-width:900px){{
  .atg-metas-hero-grid{{grid-template-columns:1fr;gap:20px;}}
  .atg-metas-annual-grid{{grid-template-columns:1fr;gap:20px;}}
}}
@container(max-width:650px){{
  .atg-metas-band{{grid-template-columns:1fr;}}
  .atg-metas-band{{padding:0 24px;}}
  .atg-metas-band-cell{{padding:18px 0;}}
  .atg-metas-band-cell+.atg-metas-band-cell{{border-left:0;border-top:1px solid {cards.COR_BORDA_SUAVE};}}
}}
@media(max-width:600px){{
  .atg-metas-support,.atg-metas-band{{grid-template-columns:1fr;}}
  .atg-metas-hero,.atg-metas-annual,.atg-metas-empty{{padding:20px;}}
  .atg-metas-band{{padding:0 20px;}}
  .atg-metas-band-cell{{padding:18px 0;}}
  .atg-metas-band-cell+.atg-metas-band-cell{{border-left:0;border-top:1px solid {cards.COR_BORDA_SUAVE};}}
  .atg-metas-partners{{padding:0 20px;}}
  .atg-metas-partner-details{{grid-template-columns:repeat(2,minmax(0,1fr));}}
  .atg-metas-number{{font-size:34px;}}
}}
</style>
"""


def _pct(valor: Decimal, *, sinal: bool = False) -> str:
    arredondado = valor.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    formato = "+.1f" if sinal else ".1f"
    return f"{format(arredondado, formato).replace('.', ',')}%"


def _moeda(valor: Decimal) -> str:
    """Abreviação executiva com valor completo no tooltip; precisão até a UI."""
    completo = cards.formatar_moeda(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return (
        f'<span class="num" title="{escape(completo, quote=True)}">'
        f'{escape(cards.formatar_moeda_executiva(valor))}</span>'
    )


def _periodo(meses: int, ano: int) -> str:
    return f"Jan a {_MESES[meses - 1]}/{ano}" if meses else str(ano)


def _fechado(resultado: ResultadoMetas) -> str:
    if not resultado.meses_encerrados:
        return "FECHADO · AGUARDANDO PRIMEIRO MÊS ENCERRADO"
    return f"FECHADO ATÉ {_MESES[resultado.meses_encerrados - 1].upper()}/{resultado.ano}"


def _periodo_futuro(pulso: ResultadoPulso) -> str:
    return f'{_MESES[pulso.meses_encerrados]} a Dez/{pulso.ano}' if pulso.meses_restantes else "Ano encerrado"


def _classe_saldo(valor: Decimal) -> str:
    return "positive" if valor > 0 else "negative" if valor < 0 else "neutral"


def _apoio(titulo: str, valor: str, contexto: str = "", classe: str = "neutral") -> str:
    return (
        '<div><div class="atg-metas-label">' + escape(titulo) + '</div>'
        f'<div class="atg-metas-support-value atg-metas-{classe}">{valor}</div>'
        f'<div class="atg-metas-context">{contexto}</div></div>'
    )


def _hero(resultado: ResultadoMetas) -> str:
    periodo = _periodo(resultado.meses_encerrados, resultado.ano)
    if not resultado.meses_encerrados:
        destaque = f'<div class="atg-metas-state">{_AGUARDANDO}</div>'
        apoio = _apoio("Meta acumulada", _AGUARDANDO)
    else:
        if resultado.atingimento_ytd_pct is None:
            destaque = f'<div class="atg-metas-state">{_SEM_META}</div>'
        else:
            destaque = (
                f'<div class="atg-metas-number num atg-metas-{_classe_saldo(resultado.saldo_ytd)}">'
                f'{_pct(resultado.atingimento_ytd_pct)}</div>'
            )
        saldo = resultado.saldo_ytd
        rotulo_saldo = "Superávit YTD" if saldo > 0 else "Déficit YTD" if saldo < 0 else "Saldo YTD"
        apoio = (
            _apoio("Realizado YTD no perímetro de metas", _moeda(resultado.realizado_ytd), periodo)
            + _apoio("Meta YTD", _moeda(resultado.meta_ytd))
            + _apoio(rotulo_saldo, _moeda(abs(saldo)), classe=_classe_saldo(saldo))
        )
        if resultado.yoy_pct is None:
            yoy = _SEM_BASE
            classe_yoy = "neutral"
        else:
            yoy = f'{_pct(resultado.yoy_pct, sinal=True)} YoY'
            classe_yoy = _classe_saldo(resultado.yoy_pct)
        anterior = resultado.realizado_anterior_ytd
        contexto_yoy = f'vs. {_periodo(resultado.meses_encerrados, resultado.ano - 1)}'
        if anterior is not None:
            contexto_yoy += f' · {_moeda(anterior)} no mesmo perímetro'
        apoio += _apoio("YoY no perímetro de metas", yoy, contexto_yoy, classe_yoy)
    return (
        '<section class="atg-card atg-metas-hero" aria-label="Meta acumulada">'
        '<div class="atg-metas-hero-grid"><div>'
        f'<div class="atg-metas-label atg-metas-eyebrow">{_fechado(resultado)}</div>'
        '<div class="atg-metas-label">RITMO FECHADO</div>'
        f'{destaque}<div class="atg-metas-context">da meta YTD realizada</div>'
        f'</div><div class="atg-metas-support">{apoio}</div></div></section>'
    )


def _meta_anual(pulso: ResultadoPulso) -> str:
    percentual = pulso.percentual_meta_ja_vendida
    progresso = (
        '<div class="atg-metas-annual-pct"><span>Meta anual já vendida</span>'
        f'<strong>{_pct(percentual)}</strong></div>'
        '<div class="atg-metas-annual-progress" aria-hidden="true">'
        f'<div class="atg-metas-annual-fill" style="width:{min(Decimal(100), max(Decimal(0), percentual)):.2f}%"></div></div>'
        if percentual is not None else '<div class="atg-metas-context">Sem meta anual para comparar</div>'
    )
    carteira = (
        f'Inclui {_moeda(pulso.carteira_futura)} já vendidos para {_periodo_futuro(pulso)}'
        if pulso.meses_restantes else "Resultado final do ano"
    )
    gap = pulso.gap_comercial
    manchete = (
        _moeda(gap) if gap > 0 else
        f'Meta superada em {_moeda(abs(gap))}' if gap < 0 else "Meta anual atingida"
    )
    contexto_gap = "ainda precisam ser vendidos" if gap > 0 else "Compromisso anual cumprido"
    return (
        '<section class="atg-card atg-metas-annual" aria-label="Meta anual">'
        f'<h2 class="atg-metas-title">META ANUAL · {pulso.ano}</h2>'
        '<div class="atg-metas-annual-grid"><div>'
        f'<div class="atg-metas-annual-sold">{_moeda(pulso.total_vendido_ano)} já vendidos</div>'
        f'<div class="atg-metas-context">de {_moeda(pulso.meta_anual)} de meta anual · no perímetro de metas</div>'
        f'{progresso}<div class="atg-metas-context">{carteira}</div></div><div>'
        '<div class="atg-metas-label">GAP COMERCIAL</div>'
        f'<div class="atg-metas-annual-gap atg-metas-{"positive" if gap < 0 else "neutral"}">{manchete}</div>'
        f'<div class="atg-metas-annual-gap-copy">{contexto_gap}</div>'
        '<div class="atg-metas-context">Meta anual menos tudo que já está vendido.</div>'
        '</div></div></section>'
    )


def _projecao(resultado: ResultadoMetas, pulso: ResultadoPulso) -> str:
    def faixa(titulo: str, valor: str, contexto: str, *, estado: bool = False) -> str:
        classe = "atg-metas-state" if estado else "atg-metas-value"
        return (
            '<div class="atg-metas-band-cell">'
            f'<div class="atg-metas-label">{escape(titulo)}</div>'
            f'<div class="{classe} atg-metas-neutral">{valor}</div>'
            f'<div class="atg-metas-context">{contexto}</div></div>'
        )
    if not resultado.meses_restantes:
        celulas = ''.join(faixa(titulo, "Ano encerrado", "Resultado final consolidado", estado=True)
                          for titulo in ("NECESSIDADE COMERCIAL", "FORECAST", "PLANO FUTURO"))
        insight = ""
    else:
        periodo_futuro = _periodo_futuro(pulso)
        necessidade = _moeda(pulso.necessidade_media_comercial) + '/mês'
        contexto_necessidade = (
            'Meta anual já superada · saldo comercial por mês restante'
            if pulso.gap_comercial < 0 else
            'Meta anual já atingida · sem necessidade comercial adicional'
            if pulso.gap_comercial == 0 else
            'Quanto ainda precisamos conquistar por mês até dezembro'
        )
        celulas = faixa(
            "NECESSIDADE COMERCIAL", necessidade,
            f'{contexto_necessidade} · {periodo_futuro}',
        )
        cobertura = pulso.cobertura_futura_ja_vendida_pct
        contexto_plano = f'Metas planejadas para {periodo_futuro}'
        if cobertura is not None:
            contexto_plano += f' · {_pct(cobertura)} já cobertos por vendas fechadas'
        if resultado.forecast is None:
            forecast = "Dados insuficientes"
            contexto_forecast = "Run rate simples · disponível após dois meses encerrados"
        else:
            forecast = _moeda(resultado.forecast)
            contexto_forecast = 'Run rate simples pelo ritmo dos meses encerrados'
            if resultado.projetado_atingimento_pct is not None:
                contexto_forecast = f'<strong>{_pct(resultado.projetado_atingimento_pct)} da meta</strong><br>{contexto_forecast}'
            else:
                contexto_forecast += f' · {_SEM_META}'
        celulas += faixa("FORECAST", forecast, contexto_forecast, estado=resultado.forecast is None)
        celulas += faixa("PLANO FUTURO", _moeda(resultado.plano_futuro), contexto_plano)
        if pulso.meta_anual_centavos > 0 and pulso.gap_comercial > 0:
            insight = (
                '<div class="atg-metas-insight">'
                f'Para atingir a meta anual, ainda precisamos conquistar {_moeda(pulso.gap_comercial)} '
                f'até dezembro, aproximadamente {_moeda(pulso.necessidade_media_comercial)}/mês.</div>'
            )
        else:
            insight = ""
    return (
        '<section class="atg-metas-projection" aria-label="Projeção"><h2 class="atg-metas-title">Projeção</h2>'
        f'<div class="atg-card atg-metas-band">{celulas}</div>{insight}</section>'
    )


def _mostrar_erro(erro: ErroDeMetas | None) -> None:
    """Nunca reproduz mensagens de exceção nem valores recebidos da fonte."""
    if erro is not None and erro.quantidade_linhas_invalidas:
        linhas = ", ".join(str(linha) for linha in erro.linhas_invalidas)
        st.error(
            f"Não foi possível validar a aba METAS: {erro.quantidade_linhas_invalidas} "
            f"linha(s) inválida(s), na(s) linha(s) {linhas} da aba. "
            "Revise a estrutura e os campos na fonte. Nenhum KPI de metas foi consolidado."
        )
    else:
        st.error(
            "Não foi possível carregar ou validar a aba METAS. "
            "Verifique a existência, os cabeçalhos e o acesso à aba na fonte. "
            "As demais páginas continuam disponíveis."
        )


def _mostrar_graficos(resultado: ResultadoMetas, pulso: ResultadoPulso) -> None:
    for titulo, contexto, figura, chave in (
        ("Evolução Mensal",
         "Realizado nos meses encerrados · Já vendido nos meses abertos · no perímetro de metas.",
         metas_charts.evolucao_mensal(resultado, pulso), "metas_mensal"),
        ("Evolução Acumulada",
         "Como o gap se acumulou · Realizado e ano anterior no perímetro de metas.",
         metas_charts.evolucao_acumulada(resultado), "metas_acumulada"),
    ):
        with st.container(border=True):
            st.markdown(
                '<div class="atg-metas" style="margin:0">'
                f'<h2 class="atg-metas-title">{titulo}</h2>'
                f'<div class="atg-metas-context">{contexto}</div></div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(figura, width="stretch", key=chave,
                            config={"displayModeBar": False, "responsive": True})


def _atividade_parceiro(
    grupo: str, resultado: ResultadoMetas, metas_vigentes: pd.DataFrame | None = None,
) -> tuple[bool, str | None]:
    """Metadado visual da atividade já resolvida pela engine, sem novos cálculos.

    P(m) inclui metas zero ativas e respeita a precedência existente. Uma
    ausência não comprova encerramento: esse rótulo exige inatividade
    explícita na revisão vigente do mês de referência.
    """
    referencia = next(
        (mes.mes for mes in resultado.meses if mes.estado_mes == "em_andamento"),
        12 if resultado.meses_encerrados == 12 else 1,
    )
    meses_ativos = [
        mes.mes for mes in resultado.meses
        if any(entidade.grupo == grupo for entidade in mes.perimetro)
    ]
    if referencia in meses_ativos:
        return True, None
    seguintes = [mes for mes in meses_ativos if mes > referencia]
    if seguintes:
        return True, f'Meta ativa a partir de {_MESES[min(seguintes) - 1]}/{resultado.ano}'
    if not meses_ativos:
        return False, "Sem meta ativa no ano"
    ultima = f'{_MESES[max(meses_ativos) - 1]}/{resultado.ano}'
    if metas_vigentes is not None:
        linhas = metas_vigentes.loc[
            (metas_vigentes["ANO"] == resultado.ano)
            & (metas_vigentes["MES"] == referencia)
            & (metas_vigentes["GRUPO"] == grupo)
        ]
        grupo_mes = linhas[linhas["NIVEL_META"] == "GRUPO"]
        selecionadas = grupo_mes if not grupo_mes.empty else linhas
        if not selecionadas.empty and selecionadas["ATIVO"].eq("NAO").all():
            return False, f"Operação encerrada em {ultima}"
    return False, f"Última meta ativa: {ultima}"


def _parceiros(
    parceiros: tuple[ParceiroMetas, ...], pulso: ResultadoPulso,
    resultado: ResultadoMetas, metas_vigentes: pd.DataFrame | None = None,
) -> str:
    rotulos = {
        "acima_da_meta": ("✓ Acima do ritmo", "positive"),
        "proximo_da_meta": ("≈ No ritmo", "neutral"),
        "abaixo_da_meta": ("↓ Abaixo do ritmo", "negative"),
        "sem_meta_periodo": ("— Sem meta no período", "neutral"),
        "aguardando_mes_encerrado": ("— Aguardando mês encerrado", "neutral"),
    }
    ordenados = sorted(parceiros, key=lambda p: (
        p.atingimento_ytd_pct is None,
        -(p.atingimento_ytd_pct or Decimal(0)), p.grupo,
    ))
    atividade = {
        parceiro.grupo: _atividade_parceiro(parceiro.grupo, resultado, metas_vigentes)
        for parceiro in ordenados
    }
    ativos = [parceiro for parceiro in ordenados if atividade[parceiro.grupo][0]]
    inativos = [parceiro for parceiro in ordenados if not atividade[parceiro.grupo][0]]
    escala = Decimal(125)  # Limite exclusivamente visual; o percentual real continua explícito.

    def linha(parceiro: ParceiroMetas) -> str:
        ativo, contexto_operacao = atividade[parceiro.grupo]
        rotulo, classe = rotulos[parceiro.status]
        if not ativo:
            rotulo, classe = contexto_operacao, "neutral"
        pct = parceiro.atingimento_ytd_pct
        percentual = _pct(pct) if pct is not None else "—"
        largura = format(min(escala, max(Decimal(0), pct or Decimal(0))) / escala * 100, '.2f')
        compromisso = parceiro.pulso
        anual = compromisso.percentual_meta_ja_vendida
        saldo = parceiro.saldo_ytd
        saldo_rotulo = "Superávit YTD" if saldo > 0 else "Déficit YTD" if saldo < 0 else "Saldo YTD"
        detalhes = (
            ("Meta anual", _moeda(compromisso.meta_anual)),
            (f"Já vendido para {pulso.ano}", _moeda(compromisso.total_vendido_ano)),
            ("Da meta anual já vendida", _pct(anual) if anual is not None else _SEM_META),
            (f"Já vendido · {_periodo_futuro(pulso)}", _moeda(compromisso.ja_vendido_meses_restantes)),
            ("Gap comercial" if compromisso.gap_comercial >= 0 else "Meta anual superada em", _moeda(abs(compromisso.gap_comercial))),
            (saldo_rotulo, _moeda(abs(saldo))),
        )
        detalhes_html = ''.join(
            f'<div><div class="atg-metas-label">{escape(titulo)}</div>'
            f'<div class="atg-metas-detail-value">{valor}</div></div>'
            for titulo, valor in detalhes
        )
        comparacao = (
            f'{_moeda(parceiro.realizado_ytd)} / {_moeda(parceiro.meta_ytd)} YTD'
            if pulso.meses_encerrados else _AGUARDANDO
        )
        complemento = (
            f' · {escape(contexto_operacao)}' if ativo and contexto_operacao else
            ' · Realizado zero no período' if ativo and pulso.meses_encerrados and parceiro.realizado_ytd == 0 else ""
        )
        classe_operacao = "" if ativo else " atg-metas-partner-inactive"
        return (
            f'<article class="atg-metas-partner{classe_operacao}" aria-label="{escape(parceiro.grupo, quote=True)}" '
            f'data-pct-ytd="{pct if pct is not None else ""}" data-scale-max="125">'
            '<div class="atg-metas-partner-head"><div class="atg-metas-partner-heading">'
            f'<div class="atg-metas-partner-name">{escape(parceiro.grupo)}</div>'
            f'<div class="atg-metas-partner-status atg-metas-{classe}">{rotulo}</div></div>'
            f'<div class="atg-metas-partner-pct">{percentual}</div></div>'
            f'<div class="atg-metas-partner-comparison">{comparacao}{complemento}</div>'
            f'<div class="atg-metas-progress" aria-hidden="true"><div class="atg-metas-progress-fill" style="width:{largura}%"></div>'
            '<span class="atg-metas-progress-reference"></span></div>'
            '<details><summary>Compromisso anual e saldo</summary>'
            f'<div class="atg-metas-partner-details">{detalhes_html}</div></details></article>'
        )
    resumo = [f'{len(ativos)} parceiros ativos']
    for estado, texto in (
        ("acima_da_meta", "acima do ritmo"), ("proximo_da_meta", "no ritmo"),
        ("abaixo_da_meta", "abaixo do ritmo"),
    ):
        quantidade = sum(parceiro.status == estado for parceiro in ativos)
        if quantidade:
            resumo.append(f'{quantidade} {texto}')
    grupos = (
        '<h3 class="atg-metas-partner-group">Parceiros ativos</h3>'
        '<div class="atg-card atg-metas-partners">'
        '<div class="atg-metas-scale"><span>100% da meta YTD</span></div>'
        + (''.join(linha(parceiro) for parceiro in ativos) if ativos else
           '<div class="atg-metas-context" style="padding:12px 0">Sem parceiros com meta ativa no período.</div>')
        + '</div>'
    )
    if inativos:
        grupos += (
            '<h3 class="atg-metas-partner-group">Fora da operação</h3>'
            '<div class="atg-card atg-metas-partners">'
            '<div class="atg-metas-scale"><span>100% da meta YTD</span></div>'
            + ''.join(linha(parceiro) for parceiro in inativos) + '</div>'
        )
    return (
        '<section class="atg-metas" aria-label="Metas por parceiro">'
        '<h2 class="atg-metas-title">Metas por parceiro</h2>'
        f'<div class="atg-metas-context">{" · ".join(resumo)}</div>'
        f'<div class="atg-metas-context">{_periodo(pulso.meses_encerrados, pulso.ano)} · Realizado no perímetro de metas.</div>'
        f'{grupos}</section>'
    )


def _mostrar_alertas(alertas: tuple[AlertaQualidade, ...]) -> None:
    ativos = tuple(alerta for alerta in alertas if alerta.possui_ocorrencias)
    if not ativos:
        return
    with st.expander(f"Alertas de Qualidade ({len(ativos)} ativos)", expanded=False):
        st.caption("Referentes ao ano selecionado. A consolidação segue a revisão vigente e a precedência de Grupo; a correção é manual na fonte.")
        for alerta in ativos:
            st.markdown(f"**{alerta.titulo}**: {alerta.quantidade}")
            linhas = sorted(set(int(linha) for linha in alerta.linhas[COL_LINHA_ORIGEM]))
            st.caption("Linhas da aba METAS: " + ", ".join(str(linha) for linha in linhas))


def _rodape() -> None:
    st.markdown(
        '<div class="atg-metas atg-metas-footer">'
        'Realizado = Vendas Líquidas, mês de veiculação, somente meses encerrados '
        'e entidades com meta ativa no mês. Meta = soma das metas vigentes por grupo ou veículo. '
        'Forecast = run rate simples, sem sazonalidade. Para vendas totais, consultar Performance Comercial.'
        '</div>', unsafe_allow_html=True,
    )


def render(
    df: pd.DataFrame,
    metas_df: pd.DataFrame | None = None,
    *,
    erro_metas: ErroDeMetas | None = None,
    data_referencia: dt.date | dt.datetime | None = None,
) -> None:
    """Renderiza apenas esta visão; falhas de METAS não encerram a aplicação."""
    st.markdown(_CSS, unsafe_allow_html=True)
    if df.empty:
        st.info("Sem dados de vendas disponíveis para selecionar um ano.")
        return
    with st.columns([1, 3])[0]:
        ano = filters.selecionar_ano(df, "metas")
    if erro_metas is not None or metas_df is None:
        _mostrar_erro(erro_metas)
        _rodape()
        return
    try:
        base_metas = validar_metas(metas_df, data_referencia=data_referencia)
        resultado = avaliar_metas(df, base_metas, ano, data_referencia=data_referencia)
        pulso = avaliar_pulso(df, base_metas, ano, data_referencia=data_referencia)
        parceiros = avaliar_parceiros(df, base_metas, ano, data_referencia=data_referencia)
        metas_vigentes = vigencia(base_metas, data_referencia=data_referencia)
        metas_ano = base_metas[base_metas["ANO"] == ano]
        alertas = (
            revisoes_retroativas(metas_ano, data_referencia=data_referencia),
            coexistencia_niveis(metas_ano, data_referencia=data_referencia),
        )
    except ErroDeMetas as erro:
        _mostrar_erro(erro)
        _rodape()
        return
    if resultado.estado == "sem_metas":
        st.markdown(
            '<div class="atg-metas atg-card atg-metas-empty">'
            f'<div class="atg-metas-state">{_SEM_META}</div>'
            f'<div class="atg-metas-context">Não há metas cadastradas para {ano}. '
            'Os indicadores de cumprimento de meta não estão disponíveis.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="atg-metas">{_hero(resultado)}{_meta_anual(pulso)}{_projecao(resultado, pulso)}</div>',
            unsafe_allow_html=True,
        )
        _mostrar_graficos(resultado, pulso)
        st.markdown(_parceiros(parceiros, pulso, resultado, metas_vigentes), unsafe_allow_html=True)
    _mostrar_alertas(alertas)
    _rodape()
