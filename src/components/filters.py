"""Filtros reutilizáveis, seguindo o comportamento padrão do documento 02.

- Ano: seleção ÚNICA, ano mais recente marcado por padrão; o ano anterior é
  sempre (ano selecionado − 1), calculado automaticamente, nunca um filtro
- Demais dimensões: seleção múltipla com TODOS os valores marcados por padrão
- Veículo: sempre exibido como o par "Grupo — Veículo", em cascata dentro
  dos grupos selecionados
- Toggles: Valor Líquido como padrão; o critério temporal padrão vem de
  metrics.CRITERIO_MES_OFICIAL (regra oficial v0.4: Mês Veiculação),
  NUNCA de um valor fixo neste módulo. MÊS (GANHO) permanece disponível
  como análise alternativa.

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
    """Toggles oficiais como segmented control (Sprint 2A, item 1).

    Retorna (valor, criterio_mes) no vocabulário de metrics.py:
    ("liquido"|"bruto", "ganho"|"veiculacao").

    - O critério temporal inicia SEMPRE em metrics.CRITERIO_MES_OFICIAL
      (fonte única de verdade da regra de negócio), em todas as páginas.
    - Se o usuário desmarcar a opção ativa (comportamento nativo do
      segmented control), o toggle volta ao padrão — nunca fica sem valor.
    - Rótulo do grupo acima do controle (papel de legenda); estado ativo
      usa a cor neutra do tema (item 2), nunca vermelho/verde.
    """
    rotulo_valor_padrao = next(iter(_OPCOES_VALOR))  # "Valor Líquido"
    rotulo_mes_padrao = next(
        rotulo for rotulo, criterio in _OPCOES_MES.items()
        if criterio == metrics.CRITERIO_MES_OFICIAL
    )
    col1, col2 = st.columns(2)
    with col1:
        rotulo_valor = st.segmented_control(
            "Métrica de valor",
            list(_OPCOES_VALOR),
            default=rotulo_valor_padrao,
            key=f"{chave}_valor",
        ) or rotulo_valor_padrao
    with col2:
        rotulo_mes = st.segmented_control(
            "Critério de mês",
            list(_OPCOES_MES),
            default=rotulo_mes_padrao,
            key=f"{chave}_mes",
        ) or rotulo_mes_padrao
    return _OPCOES_VALOR[rotulo_valor], _OPCOES_MES[rotulo_mes]


# ---------------------------------------------------------------------------
# Filtro de Grupo recolhido (Sprint 2A, item 3)
# ---------------------------------------------------------------------------

#: Máximo de nomes exibidos no resumo antes de virar contador ("+N"),
#: garantindo que o resumo nunca ocupe mais de uma linha (decisão de PO)
_MAX_NOMES_RESUMO = 3
_NOMES_COM_CONTADOR = 2


def resumo_grupos(selecionados: list[str], total: int) -> str:
    """Resumo do filtro de Grupo recolhido (regras da spec Sprint 2A):

    - todos selecionados -> "Grupo: Todos"
    - até 3 -> "Grupo: A, B, C"
    - mais que isso -> "Grupo: A, B +N" (nunca mais de uma linha)
    - nenhum -> "Grupo: Nenhum selecionado" (vazio intencional, não erro)
    """
    if total and len(selecionados) == total:
        return "Grupo: Todos"
    if not selecionados:
        return "Grupo: Nenhum selecionado"
    if len(selecionados) <= _MAX_NOMES_RESUMO:
        return "Grupo: " + ", ".join(selecionados)
    visiveis = selecionados[:_NOMES_COM_CONTADOR]
    return (
        "Grupo: " + ", ".join(visiveis)
        + f" +{len(selecionados) - len(visiveis)}"
    )


def _definir_grupos(chaves: list[str], marcado: bool) -> None:
    """Callback dos atalhos Selecionar todos / Limpar."""
    for chave in chaves:
        st.session_state[chave] = marcado


def filtro_grupo_recolhido(df: pd.DataFrame, chave: str) -> pd.DataFrame:
    """Filtro de Grupo compacto: resumo em um componente recolhido; o
    clique abre painel com checkboxes e atalhos Selecionar todos / Limpar.

    Apenas APRESENTAÇÃO (Sprint 2A, item 3): a semântica é idêntica à do
    filtro múltiplo — todos marcados por padrão; com tudo marcado, o
    universo completo passa (inclusive linhas com grupo vazio); recorte
    vazio segue a regra de negócio existente.
    """
    opcoes = sorted(v for v in df[COL_GRUPO].unique() if v != "")
    chaves = {grupo: f"{chave}_grupo_{grupo}" for grupo in opcoes}
    for chave_grupo in chaves.values():
        st.session_state.setdefault(chave_grupo, True)

    selecionados = [g for g in opcoes if st.session_state.get(chaves[g], True)]
    with st.popover(resumo_grupos(selecionados, len(opcoes)), width="stretch"):
        col_a, col_b = st.columns(2)
        col_a.button(
            "Selecionar todos",
            key=f"{chave}_grupo_todos",
            on_click=_definir_grupos,
            args=(list(chaves.values()), True),
            width="stretch",
        )
        col_b.button(
            "Limpar",
            key=f"{chave}_grupo_limpar",
            on_click=_definir_grupos,
            args=(list(chaves.values()), False),
            width="stretch",
        )
        for grupo in opcoes:
            st.checkbox(grupo, key=chaves[grupo])

    selecionados = [g for g in opcoes if st.session_state.get(chaves[g], True)]
    if len(selecionados) == len(opcoes):
        return df  # universo completo, inclusive linhas com valor vazio
    return df[df[COL_GRUPO].isin(selecionados)]


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
