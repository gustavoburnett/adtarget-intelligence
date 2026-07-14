"""Filtros reutilizáveis — Sprint 3A: sistema de filtros compactos.

Comportamento padrão preservado (documento 02):
- Ano: seleção única, ano mais recente por padrão
- Dimensões: todos os valores selecionados por padrão (universo completo)
- Veículo: sempre o par "Grupo — Veículo", em cascata dentro dos grupos
- Critério temporal padrão vem de metrics.CRITERIO_MES_OFICIAL

FILTRO COMPACTO (um único componente para TODAS as páginas):
- campo recolhido com resumo ("Todos os grupos (18)" / "Disney, Teads +15"
  / "3 grupos selecionados") — nunca parede de chips
- popover com busca (realce do trecho), "Selecionar todos" agindo sobre o
  subconjunto buscado (padrão Notion), contador, lista com rolagem e
  botões Cancelar/Aplicar
- ESTADO EM DUAS CAMADAS: o rascunho vive só dentro do popover; o estado
  APLICADO é o único que filtra dados. Nenhum gráfico reage antes do
  Aplicar. O painel roda como st.fragment: cliques internos re-renderizam
  apenas o painel — a página não é recalculada durante a seleção.
- Primitivos estáveis apenas (st.popover + st.fragment); st.dialog foi
  descartado por decisão registrada (issues 13009/9921/10907).

Este módulo apenas FILTRA linhas; nenhuma métrica é calculada aqui.
"""

from __future__ import annotations

from typing import Callable, Optional

import pandas as pd
import streamlit as st

from src.data import metrics
from src.data.cleaning import COL_GRUPO, COL_VEICULO
from src.data.loader import COL_ANO_ABA

SEPARADOR_PAR = " — "

#: Rótulos dos toggles -> valores oficiais de metrics.py
_OPCOES_VALOR = {"Valor Líquido": "liquido", "Valor Bruto": "bruto"}
_OPCOES_MES = {"Mês (Ganho)": "ganho", "Mês (Veiculação)": "veiculacao"}

#: Teto de caracteres do resumo (o campo recolhido nunca passa de 1 linha)
_LIMITE_RESUMO = 32


# ---------------------------------------------------------------------------
# Ano e toggles (inalterados na Sprint 3A)
# ---------------------------------------------------------------------------

def selecionar_ano(df: pd.DataFrame, chave: str) -> int:
    """Filtro de Ano como segmented control: seleção única, mais recente
    por padrão; deselecionar volta ao padrão."""
    anos = sorted(int(a) for a in df[COL_ANO_ABA].unique())
    padrao = anos[-1]
    escolhido = st.segmented_control(
        "Ano", anos, default=padrao, key=f"{chave}_ano"
    )
    return int(escolhido if escolhido is not None else padrao)


def selecionar_toggles(chave: str) -> tuple[str, str]:
    """Toggles oficiais (segmented). Retorna (valor, criterio_mes) no
    vocabulário de metrics.py. O critério temporal inicia SEMPRE em
    metrics.CRITERIO_MES_OFICIAL; deselecionar volta ao padrão."""
    rotulo_valor_padrao = next(iter(_OPCOES_VALOR))
    rotulo_mes_padrao = next(
        rotulo for rotulo, criterio in _OPCOES_MES.items()
        if criterio == metrics.CRITERIO_MES_OFICIAL
    )
    col1, col2 = st.columns(2)
    with col1:
        rotulo_valor = st.segmented_control(
            "Métrica de valor", list(_OPCOES_VALOR),
            default=rotulo_valor_padrao, key=f"{chave}_valor",
        ) or rotulo_valor_padrao
    with col2:
        rotulo_mes = st.segmented_control(
            "Critério de mês", list(_OPCOES_MES),
            default=rotulo_mes_padrao, key=f"{chave}_mes",
        ) or rotulo_mes_padrao
    return _OPCOES_VALOR[rotulo_valor], _OPCOES_MES[rotulo_mes]


def toggles_do_estado(chave: str) -> tuple[str, str]:
    """Lê (valor, criterio_mes) do estado dos toggles sem renderizá-los."""
    rotulo_valor = st.session_state.get(f"{chave}_valor") or next(iter(_OPCOES_VALOR))
    rotulo_mes_padrao = next(
        r for r, c in _OPCOES_MES.items() if c == metrics.CRITERIO_MES_OFICIAL
    )
    rotulo_mes = st.session_state.get(f"{chave}_mes") or rotulo_mes_padrao
    return _OPCOES_VALOR[rotulo_valor], _OPCOES_MES[rotulo_mes]


def recorte_do_ano(df: pd.DataFrame, ano: int, criterio_mes: str) -> pd.DataFrame:
    """Linhas cujo mês (no critério ativo) cai no ano selecionado."""
    col_mes = metrics.coluna_mes(criterio_mes)
    return df[df[col_mes].dt.year == ano]


# ---------------------------------------------------------------------------
# Filtro compacto — funções puras (testáveis sem Streamlit)
# ---------------------------------------------------------------------------

def resumo_selecao(
    selecionados: list[str], total: int, plural: str, genero: str = "o"
) -> str:
    """Resumo do campo recolhido (Sprint 3A):

    - todos    -> "Todos os grupos (18)" / "Todas as agências (26)"
    - nenhum   -> "Nenhum selecionado" / "Nenhuma selecionada"
    - parcial  -> nomes até caber ("Disney, Teads +15"), degradando para
                  "3 grupos selecionados" — nunca mais de uma linha
    """
    fem = genero == "a"
    if total == 0:
        return f"Sem {plural} no recorte"
    if len(selecionados) == total:
        artigo = "Todas as" if fem else "Todos os"
        return f"{artigo} {plural} ({total})"
    if not selecionados:
        return "Nenhuma selecionada" if fem else "Nenhum selecionado"
    for n_nomes in (3, 2, 1):
        if len(selecionados) < n_nomes:
            continue
        resto = len(selecionados) - n_nomes
        candidato = ", ".join(selecionados[:n_nomes]) + (
            f" +{resto}" if resto else ""
        )
        if len(candidato) <= _LIMITE_RESUMO:
            return candidato
    sufixo = "selecionadas" if fem else "selecionados"
    return f"{len(selecionados)} {plural} {sufixo}"


def resumo_curto(
    selecionados: list[str], total: int, genero: str = "o"
) -> str:
    """Resumo INLINE do campo (Sprint 3B, P1): o rótulo do filtro entra no
    próprio campo ("Grupo · Todos (18)"), então o resumo não repete o
    substantivo: "Todos (18)" / "DISNEY, TEADS +3" / "5 sel." / "Nenhum".
    """
    fem = genero == "a"
    if total == 0:
        return "—"
    if len(selecionados) == total:
        return f"{'Todas' if fem else 'Todos'} ({total})"
    if not selecionados:
        return "Nenhuma" if fem else "Nenhum"
    for n_nomes in (2, 1):
        if len(selecionados) < n_nomes:
            continue
        resto = len(selecionados) - n_nomes
        candidato = ", ".join(selecionados[:n_nomes]) + (
            f" +{resto}" if resto else ""
        )
        if len(candidato) <= 22:
            return candidato
    return f"{len(selecionados)} sel."


def realcar_busca(texto: str, busca: str) -> str:
    """Realça (negrito markdown) o trecho encontrado pela busca."""
    termo = busca.strip()
    if not termo:
        return texto
    indice = texto.upper().find(termo.upper())
    if indice < 0:
        return texto
    fim = indice + len(termo)
    return f"{texto[:indice]}**{texto[indice:fim]}**{texto[fim:]}"


def filtrar_opcoes(opcoes: list[str], busca: str) -> list[str]:
    """Subconjunto de opções que casa com a busca (case-insensitive)."""
    termo = busca.strip().upper()
    if not termo:
        return list(opcoes)
    return [o for o in opcoes if termo in o.upper()]


# ---------------------------------------------------------------------------
# Filtro compacto — motor (popover + fragment + rascunho/aplicado)
# ---------------------------------------------------------------------------

def _chave_aplicado(chave: str, ident: str) -> str:
    return f"{chave}_fc_{ident}_aplicado"


def _prefixo_rascunho(chave: str, ident: str) -> str:
    return f"{chave}_fc_{ident}_r_"


def _selecao_aplicada(
    chave: str, ident: str, opcoes: list[str]
) -> tuple[Optional[list[str]], list[str]]:
    """(estado bruto aplicado, lista efetiva de selecionados).

    None = padrão oficial (todos selecionados). Valores aplicados que
    saíram do universo (ex: cascata de Grupo mudou) são ignorados.
    """
    aplicado = st.session_state.get(_chave_aplicado(chave, ident))
    if aplicado is None:
        return None, list(opcoes)
    return aplicado, [o for o in aplicado if o in opcoes]


def _painel_filtro(
    chave: str, ident: str, opcoes: list[str], plural: str, genero: str
) -> None:
    """Conteúdo do popover. Roda como FRAGMENT: interações internas
    (busca, checkboxes, selecionar todos, cancelar) re-renderizam apenas
    este painel — a página e os gráficos não recalculam. Só o Aplicar
    dispara o rerun do app (e fecha o popover)."""
    prefixo = _prefixo_rascunho(chave, ident)
    chave_apl = _chave_aplicado(chave, ident)

    # rascunho: inicializa do aplicado quando ainda não existe
    _, aplicados = _selecao_aplicada(chave, ident, opcoes)
    base = set(aplicados)
    for opcao in opcoes:
        st.session_state.setdefault(prefixo + opcao, opcao in base)

    busca = st.text_input(
        "Pesquisar", key=f"{chave}_fc_{ident}_busca",
        placeholder=f"Pesquisar {plural}…", label_visibility="collapsed",
        icon=":material/search:",
    )
    visiveis = filtrar_opcoes(opcoes, busca)

    # "Selecionar todos" age apenas sobre o subconjunto buscado (Notion)
    chave_todos = f"{chave}_fc_{ident}_todos"
    st.session_state[chave_todos] = bool(visiveis) and all(
        st.session_state[prefixo + o] for o in visiveis
    )

    def _alternar_todos() -> None:
        marcar = st.session_state[chave_todos]
        for o in filtrar_opcoes(opcoes, st.session_state.get(
                f"{chave}_fc_{ident}_busca", "")):
            st.session_state[prefixo + o] = marcar

    col_todos, col_contador = st.columns([1.2, 1], vertical_alignment="center")
    with col_todos:
        st.checkbox("Selecionar todos", key=chave_todos, on_change=_alternar_todos)
    n_rascunho = sum(1 for o in opcoes if st.session_state[prefixo + o])
    sufixo = "selecionadas" if genero == "a" else "selecionados"
    with col_contador:
        st.markdown(
            f'<div class="atg-filtro-contador">{n_rascunho} de '
            f"{len(opcoes)} {sufixo}</div>",
            unsafe_allow_html=True,
        )

    with st.container(height=234, border=False):
        if not visiveis:
            st.caption("Nenhum resultado para a busca")
        for opcao in visiveis:
            st.checkbox(realcar_busca(opcao, busca), key=prefixo + opcao)

    # rascunho difere do aplicado? sinaliza pendência
    pendente = {o for o in opcoes if st.session_state[prefixo + o]} != base
    if pendente:
        st.markdown(
            '<div class="atg-filtro-pendente">Alterações não aplicadas</div>',
            unsafe_allow_html=True,
        )

    def _cancelar() -> None:
        _, aplicados_agora = _selecao_aplicada(chave, ident, opcoes)
        base_agora = set(aplicados_agora)
        for o in opcoes:
            st.session_state[prefixo + o] = o in base_agora

    def _aplicar() -> None:
        selecao = [o for o in opcoes if st.session_state[prefixo + o]]
        # todos marcados volta ao padrão oficial (None = universo completo)
        st.session_state[chave_apl] = (
            None if len(selecao) == len(opcoes) else selecao
        )

    col_cancelar, col_aplicar = st.columns(2)
    col_cancelar.button(
        "Cancelar", key=f"{chave}_fc_{ident}_cancelar",
        on_click=_cancelar, width="stretch",
    )
    if col_aplicar.button(
        f"Aplicar ({n_rascunho})", key=f"{chave}_fc_{ident}_aplicar",
        on_click=_aplicar, type="primary", width="stretch",
    ):
        st.rerun(scope="app")


# st.fragment como decorador dinâmico preserva testabilidade fora do runtime
_painel_filtro_fragment = st.fragment(_painel_filtro)


def _motor_filtro(
    df: pd.DataFrame,
    chave: str,
    ident: str,
    rotulo: str,
    plural: str,
    genero: str,
    opcoes: list[str],
    aplicar_filtro: Callable[[pd.DataFrame, list[str]], pd.DataFrame],
) -> pd.DataFrame:
    """Campo compacto + popover; retorna o df filtrado pelo APLICADO.

    Sprint 3B (P1/P2): o rótulo vive DENTRO do campo ("Grupo · Todos (18)")
    — sem linha de rótulo acima, sem aparência de formulário.
    """
    aplicado, selecionados = _selecao_aplicada(chave, ident, opcoes)

    with st.popover(
        f"{rotulo} · {resumo_curto(selecionados, len(opcoes), genero)}",
        width="stretch",
    ):
        _painel_filtro_fragment(chave, ident, opcoes, plural, genero)

    if aplicado is None or len(selecionados) == len(opcoes):
        return df  # universo completo (inclui linhas com valor vazio)
    return aplicar_filtro(df, selecionados)


def filtro_compacto(
    df: pd.DataFrame,
    coluna: str,
    rotulo: str,
    chave: str,
    plural: str,
    genero: str = "o",
) -> pd.DataFrame:
    """Filtro compacto padrão para uma coluna (Grupo, Agência, Cliente,
    Status, Executivo). Semântica idêntica ao filtro múltiplo de sempre."""
    opcoes = sorted(v for v in df[coluna].unique() if v != "")
    return _motor_filtro(
        df, chave, coluna, rotulo, plural, genero, opcoes,
        lambda d, selecao: d[d[coluna].isin(selecao)],
    )


def filtro_veiculo_compacto(df: pd.DataFrame, chave: str) -> pd.DataFrame:
    """Filtro compacto de Veículo como par "Grupo — Veículo" (decisão 15),
    em cascata: as opções refletem o df já filtrado por Grupo."""
    pares = (
        df[[COL_GRUPO, COL_VEICULO]]
        .drop_duplicates()
        .query(f"{COL_GRUPO} != '' and {COL_VEICULO} != ''")
    )
    opcoes = sorted(
        f"{g}{SEPARADOR_PAR}{v}" for g, v in pares.itertuples(index=False)
    )

    def _filtrar(d: pd.DataFrame, selecao: list[str]) -> pd.DataFrame:
        pares_ok = {tuple(p.split(SEPARADOR_PAR, 1)) for p in selecao}
        mascara = d.apply(
            lambda linha: (linha[COL_GRUPO], linha[COL_VEICULO]) in pares_ok,
            axis=1,
        )
        return d[mascara]

    return _motor_filtro(
        df, chave, "VEICULO_PAR", "Veículo", "veículos", "o", opcoes, _filtrar
    )


def botao_limpar_filtros(chave: str, rotulo: str = "Limpar filtros") -> None:
    """Retorna TODOS os filtros compactos da página ao padrão oficial
    (todos selecionados), descartando aplicados e rascunhos."""

    def _limpar() -> None:
        prefixo = f"{chave}_fc_"
        for k in [k for k in st.session_state if str(k).startswith(prefixo)]:
            del st.session_state[k]

    st.button(rotulo, key=f"{chave}_limpar_filtros", on_click=_limpar)
