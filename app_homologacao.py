"""Isolated OAuth acceptance entrypoint: native auth, synthetic data only.

Deploy this file in a SEPARATE Streamlit app. Never use production data secrets.
The auth gate and all five page implementations run unchanged from app.py.
"""
from pathlib import Path
import runpy
from unittest.mock import patch

import pandas as pd

from src.data import cleaning, loader, metas_loader, representacoes
from src.data.metas_schema import COLUNAS_METAS, validar_metas


def vendas_sinteticas(*_):
    rows = []
    for year in (2025, 2026):
        for month in range(1, 13):
            for group in ("PARCEIRO SINTÉTICO ALFA", "PARCEIRO SINTÉTICO BETA"):
                row = {column: "SINTÉTICO" for column in cleaning.COLUNAS_TEXTO}
                row.update({
                    "GRUPO": group, "VEICULO": group + " FM",
                    "PI": f"SYN-{year}-{month}-{group[-4:]}",
                    "STATUS": "FATURADO", "ANO_ABA": year,
                    "MÊS (GANHO)": pd.Timestamp(year, month, 1),
                    "MÊS (VEICULAÇÃO)": pd.Timestamp(year, month, 1),
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


if __name__ == "__main__":
    # Contexts restore functions even on Streamlit stop/rerun. No auth is patched.
    with (
        patch.object(loader, "load_all_sheets", vendas_sinteticas),
        patch.object(loader, "criar_cliente", bloquear_cliente_real),
        patch.object(metas_loader, "load_metas", metas_sinteticas),
        patch.object(representacoes, "load_representacoes", representacoes_sinteticas),
    ):
        runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
