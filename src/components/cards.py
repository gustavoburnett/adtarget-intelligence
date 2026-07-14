"""KPI cards, formatação pt-BR e fundação visual (Design System v0.5+).

Este módulo NÃO calcula nada: recebe valores prontos de metrics.py e apenas
formata/exibe. Comportamentos obrigatórios:
- recorte vazio exibe "R$ 0,00" ou "Sem dados no recorte selecionado"
- comparativo indisponível exibe "sem comparativo disponível", nunca erro

Formatação executiva (v0.5 Sprint 1) — todos os cards monetários:
>= R$ 1 mi -> "R$ X,XX Mi"; >= R$ 1 mil -> "R$ X,XX mil"; abaixo, valor
completo. ROUND_HALF_UP, nunca truncado. Tooltips/tabelas/auditoria com
valor completo.

Sprint 3B (design de produto): CSS consolidado em folha única no grid de
8pt — faixa de contexto compacta, toolbar executiva (ghost), KPI band com
stat strip (menos bordas), insights como linhas de texto, gráficos e
sidebar refinados, chrome do Streamlit oculto. Tokens e semântica de cor
do DS preservados; nenhuma regra/número muda.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

import streamlit as st

SEM_DADOS = "Sem dados no recorte selecionado"
SEM_COMPARATIVO = "Sem comparativo disponível"

# ---------------------------------------------------------------------------
# Design Tokens (DS §5.4 — semântica permanente)
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

#: CSS global — Sprint 3B: folha única, grid 8pt, injetada pelo app.py
CSS_GLOBAL = """
<style>
[class^="atg-"],[class^="atg-"] *{
  font-family:-apple-system,BlinkMacSystemFont,"Inter","Segoe UI",Roboto,
  Helvetica,Arial,sans-serif;}
.num{font-variant-numeric:tabular-nums;}
/* ---- P8: apagar o chrome do Streamlit ---- */
header[data-testid="stHeader"]{display:none;}
#MainMenu,footer{visibility:hidden;}
[data-testid="stMainBlockContainer"]{padding-top:32px;max-width:1400px;}
[data-testid="stMain"] .block-container{padding-bottom:48px;}
/* ---- P1/P4: faixa de contexto — título com presença, sem subtítulo fixo */
.atg-h1{font-size:22px;font-weight:700;letter-spacing:-.01em;color:#14171C;
  line-height:1.2;margin:0;}
.atg-updated{font-size:12px;color:#8B93A1;text-align:right;}
/* ---- P2: toolbar executiva — filtros ghost, formulário zero ---- */
div[data-testid="stPopover"]>div>button{
  width:100%;justify-content:space-between;background:transparent;
  border:1px solid transparent;border-radius:8px;min-height:40px;
  font-size:13px;font-weight:500;color:#14171C;box-shadow:none;
  padding:8px 8px;}
div[data-testid="stPopover"]>div>button:hover{
  background:#FFFFFF;border-color:#E3E6EA;color:#0B7A66;}
div[data-testid="stPopoverBody"]{min-width:328px;}
div[data-testid="stPopoverBody"] .stCheckbox{margin-bottom:-8px;}
div[data-testid="stPopoverBody"] .stCheckbox p{font-size:13px;}
.atg-filtro-contador{font-size:12px;color:#5B6472;text-align:right;
  font-variant-numeric:tabular-nums;}
.atg-filtro-pendente{font-size:12px;color:#C97F12;font-weight:600;
  margin:0 0 8px;}
/* ---- P3: KPI band — hero + stat strip (superfície única) ---- */
.atg-card{background:#FFFFFF;border:1px solid #F0F2F4;border-radius:12px;
  box-shadow:none;transition:box-shadow .15s ease;}
.atg-card:hover{box-shadow:0 2px 8px rgba(20,23,28,.06);}
.atg-kpi-row{display:flex;gap:16px;align-items:stretch;margin:8px 0 24px;}
.atg-kpi-hero{flex:1.35;padding:24px;display:flex;flex-direction:column;
  justify-content:center;}
.atg-eyebrow{font-size:11px;font-weight:700;letter-spacing:.08em;
  color:#0B7A66;text-transform:uppercase;margin-bottom:8px;}
.atg-hero-value{display:flex;align-items:baseline;gap:8px;}
.atg-hero-arrow{font-size:24px;}
.atg-hero-number{font-size:38px;font-weight:700;letter-spacing:-.02em;
  line-height:1.1;}
.atg-hero-caption{font-size:12px;color:#5B6472;margin-top:8px;}
.atg-statstrip{flex:3.2;display:flex;align-items:stretch;background:#FFFFFF;
  border:1px solid #F0F2F4;border-radius:12px;}
.atg-stat{flex:1;padding:24px 24px 16px;min-width:0;}
.atg-stat+.atg-stat{border-left:1px solid #F0F2F4;}
.atg-kpi-label{font-size:11px;font-weight:600;color:#8B93A1;
  letter-spacing:.02em;}
.atg-kpi-value{font-size:24px;font-weight:600;letter-spacing:-.01em;
  color:#14171C;white-space:nowrap;margin-top:8px;}
.atg-kpi-value.positivo{color:#1E9E52;}
.atg-kpi-value.ambar{color:#C97F12;}
.atg-kpi-caption{font-size:11px;color:#8B93A1;margin-top:8px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
/* ---- P5: insights — linha ambiente, sem caixa ---- */
.atg-insights{display:flex;gap:24px;margin:0 0 24px;padding:0 4px;}
.atg-insight{flex:1;display:flex;align-items:center;gap:8px;
  font-size:12.5px;color:#5B6472;line-height:1.45;background:transparent;
  border:none;padding:0;}
.atg-insight .ic{display:flex;flex-shrink:0;}
/* ---- rankings ---- */
.atg-rank{padding:24px 24px 16px;}
.atg-rank-title{font-size:14px;font-weight:700;color:#14171C;
  margin-bottom:16px;}
.atg-rank-row{display:flex;align-items:center;gap:8px;margin-bottom:16px;}
.atg-rank-name{font-size:12px;color:#5B6472;width:27%;flex-shrink:0;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.atg-rank-barwrap{flex:1;min-width:56px;background:#F5F6F8;border-radius:6px;
  height:8px;}
.atg-rank-bar{height:8px;border-radius:6px;background:#0B7A66;}
.atg-rank-value{font-size:12px;font-weight:700;color:#14171C;flex-shrink:0;
  min-width:62px;text-align:right;}
.atg-rank-pct{font-size:11px;color:#8B93A1;width:30px;flex-shrink:0;
  text-align:right;}
.atg-trend{font-size:11px;font-weight:700;width:44px;flex-shrink:0;
  text-align:right;}
.atg-trend.alta{color:#1E9E52;}
.atg-trend.queda{color:#DC4545;}
.atg-trend.neutro{color:#8B93A1;font-weight:600;}
/* ---- P7: sidebar ---- */
section[data-testid="stSidebar"]{width:248px !important;}
[data-testid="stSidebar"] div[role="radiogroup"]{gap:2px;}
[data-testid="stSidebar"] div[role="radiogroup"] label>div:first-child{display:none;}
[data-testid="stSidebar"] div[role="radiogroup"] label{
  padding:8px 12px;border-radius:8px;width:100%;margin:0;cursor:pointer;}
[data-testid="stSidebar"] div[role="radiogroup"] label p{
  font-size:13px;font-weight:500;color:#5B6472;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;}
[data-testid="stSidebar"] div[role="radiogroup"] label:hover{background:#FAFBFC;}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){
  background:#E7F3F0;}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p{
  color:#0B7A66;font-weight:600;}
[data-testid="stSidebar"] hr{margin:16px 0;}
.atg-logo-word{font-size:17px;font-weight:700;color:#14171C;line-height:1.15;
  margin-top:8px;}
.atg-logo-word b{color:#0B7A66;}
.atg-logo-sub{font-size:9.5px;letter-spacing:.14em;color:#8B93A1;
  font-weight:600;margin-bottom:8px;}
.atg-status-line{display:flex;align-items:center;gap:8px;font-size:11.5px;
  color:#5B6472;white-space:nowrap;}
.atg-status-dot{width:6px;height:6px;border-radius:50%;background:#1E9E52;
  box-shadow:0 0 0 3px #E9F8EE;display:inline-block;flex-shrink:0;}
/* ---- P6a/abas/tabelas ---- */
[data-testid="stTabs"] button p{font-size:13px;font-weight:600;}
[data-testid="stDataFrame"]{border:1px solid #F0F2F4;border-radius:12px;
  overflow:hidden;}
</style>
"""

#: Ícone das cápsulas de insight (sparkle em cor de marca — SVG inline)
ICONE_INSIGHT = (
    '<svg class="ic" width="14" height="14" viewBox="0 0 24 24" '
    'fill="#E7F3F0" stroke="#0B7A66" stroke-width="1.6" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<path d="M12 2.5l2.3 6.4 6.4 2.3-6.4 2.3L12 19.9l-2.3-6.4-6.4-2.3 '
    '6.4-2.3z"/><circle cx="19.5" cy="4.5" r="1.3" fill="#0B7A66" '
    'stroke="none"/></svg>'
)

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
    """Formatação executiva dos cards: Mi / mil / valor completo."""
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
    """Percentual com sinal e uma casa decimal (+12,3% / -4,5%)."""
    if valor is None:
        return SEM_COMPARATIVO
    texto = f"{valor:+.1f}".replace(".", ",")
    return f"{texto}%"


def formatar_inteiro(valor: int) -> str:
    """Inteiro com separador de milhar pt-BR."""
    return f"{valor:,}".replace(",", ".")


def rotulo_periodo(mes_limite: int, ano: int) -> str:
    """Rótulo do intervalo comparado: "Jan–Jul/2025" ou "Jan–Dez/2025"."""
    return f"Jan–{_MESES_ABREV[mes_limite - 1]}/{ano}"


# ---------------------------------------------------------------------------
# Cards padrão (st.metric) — usados pelas páginas analíticas
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
    """Cancelado/Bonificado: CONTAGEM de PIs como número principal; valor
    monetário só como informação secundária, quando diferente de zero."""
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
# Card YTD (peças factuais + renderização)
# ---------------------------------------------------------------------------

def montar_ytd(
    ytd_resultado: dict, ano: int, sem_dados: bool = False
) -> dict[str, str]:
    """Monta as peças FACTUAIS do card YTD (função pura, testável).

    Período usa SEMPRE o mes_limite de metrics.ytd() (regra oficial v0.4).
    Estados: "ok" | "sem_comparativo" | "sem_dados". Nenhuma frase
    interpretativa — apenas fatos.
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


# ---------------------------------------------------------------------------
# Masthead, KPI band, Insights e Rankings
# ---------------------------------------------------------------------------

def masthead(titulo: str, subtitulo: str) -> None:
    """Título da página com presença (22px); o subtítulo vira tooltip —
    Sprint 3B (P1): a faixa de contexto perde uma linha inteira."""
    st.markdown(
        f'<div class="atg-h1" title="{subtitulo}">{titulo}</div>',
        unsafe_allow_html=True,
    )


def _celula_stat(
    rotulo: str, valor: Optional[float], caption: str, classe: str = ""
) -> str:
    if valor is None:
        exibido, completo = SEM_DADOS, ""
    else:
        exibido = formatar_moeda_executiva(valor)
        completo = formatar_moeda(valor)
    return (
        '<div class="atg-stat">'
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
    """KPI band (Sprint 3B, P3): Card Hero YTD + stat strip em superfície
    única com divisores hairline — mesmos dados, mesma ordem de sempre."""
    pecas = montar_ytd(ytd_resultado, ano, sem_dados)
    seta = (
        f'<span class="atg-hero-arrow" style="color:{pecas["cor"]}">'
        f'{pecas["seta"]}</span>'
    ) if pecas["seta"] else ""
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
    strip = (
        '<div class="atg-statstrip">'
        + _celula_stat(
            "Vendas", vendas_detalhado["total"],
            f"{faturado_fmt} já faturado", classe="positivo",
        )
        + _celula_stat(
            "Em Aberto", valor_em_aberto,
            "vendido, ainda não faturado", classe="ambar",
        )
        + _celula_stat("Ticket Médio", valor_ticket, "Vendas ÷ PIs da base")
        + (
            '<div class="atg-stat">'
            '<div class="atg-kpi-label">Campanhas</div>'
            f'<div class="atg-kpi-value num">{formatar_inteiro(qtd_campanhas)}</div>'
            '<div class="atg-kpi-caption" title="Combinações distintas de '
            'Cliente + Campanha (base Vendas)">Cliente + Campanha</div>'
            "</div>"
        )
        + "</div>"
    )
    st.markdown(
        f'<div class="atg-kpi-row">{hero}{strip}</div>',
        unsafe_allow_html=True,
    )


def capsulas_insights(destaques: dict) -> None:
    """Insights (Sprint 3B, P5): linhas de texto ambiente com sparkle —
    sem caixa, sem aparência de checkbox. Até 4, sempre factuais."""
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
        f'<div class="atg-insight">{ICONE_INSIGHT}{t}</div>'
        for t in textos[:4]
    )
    st.markdown(
        f'<div class="atg-insights">{capsulas}</div>', unsafe_allow_html=True
    )


def _badge_tendencia(variacao: Optional[float]) -> str:
    """Badge ▲/▼ + % (Variante 1 aprovada). None -> neutro."""
    if variacao is None:
        return '<span class="atg-trend neutro">—</span>'
    pct = f"{abs(variacao):.0f}".replace(".", ",")
    if variacao > 0:
        return f'<span class="atg-trend alta num">▲{pct}%</span>'
    if variacao < 0:
        return f'<span class="atg-trend queda num">▼{pct}%</span>'
    return '<span class="atg-trend neutro num">0%</span>'


def bloco_ranking(titulo: str, linhas: list[dict]) -> None:
    """Ranking Top 5: nome, barra, valor, % e badge — tudo inline."""
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
