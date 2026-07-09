"""KPI cards e formatação pt-BR reutilizáveis.

Este módulo NÃO calcula nada: recebe valores prontos de metrics.py e apenas
formata/exibe. Comportamentos obrigatórios do documento 02:
- recorte vazio exibe "R$ 0,00" ou "Sem dados no recorte selecionado"
- comparativo indisponível exibe "sem comparativo disponível", nunca erro
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

SEM_DADOS = "Sem dados no recorte selecionado"
SEM_COMPARATIVO = "Sem comparativo disponível"


def formatar_moeda(valor: Optional[float]) -> str:
    """Formata em R$ no padrão brasileiro (1.234.567,89)."""
    if valor is None:
        return SEM_DADOS
    texto = f"{valor:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    return f"R$ {texto}"


def formatar_pct(valor: Optional[float]) -> str:
    """Formata percentual com sinal (+12,3% / -4,5%)."""
    if valor is None:
        return SEM_COMPARATIVO
    texto = f"{valor:+.1f}".replace(".", ",")
    return f"{texto}%"


def formatar_inteiro(valor: int) -> str:
    """Formata inteiro com separador de milhar pt-BR."""
    return f"{valor:,}".replace(",", ".")


def card_moeda(
    titulo: str, valor: Optional[float], legenda: str | None = None
) -> None:
    """Card monetário. Valor None ou recorte vazio vira mensagem, nunca erro."""
    st.metric(titulo, formatar_moeda(valor if valor is not None else None))
    if legenda:
        st.caption(legenda)


def card_ytd(titulo: str, ytd_resultado: dict) -> None:
    """Card do KPI principal de YTD (documento 04, página 1).

    Exibe o acumulado do ano e a variação contra o mesmo intervalo do ano
    anterior. Sem dado do ano anterior -> "sem comparativo disponível".
    """
    variacao = ytd_resultado.get("variacao_pct")
    st.metric(
        titulo,
        formatar_moeda(ytd_resultado.get("atual", 0.0)),
        delta=formatar_pct(variacao) if variacao is not None else None,
    )
    anterior = ytd_resultado.get("anterior")
    mes_limite = ytd_resultado.get("mes_limite")
    if anterior is None:
        st.caption(SEM_COMPARATIVO)
    else:
        st.caption(
            f"Ano anterior (jan–mês {mes_limite}): {formatar_moeda(anterior)}"
        )


def card_numero(titulo: str, valor: Optional[float], legenda: str | None = None) -> None:
    """Card de contagem/quantidade."""
    if valor is None:
        st.metric(titulo, "—")
        st.caption(SEM_DADOS)
    else:
        st.metric(titulo, formatar_inteiro(int(valor)))
        if legenda:
            st.caption(legenda)


def card_cancelado_bonificado(resultado: dict) -> None:
    """Bloco de Cancelado/Bonificado: CONTAGEM de PIs como número principal
    (documento 02); valor monetário só como informação secundária, quando
    diferente de zero."""
    st.metric(
        "Cancelado / Bonificado",
        f"{resultado['cancelados']} canc. | {resultado['bonificados']} bonif.",
    )
    valor_secundario = resultado.get("valor_bruto_secundario", 0.0)
    if valor_secundario:
        st.caption(
            f"Atenção: {formatar_moeda(valor_secundario)} bruto em PIs "
            "cancelados/bonificados (esperado: zero — ver Alertas)"
        )
