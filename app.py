"""AdTarget Intelligence — entrada única da aplicação.

A SIDEBAR é a navegação oficial do produto: Performance Comercial,
Metas e Resultados, Analítico Comercial, Analítico Veículos e,
temporariamente, 🔧 Auditoria. A sidebar reúne marca, navegação e status
dos dados (somente leitura); o masthead mantém o título da página ativa.

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
    auditoria_vendas,  # ferramenta de validação — visível só com dev_auditoria
    metas_resultados,
    performance_comercial,
)
from src.auth.gate import exigir_autenticacao
from src.components import cards, design_styles, performance_styles, shell
from src.components.design_tokens import SIDEBAR_WIDTH
from src.data.cleaning import limpar_dataframe
from src.data.loader import ErroDeCarga, load_all_sheets
from src.data.metas_loader import load_metas
from src.data.metas_schema import ErroDeMetas

st.set_page_config(
    page_title="AdTarget Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state=SIDEBAR_WIDTH,
)

# ---------------------------------------------------------------- gate
exigir_autenticacao()

# Conteúdo legado preservado; fundação do shell no Design System v1.0.1.
st.markdown(cards.CSS_GLOBAL, unsafe_allow_html=True)
st.html(shell.font_style())
st.html(design_styles.CSS_SHELL)


# ---------------------------------------------------------------- dados
@st.cache_data(ttl=900, show_spinner="Carregando dados da planilha...")
def _carregar_dados_brutos(
    spreadsheet_id: str, credenciais: dict
) -> tuple[pd.DataFrame, _dt.datetime]:
    """Leitura bruta do Google Sheets com cache de 15 minutos,
    compartilhado entre todos os usuários (documento 03). Retorna também o
    horário real da sincronização para o bloco de status."""
    return load_all_sheets(spreadsheet_id, credenciais), _dt.datetime.now()


@st.cache_data(ttl=900, show_spinner="Carregando metas da planilha...")
def _carregar_metas(spreadsheet_id: str, credenciais: dict) -> pd.DataFrame:
    """Cache independente de METAS, consultado somente na visão de metas."""
    return load_metas(spreadsheet_id, credenciais)


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
    "Metas e Resultados": (
        metas_resultados.render,
        "Atingimento de metas e projeção no perímetro comercial",
    ),
    "Analítico Comercial": (
        analitico_comercial.render,
        "Carteira completa, PI a PI, com filtros finos e alertas de qualidade",
    ),
    "Analítico Veículos": (
        analitico_veiculos.render,
        "Vendas por grupo e veículo, rankings e consolidado",
    ),
}

# Ferramenta de validação de indicadores (Release 1.0, decisão 38): a
# Auditoria sai da navegação de produção, mas permanece no produto para
# reuso quando for preciso conciliar indicadores com a planilha. Para
# habilitar em desenvolvimento: `dev_auditoria = true` no secrets.toml.
if st.secrets.get("dev_auditoria", False):
    PAGINAS["🔧 Auditoria (dev)"] = (
        auditoria_vendas.render,
        "Conciliação do indicador Vendas com a planilha de origem",
    )

# --------------------------------------------------------------- sidebar
# Shell compartilhado; valores, chave de seleção e roteamento preservados.
minutos = max(
    0, int((_dt.datetime.now() - sincronizado_em).total_seconds() // 60)
)
with st.sidebar:
    with st.container(key="design_sidebar_shell"):
        with st.container(key="design_sidebar_brand"):
            st.markdown(shell.sidebar_brand(), unsafe_allow_html=True)
        with st.container(key="design_sidebar_nav"):
            pagina_ativa = st.radio(
                "Navegação",
                list(PAGINAS),
                key="nav_pagina",
                label_visibility="collapsed",
                format_func=shell.navigation_label,
            )
        with st.container(key="design_sidebar_footer"):
            st.markdown(
                shell.sidebar_footer(sincronizado_em, minutos),
                unsafe_allow_html=True,
            )

# -------------------------------------------------------------- masthead
render_pagina, subtitulo = PAGINAS[pagina_ativa]
titulo_visivel = pagina_ativa.replace("🔧 ", "")

if pagina_ativa == "Performance Comercial":
    st.html(performance_styles.CSS_PERFORMANCE)
    with st.container(
        key="design_performance_header", horizontal=True,
        vertical_alignment="center", gap="medium",
    ):
        col_titulo = st.container(key="design_performance_title", width="stretch")
        col_acoes = st.container(
            key="design_performance_actions", width="content", horizontal=True,
            vertical_alignment="center", gap="small",
        )
else:
    col_titulo, col_acoes = st.columns([4, 1.6], vertical_alignment="center")
with col_titulo:
    cards.masthead(titulo_visivel, subtitulo)
with col_acoes:
    st.markdown(
        f'<div class="atg-updated">atualizado há {minutos} min</div>',
        unsafe_allow_html=True,
        width="content" if pagina_ativa == "Performance Comercial" else "auto",
    )
    if pagina_ativa == "Performance Comercial":
        col_refresh = st.container(key="design_performance_refresh", width="content")
        col_tema = st.container(key="design_performance_theme", width="content")
    else:
        col_refresh, col_tema = st.columns([3, 1])
    with col_refresh:
        if st.button("Atualizar" if pagina_ativa == "Performance Comercial" else "↻ Atualizar",
                     icon=":material/refresh:" if pagina_ativa == "Performance Comercial" else None,
                     key="masthead_refresh",
                     help="Recarregar os dados da planilha agora"):
            _carregar_dados_brutos.clear()
            _carregar_metas.clear()
            st.session_state["_dados_recarregados"] = True
            st.rerun()
    with col_tema:
        st.button(
            "☾", key="masthead_tema", disabled=True,
            help="Tema escuro — em estudo (Design System §5.10)",
        )

# ---------------------------------------------------------------- página
if pagina_ativa == "Performance Comercial":
    render_pagina(
        dados, sincronizado_em=sincronizado_em,
        carregar_metas=lambda: _carregar_metas(spreadsheet_id, credenciais),
    )
elif pagina_ativa == "Metas e Resultados":
    try:
        metas_df = _carregar_metas(spreadsheet_id, credenciais)
    except ErroDeMetas as erro:
        render_pagina(dados, erro_metas=erro)
    else:
        render_pagina(dados, metas_df=metas_df)
else:
    render_pagina(dados)
