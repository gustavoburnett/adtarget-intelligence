"""KPI cards e formatação pt-BR reutilizáveis.

Este módulo NÃO calcula nada: recebe valores prontos de metrics.py e apenas
formata/exibe. Comportamentos obrigatórios:
- recorte vazio exibe "R$ 0,00" ou "Sem dados no recorte selecionado"
- comparativo indisponível exibe "sem comparativo disponível", nunca erro

Formatação executiva (v0.5 Sprint 1) — vale para TODOS os cards monetários
das 3 páginas:
- >= R$ 1.000.000  -> "R$ X,XX Mi"
- >= R$ 1.000      -> "R$ X,XX mil"  (nunca "K")
- <  R$ 1.000      -> valor completo
Arredondamento pelo valor mais próximo (ROUND_HALF_UP), nunca truncado.
Tooltips, tabelas analíticas e auditoria continuam com o valor completo.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

import streamlit as st

SEM_DADOS = "Sem dados no recorte selecionado"
SEM_COMPARATIVO = "Sem comparativo disponível"

# ---------------------------------------------------------------------------
# Design Tokens — Sprint 2B (docs/09, seção 5; mockup aprovado)
# Semântica de cor [REGRA PERMANENTE]: verde = desempenho positivo;
# vermelho = queda/alerta; âmbar = pipeline/atenção; MARCA = identidade,
# navegação e seleção (nunca desempenho).
# ---------------------------------------------------------------------------
COR_MARCA = "#0B7A66"
COR_MARCA_SUAVE = "#E7F3F0"
COR_POSITIVO = "#1E9E52"
COR_POSITIVO_SUAVE = "#E9F8EE"
COR_NEGATIVO = "#DC4545"
COR_AMBAR = "#C97F12"
COR_NEUTRO = "#8B93A1"
COR_TEXTO = "#14171C"
COR_TEXTO_SECUNDARIO = "#5B6472"
COR_BORDA_SUAVE = "#EDEFF2"

#: CSS global da Sprint 2B — injetado uma vez pelo app.py
CSS_GLOBAL = """
<style>
[class^="atg-"],[class^="atg-"] *{
  font-family:-apple-system,BlinkMacSystemFont,"Inter","Segoe UI",Roboto,
  Helvetica,Arial,sans-serif;}
.num{font-variant-numeric:tabular-nums;}
.atg-card{background:#FFFFFF;border:1px solid #EDEFF2;border-radius:12px;
  box-shadow:0 1px 2px rgba(20,23,28,.04),0 1px 3px rgba(20,23,28,.05);}
/* ---- masthead ---- */
.atg-h1{font-size:23px;font-weight:700;letter-spacing:-.01em;color:#14171C;margin:0;}
.atg-sub{font-size:13.5px;color:#5B6472;margin-top:3px;}
.atg-updated{font-size:11.5px;color:#8B93A1;text-align:right;}
/* ---- KPI row ---- */
.atg-kpi-row{display:flex;gap:16px;align-items:stretch;margin:6px 0 18px;}
.atg-kpi-hero{flex:1.55;padding:24px 26px;display:flex;flex-direction:column;justify-content:center;}
.atg-eyebrow{font-size:11px;font-weight:700;letter-spacing:.06em;color:#0B7A66;text-transform:uppercase;margin-bottom:10px;}
.atg-hero-value{display:flex;align-items:baseline;gap:10px;}
.atg-hero-arrow{font-size:26px;}
.atg-hero-number{font-size:42px;font-weight:700;letter-spacing:-.02em;line-height:1.05;}
.atg-hero-caption{font-size:12.5px;color:#5B6472;margin-top:10px;}
.atg-kpi-sec{flex:1;padding:20px 20px 18px;display:flex;flex-direction:column;gap:10px;}
.atg-kpi-label{font-size:12px;font-weight:600;color:#8B93A1;}
.atg-kpi-value{font-size:27px;font-weight:600;letter-spacing:-.01em;color:#14171C;}
.atg-kpi-value.positivo{color:#1E9E52;}
.atg-kpi-value.ambar{color:#C97F12;}
.atg-kpi-caption{font-size:11.5px;color:#8B93A1;}
/* ---- insights ---- */
.atg-insights{display:flex;gap:14px;margin-bottom:18px;}
.atg-insight{flex:1;background:#FAFBFC;border:1px solid #EDEFF2;border-radius:12px;
  padding:13px 16px;display:flex;align-items:flex-start;gap:10px;
  font-size:12.5px;color:#5B6472;line-height:1.4;}
.atg-insight .ic{font-size:15px;line-height:1;margin-top:1px;}
/* ---- rankings ---- */
.atg-rank{padding:20px 20px 8px;}
.atg-rank-title{font-size:14px;font-weight:700;color:#14171C;margin-bottom:14px;}
.atg-rank-row{display:flex;align-items:center;gap:8px;margin-bottom:12px;}
.atg-rank-name{font-size:12px;color:#5B6472;width:34%;flex-shrink:0;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.atg-rank-barwrap{flex:1;background:#F5F6F8;border-radius:5px;height:8px;}
.atg-rank-bar{height:8px;border-radius:5px;background:#0B7A66;}
.atg-rank-value{font-size:12px;font-weight:700;color:#14171C;flex-shrink:0;}
.atg-rank-pct{font-size:11px;color:#8B93A1;width:34px;flex-shrink:0;text-align:right;}
.atg-trend{font-size:11px;font-weight:700;width:48px;flex-shrink:0;text-align:right;}
.atg-trend.alta{color:#1E9E52;}
.atg-trend.queda{color:#DC4545;}
.atg-trend.neutro{color:#8B93A1;font-weight:600;}
/* ---- sidebar (logo + nav estilizada sobre o radio nativo) ---- */
[data-testid="stSidebar"] div[role="radiogroup"] label>div:first-child{display:none;}
[data-testid="stSidebar"] div[role="radiogroup"]{gap:2px;}
[data-testid="stSidebar"] div[role="radiogroup"] label{
  padding:10px 12px;border-radius:8px;border-left:3px solid transparent;
  width:100%;margin:0;cursor:pointer;}
[data-testid="stSidebar"] div[role="radiogroup"] label p{
  font-size:13.5px;font-weight:500;color:#5B6472;}
[data-testid="stSidebar"] div[role="radiogroup"] label:hover{background:#FAFBFC;}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){
  background:#E7F3F0;border-left:3px solid #0B7A66;}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p{
  color:#0B7A66;font-weight:600;}
.atg-logo-word{font-size:19px;font-weight:700;color:#14171C;line-height:1.1;}
.atg-logo-word b{color:#0B7A66;}
.atg-logo-sub{font-size:10px;letter-spacing:.14em;color:#8B93A1;font-weight:600;}
.atg-status-line{display:flex;align-items:center;gap:6px;font-size:12.5px;font-weight:600;color:#14171C;}
.atg-status-dot{width:7px;height:7px;border-radius:50%;background:#1E9E52;
  box-shadow:0 0 0 3px #E9F8EE;display:inline-block;}
.atg-status-caption{font-size:11.5px;color:#8B93A1;margin-left:13px;}
</style>
"""

#: Nomes completos dos meses (cápsulas de insight)
MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
               "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

#: Abreviações de mês para o rótulo do período comparado
_MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


# ---------------------------------------------------------------------------
# Formatação pt-BR
# ---------------------------------------------------------------------------

def _numero_ptbr(valor: Decimal | float) -> str:
    return f"{valor:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def formatar_moeda(valor: Optional[float]) -> str:
    """Valor COMPLETO em R$ pt-BR (tabelas, tooltips, auditoria)."""
    if valor is None:
        return SEM_DADOS
    return f"R$ {_numero_ptbr(valor)}"


def _quantizar(valor: float) -> Decimal:
    """Arredonda para 2 casas pelo valor mais próximo (nunca trunca)."""
    return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def formatar_moeda_executiva(valor: Optional[float]) -> str:
    """Formatação executiva dos cards (v0.5): Mi / mil / valor completo.

    Regras: >= 1 milhão -> "R$ X,XX Mi"; >= 1 mil -> "R$ X,XX mil";
    abaixo disso, valor completo. Nunca "K". Arredondamento half-up; se o
    arredondamento promover a faixa (ex: 999.995 -> 1.000,00 mil), o valor
    sobe de unidade ("R$ 1,00 Mi"), nunca exibindo mil >= 1.000.
    """
    if valor is None:
        return SEM_DADOS
    sinal = "-" if valor < 0 else ""
    v = abs(valor)

    if v >= 1_000_000:
        return f"{sinal}R$ {_numero_ptbr(_quantizar(v / 1_000_000))} Mi"
    if v >= 1_000:
        em_mil = _quantizar(v / 1_000)
        if em_mil >= 1000:  # promoção de faixa pelo arredondamento
            return f"{sinal}R$ {_numero_ptbr(_quantizar(v / 1_000_000))} Mi"
        return f"{sinal}R$ {_numero_ptbr(em_mil)} mil"
    return f"{sinal}R$ {_numero_ptbr(_quantizar(v))}"


def formatar_pct(valor: Optional[float]) -> str:
    """Formata percentual com sinal e uma casa decimal (+12,3% / -4,5%)."""
    if valor is None:
        return SEM_COMPARATIVO
    texto = f"{valor:+.1f}".replace(".", ",")
    return f"{texto}%"


def formatar_inteiro(valor: int) -> str:
    """Formata inteiro com separador de milhar pt-BR."""
    return f"{valor:,}".replace(",", ".")


def rotulo_periodo(mes_limite: int, ano: int) -> str:
    """Rótulo do intervalo comparado: "Jan–Jul/2025" ou "Jan–Dez/2025"."""
    return f"Jan–{_MESES_ABREV[mes_limite - 1]}/{ano}"


# ---------------------------------------------------------------------------
# Cards padrão (st.metric) — formato executivo + valor completo no tooltip
# ---------------------------------------------------------------------------

def card_moeda(
    titulo: str, valor: Optional[float], legenda: str | None = None
) -> None:
    """Card monetário: valor executivo no card, completo no tooltip."""
    if valor is None:
        st.metric(titulo, SEM_DADOS)
    else:
        st.metric(
            titulo,
            formatar_moeda_executiva(valor),
            help=formatar_moeda(valor),
        )
    if legenda:
        st.caption(legenda)


def card_numero(titulo: str, valor: Optional[float], legenda: str | None = None) -> None:
    """Card de contagem/quantidade (número inteiro, sem abreviação)."""
    if valor is None:
        st.metric(titulo, "—")
        st.caption(SEM_DADOS)
    else:
        st.metric(titulo, formatar_inteiro(int(valor)))
        if legenda:
            st.caption(legenda)


def card_cancelado_bonificado(resultado: dict) -> None:
    """Bloco de Cancelado/Bonificado: CONTAGEM de PIs como número principal;
    valor monetário só como informação secundária, quando diferente de zero."""
    st.metric(
        "Cancelado / Bonificado",
        f"{resultado['cancelados']} canc. | {resultado['bonificados']} bonif.",
    )
    valor_secundario = resultado.get("valor_bruto_secundario", 0.0)
    if valor_secundario:
        st.caption(
            f"Atenção: {formatar_moeda_executiva(valor_secundario)} bruto em "
            "PIs cancelados/bonificados (esperado: zero — ver Alertas)"
        )


# ---------------------------------------------------------------------------
# Card YTD de destaque (v0.5 Sprint 1) — apenas fatos, sem interpretação
# ---------------------------------------------------------------------------

def montar_ytd(
    ytd_resultado: dict, ano: int, sem_dados: bool = False
) -> dict[str, str]:
    """Monta as peças FACTUAIS do card YTD (função pura, testável).

    O período usa SEMPRE o mes_limite retornado por metrics.ytd() — a regra
    oficial v0.4 (mês atual no ano corrente; Dez em ano encerrado) — nunca
    "último mês com dado", que reintroduziria meses futuros no acumulado.

    Retorna dict com: estado, periodo, seta, percentual, cor, suporte.
    Estados: "ok" | "sem_comparativo" | "sem_dados".
    Nenhuma frase interpretativa é gerada — apenas fatos.
    """
    mes_limite = ytd_resultado.get("mes_limite") or 12
    periodo = (
        f"Acumulado {rotulo_periodo(mes_limite, ano)} "
        f"vs {rotulo_periodo(mes_limite, ano - 1)}"
    )

    if sem_dados:
        return {
            "estado": "sem_dados",
            "periodo": periodo,
            "seta": "",
            "percentual": "—",
            "cor": COR_NEUTRO,
            "suporte": "Sem dados no recorte selecionado.",
        }

    atual = ytd_resultado.get("atual", 0.0)
    anterior = ytd_resultado.get("anterior")

    if anterior is None:
        return {
            "estado": "sem_comparativo",
            "periodo": f"Acumulado {rotulo_periodo(mes_limite, ano)}",
            "seta": "",
            "percentual": formatar_moeda_executiva(atual),
            "cor": COR_NEUTRO,
            "suporte": "Sem comparativo disponível para este ano.",
        }

    variacao = ytd_resultado.get("variacao_pct")
    if variacao is None:  # anterior == 0: percentual seria divisão por zero
        seta, cor, percentual = "", COR_NEUTRO, "—"
    elif variacao > 0:
        seta, cor = "▲", COR_POSITIVO
        percentual = f"{variacao:.1f}".replace(".", ",") + "%"
    elif variacao < 0:
        seta, cor = "▼", COR_NEGATIVO
        percentual = f"{abs(variacao):.1f}".replace(".", ",") + "%"
    else:
        seta, cor, percentual = "", COR_NEUTRO, "0,0%"

    suporte = (
        f"{formatar_moeda_executiva(atual)} este ano · "
        f"{formatar_moeda_executiva(anterior)} no mesmo período de {ano - 1}"
    )
    return {
        "estado": "ok",
        "periodo": periodo,
        "seta": seta,
        "percentual": percentual,
        "cor": cor,
        "suporte": suporte,
    }


def card_ytd(
    titulo: str, ytd_resultado: dict, ano: int, sem_dados: bool = False
) -> None:
    """Card YTD de destaque (v0.5): frase de período, percentual com seta e
    cor de sentimento (~25% maior que os demais valores), valores absolutos
    de suporte em formato executivo, borda lateral fina na cor do
    sentimento. Mesma célula da grade dos demais cards.

    ``titulo`` é mantido na assinatura por compatibilidade, mas a
    identidade visual do card é a própria frase de período (spec v0.5).
    """
    pecas = montar_ytd(ytd_resultado, ano, sem_dados)
    seta_html = f"{pecas['seta']} " if pecas["seta"] else ""
    html = (
        f'<div style="border-left: 3px solid {pecas["cor"]}; '
        'padding: 0.15rem 0 0.15rem 0.75rem; margin-bottom: 0.25rem;">'
        f'<div style="font-size: 0.8rem; color: {COR_NEUTRO};">'
        f'{pecas["periodo"]}</div>'
        f'<div style="font-size: 2.8rem; font-weight: 700; line-height: 1.15; '
        f'color: {pecas["cor"]};">{seta_html}{pecas["percentual"]}</div>'
        f'<div style="font-size: 0.8rem; color: rgb(49, 51, 63);">'
        f'{pecas["suporte"]}</div>'
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sprint 2B — Masthead, linha de KPIs, Insights e Rankings (mockup aprovado)
# Renderizadores puros de apresentação: recebem valores prontos de
# metrics.py e apenas montam HTML. Tooltips (title=) trazem o valor completo.
# ---------------------------------------------------------------------------

def masthead(titulo: str, subtitulo: str) -> None:
    """Bloco esquerdo do Masthead (título + subtítulo). Ações ficam no app."""
    st.markdown(
        f'<div class="atg-h1">{titulo}</div>'
        f'<div class="atg-sub">{subtitulo}</div>',
        unsafe_allow_html=True,
    )


def _card_secundario(
    rotulo: str, valor: Optional[float], caption: str, classe: str = ""
) -> str:
    if valor is None:
        exibido, completo = SEM_DADOS, ""
    else:
        exibido = formatar_moeda_executiva(valor)
        completo = formatar_moeda(valor)
    return (
        '<div class="atg-card atg-kpi-sec">'
        f'<div class="atg-kpi-label">{rotulo}</div>'
        f'<div class="atg-kpi-value num {classe}" title="{completo}">{exibido}</div>'
        f'<div class="atg-kpi-caption">{caption}</div>'
        "</div>"
    )


def linha_kpis(
    ytd_resultado: dict,
    ano: int,
    sem_dados: bool,
    vendas_detalhado: dict,
    valor_em_aberto: float,
    valor_ticket: Optional[float],
    qtd_campanhas: int,
) -> None:
    """Linha única de KPIs (2B.5): Card Hero YTD + 4 secundários, mesma
    grade e altura (flex). Nomenclatura oficial v0.3 (adendo C1/C2)."""
    pecas = montar_ytd(ytd_resultado, ano, sem_dados)
    seta = f'<span class="atg-hero-arrow" style="color:{pecas["cor"]}">{pecas["seta"]}</span>' if pecas["seta"] else ""
    hero = (
        '<div class="atg-card atg-kpi-hero">'
        '<div class="atg-eyebrow">KPI Principal · YTD vs Ano Anterior</div>'
        f'<div class="atg-hero-value">{seta}'
        f'<span class="atg-hero-number num" style="color:{pecas["cor"]}">'
        f'{pecas["percentual"]}</span></div>'
        f'<div class="atg-hero-caption num">{pecas["suporte"]}</div>'
        "</div>"
    )
    faturado_fmt = formatar_moeda_executiva(vendas_detalhado["faturado"])
    cards_html = [
        hero,
        _card_secundario(
            "Vendas", vendas_detalhado["total"],
            f"sendo {faturado_fmt} já faturado", classe="positivo",
        ),
        _card_secundario(
            "Em Aberto", valor_em_aberto,
            "vendido, ainda não faturado", classe="ambar",
        ),
        _card_secundario("Ticket Médio", valor_ticket, "Vendas ÷ PIs da base"),
        (
            '<div class="atg-card atg-kpi-sec">'
            '<div class="atg-kpi-label">Campanhas</div>'
            f'<div class="atg-kpi-value num">{formatar_inteiro(qtd_campanhas)}</div>'
            '<div class="atg-kpi-caption">Cliente + Campanha distintos</div>'
            "</div>"
        ),
    ]
    st.markdown(
        '<div class="atg-kpi-row">' + "".join(cards_html) + "</div>",
        unsafe_allow_html=True,
    )


def capsulas_insights(destaques: dict) -> None:
    """Faixa de Insights (2B.6): até 4 cápsulas factuais derivadas de
    métricas oficiais — nunca repetem número de card ao lado."""
    textos: list[str] = []
    if destaques.get("concentracao"):
        grupo, pct = destaques["concentracao"]
        pct_txt = f"{pct:.0f}".replace(".", ",")
        textos.append(
            f"{grupo} concentra {pct_txt}% das vendas no recorte selecionado"
        )
    if destaques.get("maior_mes"):
        mes, valor = destaques["maior_mes"]
        textos.append(
            f"{MESES_NOMES[mes - 1]} concentrou o maior volume do ano, "
            f"com {formatar_moeda_executiva(valor)}"
        )
    if destaques.get("maior_queda"):
        mes, mes_ant, variacao = destaques["maior_queda"]
        var_txt = f"{variacao:.0f}".replace(".", ",")
        textos.append(
            f"{MESES_NOMES[mes - 1]} teve a maior queda mês a mês do "
            f"período, {var_txt}% vs {MESES_NOMES[mes_ant - 1]}"
        )
    if not textos:
        return
    capsulas = "".join(
        f'<div class="atg-insight"><span class="ic">💡</span>{t}</div>'
        for t in textos[:4]
    )
    st.markdown(
        f'<div class="atg-insights">{capsulas}</div>', unsafe_allow_html=True
    )


def _badge_tendencia(variacao: Optional[float]) -> str:
    """Badge ▲/▼ + % (Variante 1 aprovada). None -> neutro, nunca % quebrado."""
    if variacao is None:
        return '<span class="atg-trend neutro">—</span>'
    pct = f"{abs(variacao):.0f}".replace(".", ",")
    if variacao > 0:
        return f'<span class="atg-trend alta num">▲{pct}%</span>'
    if variacao < 0:
        return f'<span class="atg-trend queda num">▼{pct}%</span>'
    return '<span class="atg-trend neutro num">0%</span>'


def bloco_ranking(titulo: str, linhas: list[dict]) -> None:
    """Ranking Top 5 (2B.8): nome, barra, valor, % e badge de tendência —
    tudo inline, nada dependente de hover.

    ``linhas``: [{"nome", "valor", "pct", "tendencia"}], já ordenadas.
    """
    if not linhas:
        st.markdown(
            f'<div class="atg-card atg-rank"><div class="atg-rank-title">'
            f'{titulo}</div><div class="atg-kpi-caption">{SEM_DADOS}</div></div>',
            unsafe_allow_html=True,
        )
        return
    maximo = max(item["valor"] for item in linhas) or 1.0
    linhas_html = []
    for item in linhas:
        largura = max(2, round(item["valor"] / maximo * 100))
        pct_txt = f"{item['pct']:.0f}".replace(".", ",")
        linhas_html.append(
            '<div class="atg-rank-row">'
            f'<div class="atg-rank-name" title="{item["nome"]}">{item["nome"]}</div>'
            f'<div class="atg-rank-barwrap"><div class="atg-rank-bar" '
            f'style="width:{largura}%"></div></div>'
            f'<span class="atg-rank-value num" '
            f'title="{formatar_moeda(item["valor"])}">'
            f'{formatar_moeda_executiva(item["valor"])}</span>'
            f'<span class="atg-rank-pct num">{pct_txt}%</span>'
            f'{_badge_tendencia(item["tendencia"])}'
            "</div>"
        )
    st.markdown(
        f'<div class="atg-card atg-rank"><div class="atg-rank-title">{titulo}'
        "</div>" + "".join(linhas_html) + "</div>",
        unsafe_allow_html=True,
    )
