"""AdTarget Intelligence — entrada única da aplicação (documento 03).

Fluxo: gate de senha -> carga de dados (cache 15 min) -> limpeza -> 3 abas.
Navegação em st.tabs() (3 páginas fixas); a migração para o sistema nativo
de multipágina está prevista apenas para a Fase 1.2 (6 páginas).

Erros de configuração (secrets ausentes, planilha inacessível, coluna
renomeada) geram mensagem amigável na tela, nunca stack trace bruto.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pages_content import (
    analitico_comercial,
    analitico_veiculos,
    performance_comercial,
)
from src.auth.gate import exigir_autenticacao
from src.data.cleaning import limpar_dataframe
from src.data.loader import ErroDeCarga, load_all_sheets

st.set_page_config(
    page_title="AdTarget Intelligence",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------- gate
# Roda antes de qualquer leitura de dado; se não autenticado, para aqui.
exigir_autenticacao()


# ---------------------------------------------------------------- dados
@st.cache_data(ttl=900, show_spinner="Carregando dados da planilha...")
def _carregar_dados_brutos(spreadsheet_id: str, credenciais: dict) -> pd.DataFrame:
    """Leitura bruta do Google Sheets com cache de 15 minutos,
    compartilhado entre todos os usuários (documento 03)."""
    return load_all_sheets(spreadsheet_id, credenciais)


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

with st.sidebar:
    st.title("AdTarget Intelligence")
    if st.button("Atualizar dados agora"):
        _carregar_dados_brutos.clear()
        st.rerun()
    st.caption(
        "Os dados são atualizados automaticamente a cada 15 minutos. "
        "Use o botão para forçar uma recarga imediata da planilha."
    )

try:
    dados_brutos = _carregar_dados_brutos(spreadsheet_id, credenciais)
except ErroDeCarga as erro:
    st.error(str(erro))
    st.stop()

dados = limpar_dataframe(dados_brutos)

# ---------------------------------------------------------------- páginas
aba1, aba2, aba3 = st.tabs(
    ["Performance Comercial", "Analítico Comercial", "Analítico Veículos"]
)
with aba1:
    performance_comercial.render(dados)
with aba2:
    analitico_comercial.render(dados)
with aba3:
    analitico_veiculos.render(dados)
