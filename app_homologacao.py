"""Isolated OAuth acceptance entrypoint.

Deploy this file in a SEPARATE Streamlit app. Synthetic data is the default;
real data is available only through an explicit read-only homologation mode.
The auth gate and all five page implementations run unchanged from app.py.
"""
from contextlib import ExitStack
from pathlib import Path
import runpy
from unittest.mock import patch

import pandas as pd
from pages_content import carteira_vendas

from src.data import cleaning, loader, metas_loader, representacoes
from src.data.metas_schema import COLUNAS_METAS, validar_metas

ANOS_REAIS_HOMOLOGACAO = frozenset({"2024", "2025", "2026"})
_load_all_sheets_original = loader.load_all_sheets


def vendas_sinteticas(*_):
    rows = []
    months = ("JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
              "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO")
    for year in (2025, 2026):
        for month in range(1, 13):
            for group in ("PARCEIRO SINTÉTICO ALFA", "PARCEIRO SINTÉTICO BETA"):
                row = {column: "SINTÉTICO" for column in cleaning.COLUNAS_TEXTO}
                row.update({
                    "GRUPO": group, "VEICULO": group + " FM",
                    "PI": f"SYN-{year}-{month}-{group[-4:]}",
                    "STATUS": "FATURADO", "ANO_ABA": year,
                    "MÊS (GANHO)": f"{months[month - 1]}/{year}",
                    "MÊS (VEICULAÇÃO)": f"{months[month - 1]}/{year}",
                    "VALOR PI BRUTO": month * 500.0,
                    "VALOR PI LIQUIDO": month * 400.0,
                    "VENCIMENTO PI": "CONTRA APRESENT.", "NOTA FISCAL": "SINTÉTICA",
                })
                rows.append(row)
    return pd.DataFrame(rows)


def metas_sinteticas(*_):
    return validar_metas(pd.DataFrame(columns=COLUNAS_METAS))


def representacoes_sinteticas(*_):
    return representacoes.CadastroRepresentacoes({})


def bloquear_cliente_real(*_, **__):
    raise RuntimeError("Homologação sintética não permite acesso ao Google Sheets.")


def filtrar_anos_homologacao(dados: pd.DataFrame) -> pd.DataFrame:
    """Restringe a homologação real às abas comerciais oficiais de 2024–2026."""
    if "ANO_ABA" not in dados.columns:
        raise ValueError("A fonte comercial não contém a coluna ANO_ABA.")
    return dados.loc[dados["ANO_ABA"].astype(str).isin(ANOS_REAIS_HOMOLOGACAO)].copy()


def vendas_reais_homologacao(spreadsheet_id, credenciais):
    """Lê a fonte oficial com o escopo spreadsheets.readonly do loader."""
    dados = _load_all_sheets_original(spreadsheet_id, credenciais)
    return filtrar_anos_homologacao(dados)


_documento_original = carteira_vendas.documento


def documento_homologacao(*args, **kwargs):
    # Keep links inside the separate acceptance environment, including iframe links.
    return _documento_original(*args, **kwargs).replace(
        "https://adtarget-intelligence-e7ftyu8hg9jcek5gaguhpm.streamlit.app/",
        "https://adtarget-intelligence-homologacao.streamlit.app/",
    )


if __name__ == "__main__":
    import streamlit as st

    modo_dados = st.secrets.get("homologation_data_mode", "synthetic")
    if modo_dados not in {"synthetic", "real_readonly"}:
        st.error("Modo de dados inválido para a homologação.")
        st.stop()

    patches = [patch.object(carteira_vendas, "documento", documento_homologacao)]
    if modo_dados == "real_readonly":
        # Authentication remains unchanged and the loader requests only the
        # spreadsheets.readonly OAuth scope.
        patches.append(patch.object(loader, "load_all_sheets", vendas_reais_homologacao))
    else:
        patches.extend([
            patch.object(loader, "load_all_sheets", vendas_sinteticas),
            patch.object(loader, "criar_cliente", bloquear_cliente_real),
            patch.object(metas_loader, "load_metas", metas_sinteticas),
            patch.object(representacoes, "load_representacoes", representacoes_sinteticas),
        ])

    # Contexts restore functions even on Streamlit stop/rerun. No auth is patched.
    with ExitStack() as stack:
        for contexto in patches:
            stack.enter_context(contexto)
        runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
