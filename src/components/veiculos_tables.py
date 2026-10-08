"""Apresentação dos rankings nativos, com números e dimensões preservados.

A formatação pt-BR fica no Styler, separada dos valores usados pela ordenação.
A proteção do CSV nativo é aplicada apenas à cópia de apresentação pelo mesmo
adaptador do Analítico Comercial. O texto original permanece visível por célula;
a ordenação textual das células neutralizadas pode considerar seu apóstrofo.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from pandas.io.formats.style import Styler

from src.components.analitico_tables import preparar_tabela
from src.components.cards import formatar_moeda
from src.components.filters import SEPARADOR_PAR
from src.data.cleaning import COL_GRUPO, COL_VEICULO


_COLUNAS_VEICULOS = [
    "Veículo", "Vendas (Bruto)", "Vendas (Líquido)",
    "Ticket Médio", "Qtd PIs", "% do Total",
]
_MOEDAS = {"Vendas (Bruto)", "Vendas (Líquido)", "Ticket Médio", "Vendas"}


def _identificacao(grupo: object, veiculo: object) -> str | None:
    """Reduz somente a repetição literal, sem normalizar as chaves comerciais."""
    if pd.isna(grupo) and pd.isna(veiculo):
        return None
    if pd.isna(grupo):
        return str(veiculo)
    if pd.isna(veiculo):
        return str(grupo)
    if grupo == veiculo:
        return str(grupo)
    return f"{grupo}{SEPARADOR_PAR}{veiculo}"


def _moeda(valor: object) -> str:
    return "—" if pd.isna(valor) else formatar_moeda(valor)


def _percentual(valor: object) -> str:
    return "—" if pd.isna(valor) else f"{valor:.1f}".replace(".", ",") + "%"


def _formatar(styler: Styler) -> Styler:
    formatos = {coluna: _moeda for coluna in _MOEDAS.intersection(styler.data)}
    if "% do Total" in styler.data:
        formatos["% do Total"] = _percentual
    # Limita a alteração às colunas numéricas: os formatadores por célula do
    # adaptador de segurança continuam restaurando os textos originais.
    return styler.format(formatos, subset=list(formatos), na_rep="—")


def preparar_ranking_veiculos(agregado: pd.DataFrame) -> Styler:
    """Preserva as seis colunas e a ordem da agregação oficial Grupo + Veículo.

    Vendas, ticket, contagem e participação são copiados sem arredondamento,
    recalculo ou conversão textual. A identificação composta é só apresentação.
    """
    tabela = agregado.rename(columns={
        "vendas_bruto": "Vendas (Bruto)",
        "vendas_liquido": "Vendas (Líquido)",
        "ticket_medio": "Ticket Médio",
        "qtd_pis": "Qtd PIs",
        "pct_do_total": "% do Total",
    }).copy(deep=True)
    tabela["Veículo"] = [
        _identificacao(grupo, veiculo)
        for grupo, veiculo in zip(agregado[COL_GRUPO], agregado[COL_VEICULO])
    ]
    return _formatar(preparar_tabela(tabela, colunas=_COLUNAS_VEICULOS))


def preparar_ranking_dimensao(agregado: pd.DataFrame) -> Styler:
    """Aplica somente formatos e proteção à tabela existente Agência/Cliente."""
    return _formatar(preparar_tabela(agregado))


def configuracao_colunas_ranking(tabela: pd.DataFrame) -> dict:
    """Mantém alinhamento e larguras nativas sem converter números em texto."""
    configuracao = {}
    for coluna in tabela:
        if coluna in _MOEDAS:
            valores = [_moeda(valor) for valor in tabela[coluna] if not pd.isna(valor)]
            largura = max(190, max((len(valor) for valor in valores), default=0) * 8 + 40)
            configuracao[coluna] = st.column_config.NumberColumn(
                width=largura, alignment="right",
            )
        elif coluna in {"Qtd PIs", "% do Total"}:
            configuracao[coluna] = st.column_config.NumberColumn(
                width=130, alignment="right",
            )
        else:
            configuracao[coluna] = st.column_config.TextColumn(
                width=280 if coluna == "Veículo" else 260,
            )
    return configuracao
