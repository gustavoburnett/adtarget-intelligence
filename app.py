"""AdTarget Intelligence — entrada única da aplicação.

Sprint 2B: a SIDEBAR é a navegação oficial do produto (decisão 34 —
supersede as abas do documento 03): Performance Comercial, Analítico
Comercial, Analítico Veículos e, temporariamente, 🔧 Auditoria (removida
junto com a ferramenta). Ações vivem no Masthead; a sidebar tem apenas
logo, navegação e o bloco de status dos dados (somente leitura).

Fluxo: gate de senha -> carga com cache (15 min) -> limpeza -> shell
(sidebar + masthead) -> página ativa. Erros de configuração geram mensagem
amigável, nunca stack trace.
"""

from __future__ import annotations

import datetime as _dt

import pandas as pd
import streamlit as st

from pages_content import (
    analitico_comercial,
    analitico_veiculos,
    auditoria_vendas,  # TEMPORÁRIO: remover junto com o item de navegação
    performance_comercial,
)
from src.auth.gate import exigir_autenticacao
from src.components import cards
from src.data.cleaning import limpar_dataframe
from src.data.loader import ErroDeCarga, load_all_sheets

st.set_page_config(
    page_title="AdTarget Intelligence",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------- gate
exigir_autenticacao()

# Fundação visual da Sprint 2B (Design System aplicado — 2B.1)
st.markdown(cards.CSS_GLOBAL, unsafe_allow_html=True)


# ---------------------------------------------------------------- dados
@st.cache_data(ttl=900, show_spinner="Carregando dados da planilha...")
def _carregar_dados_brutos(
    spreadsheet_id: str, credenciais: dict
) -> tuple[pd.DataFrame, _dt.datetime]:
    """Leitura bruta do Google Sheets com cache de 15 minutos,
    compartilhado entre todos os usuários (documento 03). Retorna também o
    horário real da sincronização para o bloco de status."""
    return load_all_sheets(spreadsheet_id, credenciais), _dt.datetime.now()


def _validar_secrets() -> tuple[str, dict]:
    """Valida a presença dos secrets de dados, com erro amigável."""
    faltando = []
    if "spreadsheet_id" not in st.secrets:
        faltando.append("`spreadsheet_id`")
    if "gcp_service_account" not in st.secrets:
        faltando.append("`[gcp_service_account]`")
    if faltando:
        st.error(
            "Credenciais do Google não configuradas: falta "
            + " e ".join(faltando)
            + " no secrets.toml (local) ou na interface de secrets do "
            "Streamlit Cloud. Use .streamlit/secrets.toml.example como modelo."
        )
        st.stop()
    return st.secrets["spreadsheet_id"], dict(st.secrets["gcp_service_account"])


spreadsheet_id, credenciais = _validar_secrets()

try:
    dados_brutos, sincronizado_em = _carregar_dados_brutos(
        spreadsheet_id, credenciais
    )
except ErroDeCarga as erro:
    st.error(str(erro))
    st.stop()

dados = limpar_dataframe(dados_brutos)

# Toast de confirmação pós-atualização manual (estado de sucesso — 2B.9)
if st.session_state.pop("_dados_recarregados", False):
    st.toast("Dados atualizados", icon="✅")

# --------------------------------------------------------------- páginas
PAGINAS = {
    "Performance Comercial": (
        performance_comercial.render,
        "Visão geral de vendas, campanhas e faturamento",
    ),
    "Analítico Comercial": (
        analitico_comercial.render,
        "Carteira completa, PI a PI, com filtros finos e alertas de qualidade",
    ),
    "Analítico Veículos": (
        analitico_veiculos.render,
        "Vendas por grupo e veículo, rankings e consolidado",
    ),
    "🔧 Auditoria (temp.)": (
        auditoria_vendas.render,
        "Conciliação do indicador Vendas com a planilha de origem",
    ),
}

# --------------------------------------------------------------- sidebar
# Estrutura (DS §5.8): logo -> navegação -> separador -> status. Sem botão.
with st.sidebar:
    st.markdown(
        '<div class="atg-logo-word"><b>Ad</b>Target</div>'
        '<div class="atg-logo-sub">INTELLIGENCE</div><br>',
        unsafe_allow_html=True,
    )
    pagina_ativa = st.radio(
        "Navegação",
        list(PAGINAS),
        key="nav_pagina",
        label_visibility="collapsed",
    )
    st.divider()
    minutos = max(
        0, int((_dt.datetime.now() - sincronizado_em).total_seconds() // 60)
    )
    # Sprint 3B (P7): status em uma linha, sem jargão
    st.markdown(
        '<div class="atg-status-line"><span class="atg-status-dot"></span>'
        f"Sincronizado às {sincronizado_em:%H:%M} · há {minutos} min</div>",
        unsafe_allow_html=True,
    )

# -------------------------------------------------------------- masthead
render_pagina, subtitulo = PAGINAS[pagina_ativa]
titulo_visivel = pagina_ativa.replace("🔧 ", "")

col_titulo, col_acoes = st.columns([4, 1.6], vertical_alignment="center")
with col_titulo:
    cards.masthead(titulo_visivel, subtitulo)
with col_acoes:
    st.markdown(
        f'<div class="atg-updated">atualizado há {minutos} min</div>',
        unsafe_allow_html=True,
    )
    col_refresh, col_tema = st.columns([3, 1])
    with col_refresh:
        if st.button("↻ Atualizar", key="masthead_refresh",
                     help="Recarregar os dados da planilha agora"):
            _carregar_dados_brutos.clear()
            st.session_state["_dados_recarregados"] = True
            st.rerun()
    with col_tema:
        st.button(
            "☾", key="masthead_tema", disabled=True,
            help="Tema escuro — em estudo (Design System §5.10)",
        )

# ---------------------------------------------------------------- página
render_pagina(dados)
