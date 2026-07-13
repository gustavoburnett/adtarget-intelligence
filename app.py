"""AdTarget Intelligence — entrada única da aplicação (documento 03).

Fluxo: gate de senha -> carga de dados (cache 15 min) -> limpeza -> 3 abas.
Navegação em st.tabs() (3 páginas fixas); a migração para o sistema nativo
de multipágina está prevista apenas para a Fase 1.2 (6 páginas).

Erros de configuração (secrets ausentes, planilha inacessível, coluna
renomeada) geram mensagem amigável na tela, nunca stack trace bruto.
"""

from __future__ import annotations

import datetime as _dt

import pandas as pd
import streamlit as st

from pages_content import (
    analitico_comercial,
    analitico_veiculos,
    auditoria_vendas,  # TEMPORÁRIO: remover junto com a aba de auditoria
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
def _carregar_dados_brutos(
    spreadsheet_id: str, credenciais: dict
) -> tuple[pd.DataFrame, _dt.datetime]:
    """Leitura bruta do Google Sheets com cache de 15 minutos,
    compartilhado entre todos os usuários (documento 03).

    Retorna também o horário da sincronização (momento real da leitura,
    preservado pelo cache) para o bloco de status da sidebar (Sprint 2A,
    item 5). O pipeline de leitura em si (load_all_sheets) é o mesmo.
    """
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

# --------------------------------------------------------------- sidebar
# Estrutura (Sprint 2A, item 5): nome do produto -> bloco de status dos
# dados (isolado do botão) -> botão de atualização -> nota de rodapé
# sobre o ciclo automático.
with st.sidebar:
    st.title("AdTarget Intelligence")

    minutos = max(0, int((_dt.datetime.now() - sincronizado_em).total_seconds() // 60))
    st.markdown("🟢 **Dados atualizados**")
    st.caption(
        f"há {minutos} min · sincronizado às {sincronizado_em:%H:%M}"
    )

    st.write("")  # espaçamento claro entre o bloco de status e o botão
    if st.button("Atualizar dados agora"):
        _carregar_dados_brutos.clear()
        st.rerun()
    st.caption("Os dados são atualizados automaticamente a cada 15 minutos.")

# ---------------------------------------------------------------- páginas
# A 4ª aba é uma FERRAMENTA TEMPORÁRIA de diagnóstico (auditoria de
# Vendas 2026). Remover a aba, o import acima, pages_content/
# auditoria_vendas.py e src/data/auditoria.py após o fechamento.
aba1, aba2, aba3, aba4 = st.tabs(
    [
        "Performance Comercial",
        "Analítico Comercial",
        "Analítico Veículos",
        "🔧 Auditoria de Vendas 2026",
    ]
)
with aba1:
    performance_comercial.render(dados)
with aba2:
    analitico_comercial.render(dados)
with aba3:
    analitico_veiculos.render(dados)
with aba4:
    auditoria_vendas.render(dados)
