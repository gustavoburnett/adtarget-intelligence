"""FERRAMENTA TEMPORÁRIA DE DIAGNÓSTICO — seção Auditoria de Vendas 2026.

Remover esta página (e a aba no app.py) quando a conciliação com a
planilha estiver encerrada. Nenhuma regra de negócio é definida aqui:
todo o cálculo vem de src/data/auditoria.py, que por sua vez reutiliza os
buckets oficiais de metrics.py.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.components import cards
from src.data import auditoria

_ANO_AUDITADO = 2026


def render(df: pd.DataFrame) -> None:
    st.warning(
        "🔧 **Ferramenta temporária de diagnóstico** — conciliação do "
        f"indicador Vendas {_ANO_AUDITADO} com a planilha de origem. "
        "Remover após o fechamento da auditoria."
    )

    resultado = auditoria.auditar_vendas_ano(df, _ANO_AUDITADO)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            f"Total da aba {_ANO_AUDITADO} (todas as linhas)",
            cards.formatar_moeda(resultado["total_aba"]),
        )
        st.caption("Soma de VALOR PI LIQUIDO de toda a aba, sem exclusões")
    with c2:
        st.metric(
            "Vendas (indicador do sistema)",
            cards.formatar_moeda(resultado["vendas_sistema"]),
        )
        st.caption("Base Vendas, MÊS (GANHO) dentro do ano — como no card")
    with c3:
        st.metric(
            "Diferença",
            cards.formatar_moeda(resultado["diferenca"]),
        )

    st.divider()
    st.subheader(f"Linhas da aba {_ANO_AUDITADO} fora de Vendas")

    excluidas = resultado["excluidas"]
    if excluidas.empty:
        st.info("Nenhuma linha excluída no ano auditado.")
    else:
        st.dataframe(
            excluidas[auditoria.COLUNAS_RELATORIO],
            width="stretch",
            hide_index=True,
            column_config={
                "VALOR PI LIQUIDO": st.column_config.NumberColumn(
                    format="R$ %.2f"
                ),
                auditoria.COL_MOTIVO: st.column_config.TextColumn(
                    "Motivo da exclusão", width="large"
                ),
            },
        )
    st.metric(
        "Soma das linhas excluídas",
        cards.formatar_moeda(resultado["total_excluidas"]),
    )

    outras = resultado["outras_abas"]
    if not outras.empty:
        st.divider()
        st.subheader("Linhas de outras abas contadas pelo sistema no ano")
        st.caption(
            f"PIs com MÊS (GANHO) em {_ANO_AUDITADO} lançados em outra aba: "
            "entram no indicador do sistema, mas não na soma da aba "
            f"{_ANO_AUDITADO}. Sem elas a conciliação não fecharia."
        )
        st.dataframe(
            outras[["PI", "CLIENTE", "CAMPANHA", "VALOR PI LIQUIDO",
                    "STATUS", "ANO_ABA"]],
            width="stretch",
            hide_index=True,
            column_config={
                "VALOR PI LIQUIDO": st.column_config.NumberColumn(
                    format="R$ %.2f"
                ),
            },
        )
        st.metric(
            "Soma dessas linhas",
            cards.formatar_moeda(resultado["total_outras_abas"]),
        )

    st.divider()
    residuo = resultado["residuo"]
    if abs(residuo) < 0.01:
        st.success(
            "✅ Conciliação fechada: as linhas listadas explicam "
            "exatamente a diferença entre a aba e o indicador Vendas."
        )
    else:
        st.error(
            f"⚠️ Resíduo não explicado de {cards.formatar_moeda(residuo)}. "
            "Se o total de referência veio de uma célula pré-calculada da "
            "planilha, desconfie dela: a documentação registra que esses "
            "totais usam critérios divergentes e já estiveram desatualizados "
            "(documento 01). A soma linha a linha exibida acima é a base "
            "confiável de conciliação."
        )
