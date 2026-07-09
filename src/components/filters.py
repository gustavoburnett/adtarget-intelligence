"""Filtros reutilizáveis, seguindo o comportamento padrão do documento 02.

- Ano: seleção ÚNICA, ano mais recente marcado por padrão; o ano anterior é
  sempre (ano selecionado − 1), calculado automaticamente, nunca um filtro
- Demais dimensões: seleção múltipla com TODOS os valores marcados por padrão
- Veículo: sempre exibido como o par "Grupo — Veículo", em cascata dentro
  dos grupos selecionados
- Toggles: Valor Líquido + MÊS (GANHO) como padrão de todo carregamento

Este módulo apenas FILTRA linhas; nenhuma métrica é calculada aqui.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data import metrics
from src.data.cleaning import COL_GRUPO, COL_VEICULO
from src.data.loader import COL_ANO_ABA

SEPARADOR_PAR = " — "

#: Rótulos dos toggles -> valores oficiais de metrics.py
_OPCOES_VALOR = {"Valor Líquido": "liquido", "Valor Bruto": "bruto"}
_OPCOES_MES = {"Mês (Ganho)": "ganho", "Mês (Veiculação)": "veiculacao"}


def selecionar_ano(df: pd.DataFrame, chave: str) -> int:
    """Filtro de Ano: seleção única, mais recente por padrão."""
    anos = sorted(df[COL_ANO_ABA].unique(), reverse=True)
    return int(st.selectbox("Ano", anos, index=0, key=f"{chave}_ano"))


def selecionar_toggles(chave: str) -> tuple[str, str]:
    """Toggles oficiais. Retorna (valor, criterio_mes) no vocabulário de
    metrics.py: ("liquido"|"bruto", "ganho"|"veiculacao")."""
    col1, col2 = st.columns(2)
    with col1:
        rotulo_valor = st.radio(
            "Métrica de valor",
            list(_OPCOES_VALOR),
            horizontal=True,
            key=f"{chave}_valor",
        )
    with col2:
        rotulo_mes = st.radio(
            "Critério de mês",
            list(_OPCOES_MES),
            horizontal=True,
            key=f"{chave}_mes",
        )
    return _OPCOES_VALOR[rotulo_valor], _OPCOES_MES[rotulo_mes]


def filtro_multiplo(
    df: pd.DataFrame, coluna: str, rotulo: str, chave: str
) -> pd.DataFrame:
    """Multiselect com todos os valores marcados por padrão (documento 02).

    Valores vazios ("") não viram opção, mas as linhas só são cortadas se o
    usuário desmarcar algo — com tudo marcado, o universo completo passa.
    """
    opcoes = sorted(v for v in df[coluna].unique() if v != "")
    selecionadas = st.multiselect(
        rotulo, opcoes, default=opcoes, key=f"{chave}_{coluna}"
    )
    if set(selecionadas) == set(opcoes):
        return df  # universo completo, inclusive linhas com valor vazio
    return df[df[coluna].isin(selecionadas)]


def filtro_veiculo_cascata(df: pd.DataFrame, chave: str) -> pd.DataFrame:
    """Filtro de Veículo como par "Grupo — Veículo" (decisão 15).

    Em cascata: as opções refletem o DataFrame já filtrado por Grupo. Se
    nenhum grupo foi restringido, lista todos os pares existentes.
    """
    pares = (
        df[[COL_GRUPO, COL_VEICULO]]
        .drop_duplicates()
        .query(f"{COL_GRUPO} != '' and {COL_VEICULO} != ''")
    )
    opcoes = sorted(
        f"{grupo}{SEPARADOR_PAR}{veiculo}"
        for grupo, veiculo in pares.itertuples(index=False)
    )
    selecionadas = st.multiselect(
        "Veículo (Grupo — Veículo)", opcoes, default=opcoes, key=f"{chave}_veiculo"
    )
    if set(selecionadas) == set(opcoes):
        return df
    pares_ok = {tuple(p.split(SEPARADOR_PAR, 1)) for p in selecionadas}
    mascara = df.apply(
        lambda linha: (linha[COL_GRUPO], linha[COL_VEICULO]) in pares_ok, axis=1
    )
    return df[mascara]


def recorte_do_ano(df: pd.DataFrame, ano: int, criterio_mes: str) -> pd.DataFrame:
    """Linhas cujo mês (no critério ativo) cai no ano selecionado.

    Usado pelos cards e tabelas; os comparativos (YTD, mês a mês) recebem o
    DataFrame SEM corte de ano, porque precisam do ano anterior. Linhas com
    mês inválido (NaT) ficam fora do recorte temporal.
    """
    col_mes = metrics.coluna_mes(criterio_mes)
    return df[df[col_mes].dt.year == ano]
