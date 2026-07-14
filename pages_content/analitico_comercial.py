"""Página 2: Analítico Comercial (ex-Analítico Faturamento).

Cards: Vendas (com decomposição Faturado), Em Aberto, Cancelado/Bonificado
(contagem), Alertas de Qualidade. Gráfico por status. Tabela linha a linha
(auditoria), pesquisável, ordenável e exportável em CSV. Todos os filtros
finos do MVP.

Métricas de metrics.py; alertas de quality_checks.py. Nada é calculado aqui.
Os Alertas de Qualidade são calculados sobre a BASE COMPLETA carregada
(qualidade é atributo da fonte, não do recorte de filtros).
Regra de indicadores vigente: Vendas / Faturado / Em Aberto (2026-07-09).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.components import cards, charts, filters
from src.data import metrics, quality_checks
from src.data.cleaning import (
    COL_AGENCIA,
    COL_CLIENTE,
    COL_EXECUTIVO,
    COL_GRUPO,
    COL_STATUS,
)

_CHAVE = "anfat"

#: Colunas da tabela de auditoria, na ordem do wireframe (documento 04)
_COLUNAS_TABELA = [
    "GRUPO", "VEICULO", "PI", "AGENCIA", "CLIENTE", "CAMPANHA",
    "MÊS (GANHO)", "MÊS (VEICULAÇÃO)", "INÍCIO", "FIM",
    "VALOR PI BRUTO", "VALOR PI LIQUIDO", "VENCIMENTO PI",
    "STATUS", "NOTA FISCAL", "EXECUTIVO",
]

#: Colunas usadas na pesquisa textual da tabela
_COLUNAS_PESQUISA = ["GRUPO", "VEICULO", "PI", "AGENCIA", "CLIENTE", "CAMPANHA",
                     "STATUS", "NOTA FISCAL", "EXECUTIVO"]


def render(df: pd.DataFrame) -> None:
    # ------------------------------------------------------------- filtros
    # Sprint 3A: filtros compactos numa faixa única e recolhível —
    # semântica idêntica (todos por padrão; cascata Grupo -> Veículo).
    with st.expander("Filtros", expanded=True):
        col_ano, col_toggles, col_limpar = st.columns(
            [1.2, 2.4, 0.7], vertical_alignment="bottom"
        )
        with col_ano:
            ano = filters.selecionar_ano(df, _CHAVE)
        with col_toggles:
            valor, criterio_mes = filters.selecionar_toggles(_CHAVE)
        with col_limpar:
            filters.botao_limpar_filtros(_CHAVE)

        f1, f2, f3, f4, f5, f6 = st.columns(6)
        with f1:
            df_dim = filters.filtro_compacto(
                df, COL_GRUPO, "Grupo", _CHAVE, "grupos"
            )
        with f2:
            df_dim = filters.filtro_veiculo_compacto(df_dim, _CHAVE)
        with f3:
            df_dim = filters.filtro_compacto(
                df_dim, COL_AGENCIA, "Agência", _CHAVE, "agências", genero="a"
            )
        with f4:
            df_dim = filters.filtro_compacto(
                df_dim, COL_CLIENTE, "Cliente", _CHAVE, "clientes"
            )
        with f5:
            df_dim = filters.filtro_compacto(
                df_dim, COL_STATUS, "Status", _CHAVE, "status"
            )
        with f6:
            df_dim = filters.filtro_compacto(
                df_dim, COL_EXECUTIVO, "Executivo", _CHAVE, "executivos"
            )

    df_ano = filters.recorte_do_ano(df_dim, ano, criterio_mes)

    # --------------------------------------------------------------- cards
    alertas = quality_checks.executar_todas(df)  # base completa, sem filtros
    alertas_ativos = [a for a in alertas if a.possui_ocorrencias]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        detalhado = metrics.vendas_detalhado(df_ano, valor)
        cards.card_moeda(
            "Vendas",
            detalhado["total"],
            legenda=(
                f"Faturado: {cards.formatar_moeda_executiva(detalhado['faturado'])}"
            ),
        )
    with c2:
        cards.card_moeda(
            "Em Aberto",
            metrics.em_aberto(df_ano, valor),
            legenda="vendido, ainda não faturado",
        )
    with c3:
        cards.card_cancelado_bonificado(metrics.cancelado_bonificado(df_ano))
    with c4:
        cards.card_numero(
            "Alertas de Qualidade",
            len(alertas_ativos),
            legenda="na base completa (independe dos filtros)",
        )

    # ------------------------------------------------------ bloco de alertas
    with st.expander(
        f"Alertas de Qualidade ({len(alertas_ativos)} ativos)", expanded=False
    ):
        st.caption(
            "Verificados sobre a base completa carregada. Os alertas apenas "
            "sinalizam — a correção é sempre manual, na planilha de origem."
        )
        for alerta in alertas:
            icone = "🔴" if alerta.possui_ocorrencias else "🟢"
            st.markdown(f"{icone} **{alerta.titulo}**: {alerta.quantidade}")
            if alerta.codigo == "3" and alerta.possui_ocorrencias:
                for veiculo, grupos in alerta.detalhes["veiculos"].items():
                    st.caption(f"“{veiculo}” aparece em: {', '.join(grupos)}")
            if alerta.codigo == "4" and alerta.possui_ocorrencias:
                st.caption(f"Status novos: {', '.join(alerta.detalhes['valores'])}")
            if alerta.possui_ocorrencias and not alerta.linhas.empty:
                colunas = [c for c in _COLUNAS_TABELA if c in alerta.linhas.columns]
                st.dataframe(
                    alerta.linhas[colunas], width="stretch", hide_index=True
                )

    st.divider()

    # -------------------------------------------------- gráfico por status
    charts.grafico_por_status(
        metrics.resumo_por_status(df_ano, valor),
        "Carteira por status (valor e quantidade de PIs)",
    )

    st.divider()

    # ------------------------------------------------- tabela de auditoria
    st.subheader("Tabela analítica (uma linha por PI)")
    pesquisa = st.text_input(
        "Pesquisar (grupo, veículo, PI, agência, cliente, campanha, status, NF, executivo)",
        key=f"{_CHAVE}_pesquisa",
    )
    tabela = df_ano.copy()
    if pesquisa:
        termo = pesquisa.strip().upper()
        mascara = pd.Series(False, index=tabela.index)
        for coluna in _COLUNAS_PESQUISA:
            mascara |= tabela[coluna].astype(str).str.upper().str.contains(
                termo, regex=False
            )
        tabela = tabela[mascara]

    colunas_presentes = [c for c in _COLUNAS_TABELA if c in tabela.columns]
    st.dataframe(
        tabela[colunas_presentes],
        width="stretch",
        hide_index=True,
        row_height=40,  # 2B.1: leitura mais confortável, menos "Excel"
        column_config={
            "VALOR PI BRUTO": st.column_config.NumberColumn(format="R$ %.2f"),
            "VALOR PI LIQUIDO": st.column_config.NumberColumn(format="R$ %.2f"),
        },
    )
    st.caption(f"{len(tabela)} linha(s) no recorte")
    st.download_button(
        "Exportar CSV",
        tabela[colunas_presentes].to_csv(index=False).encode("utf-8-sig"),
        file_name=f"analitico_comercial_{ano}.csv",
        mime="text/csv",
        key=f"{_CHAVE}_csv",
    )
