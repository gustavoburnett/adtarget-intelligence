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


#: Abreviações de mês para o rótulo do período comparado
_MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def rotulo_periodo(mes_limite: int, ano: int) -> str:
    """Rótulo do intervalo comparado: "Jan–Jul/2025" ou "Jan–Dez/2025"."""
    return f"Jan–{_MESES_ABREV[mes_limite - 1]}/{ano}"


def card_ytd(titulo: str, ytd_resultado: dict, ano: int) -> None:
    """Card do KPI principal de YTD (documento 04, página 1).

    Exibe o acumulado do ano e a variação contra o mesmo intervalo do ano
    anterior, com o período comparado explícito no texto auxiliar
    (ex: "vs Jan–Jul/2025" no ano corrente; "vs Jan–Dez/2024" em ano
    encerrado). Sem dado do ano anterior -> "sem comparativo disponível".
    """
    variacao = ytd_resultado.get("variacao_pct")
    mes_limite = ytd_resultado.get("mes_limite") or 12
    st.metric(
        titulo,
        formatar_moeda(ytd_resultado.get("atual", 0.0)),
        delta=formatar_pct(variacao) if variacao is not None else None,
    )
    anterior = ytd_resultado.get("anterior")
    periodo_atual = rotulo_periodo(mes_limite, ano)
    if anterior is None:
        st.caption(f"{periodo_atual} — {SEM_COMPARATIVO}")
    else:
        periodo_anterior = rotulo_periodo(mes_limite, ano - 1)
        st.caption(
            f"{periodo_atual} vs {periodo_anterior}: {formatar_moeda(anterior)}"
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
