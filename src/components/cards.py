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

#: Cores de sentimento do card de destaque (v0.5 Sprint 1)
COR_POSITIVO = "#15803d"   # verde: crescimento
COR_NEGATIVO = "#b91c1c"   # vermelho: queda
COR_NEUTRO = "#6b7280"     # cinza: sem direção definida

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
