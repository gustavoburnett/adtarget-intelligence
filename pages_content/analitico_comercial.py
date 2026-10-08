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

from html import escape

import pandas as pd
import streamlit as st

from src.components import cards, charts, filters
from src.components.analitico_tables import configuracao_colunas, preparar_tabela
from src.components.kpi_icons import ICONES_KPI
from src.data import metrics, quality_checks
from src.data.csv_export import gerar_csv_seguro
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
    with st.container(key="design_comercial_filters"), st.expander("Filtros", expanded=True):
        with st.container(key="design_comercial_filter_top"):
            col_ano, col_toggles, col_limpar = st.columns(
                [1.2, 2.4, 0.7], vertical_alignment="bottom"
            )
        with col_ano, st.container(key="design_comercial_year"):
            ano = filters.selecionar_ano(df, _CHAVE)
        with col_toggles, st.container(key="design_comercial_toggles"):
            valor, criterio_mes = filters.selecionar_toggles(_CHAVE)
        with col_limpar, st.container(key="design_comercial_clear"):
            filters.botao_limpar_filtros(_CHAVE)

        with st.container(key="design_comercial_filter_dimensions"):
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

    with st.container(key="design_comercial_kpis"):
        c1, c2, c3, c4 = st.columns(4)
    with c1, st.container(key="design_comercial_kpi_vendas"):
        st.markdown(f'<div class="atg-analytic-kpi-icon">{ICONES_KPI["vendas"]}</div>', unsafe_allow_html=True)
        detalhado = metrics.vendas_detalhado(df_ano, valor)
        cards.card_moeda(
            "Vendas",
            detalhado["total"],
            legenda=(
                f"Faturado: {cards.formatar_moeda_executiva(detalhado['faturado'])}"
            ),
        )
    with c2, st.container(key="design_comercial_kpi_em_aberto"):
        st.markdown(f'<div class="atg-analytic-kpi-icon">{ICONES_KPI["em-aberto"]}</div>', unsafe_allow_html=True)
        cards.card_moeda(
            "Em Aberto",
            metrics.em_aberto(df_ano, valor),
            legenda="vendido, ainda não faturado",
        )
    with c3, st.container(key="design_comercial_kpi_cancelado"):
        st.markdown(f'<div class="atg-analytic-kpi-icon">{ICONES_KPI["cancelado"]}</div>', unsafe_allow_html=True)
        cards.card_cancelado_bonificado(metrics.cancelado_bonificado(df_ano))
    with c4, st.container(key="design_comercial_kpi_alertas"):
        st.markdown(f'<div class="atg-analytic-kpi-icon">{ICONES_KPI["alertas"]}</div>', unsafe_allow_html=True)
        cards.card_numero(
            "Alertas de Qualidade",
            len(alertas_ativos),
            legenda="na base completa (independe dos filtros)",
        )

    # ------------------------------------------------------ bloco de alertas
    with st.container(key="design_comercial_quality"), st.expander(
        f"Alertas de Qualidade ({len(alertas_ativos)} ativos)", expanded=False
    ):
        st.caption(
            "Verificados sobre a base completa carregada. Os alertas apenas "
            "sinalizam — a correção é sempre manual, na planilha de origem."
        )
        for alerta in alertas:
            estado = "active" if alerta.possui_ocorrencias else "inactive"
            icone = ICONES_KPI["alertas"] if alerta.possui_ocorrencias else (
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
                'aria-hidden="true"><path d="m5 12 4 4 10-10"/></svg>'
            )
            st.markdown(
                f'<div class="atg-analytic-alert atg-analytic-alert-{estado}">'
                f'<span class="atg-analytic-alert-icon">{icone}</span>'
                f'<span class="atg-analytic-alert-title">{escape(alerta.titulo)}</span>'
                f'<span class="atg-analytic-alert-count">{alerta.quantidade}</span></div>',
                unsafe_allow_html=True,
            )
            if alerta.codigo == "3" and alerta.possui_ocorrencias:
                for veiculo, grupos in alerta.detalhes["veiculos"].items():
                    st.caption(f"“{veiculo}” aparece em: {', '.join(grupos)}")
            if alerta.codigo == "4" and alerta.possui_ocorrencias:
                st.caption(f"Status novos: {', '.join(alerta.detalhes['valores'])}")
            if alerta.possui_ocorrencias and not alerta.linhas.empty:
                colunas = [c for c in _COLUNAS_TABELA if c in alerta.linhas.columns]
                st.dataframe(
                    preparar_tabela(alerta.linhas, colunas=colunas),
                    column_config=configuracao_colunas(alerta.linhas, colunas=colunas),
                    width="stretch", hide_index=True, row_height=40,
                )

    # -------------------------------------------------- gráfico por status
    with st.container(key="design_comercial_status"):
        st.subheader("Carteira por status (valor e quantidade de PIs)")
        charts.grafico_por_status(
            metrics.resumo_por_status(df_ano, valor),
            "Carteira por status (valor e quantidade de PIs)",
            estilo_analitico=True,
        )

    # ------------------------------------------------- tabela de auditoria
    bloco_tabela = st.container(key="design_comercial_table")
    with bloco_tabela:
        st.subheader("Tabela analítica")
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
    with bloco_tabela:
        st.dataframe(
            preparar_tabela(tabela, colunas=colunas_presentes),
            width="stretch", hide_index=True, row_height=40,
            column_config=configuracao_colunas(tabela, colunas=colunas_presentes),
        )
        with st.container(key="design_comercial_table_footer", horizontal=True, vertical_alignment="center"):
            with st.container(width="stretch"):
                st.caption(f"{len(tabela)} linha(s) no recorte")
            with st.container(width="content"):
                # Sem registros, o CSV contém somente os mesmos cabeçalhos.
                # A cópia object evita a redução de uma série datetime vazia
                # no exportador existente, sem alterar seus contratos/dados.
                exportacao = tabela[colunas_presentes]
                if exportacao.empty:
                    exportacao = exportacao.astype(object)
                st.download_button(
                    "Exportar CSV", gerar_csv_seguro(exportacao),
                    file_name=f"analitico_comercial_{ano}.csv", mime="text/csv",
                    key=f"{_CHAVE}_csv", icon=":material/download:",
                )
