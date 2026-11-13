"""Linhas do Top 5 Grupos, derivadas exclusivamente das métricas oficiais."""

from __future__ import annotations

import datetime as _dt

import pandas as pd

from src.data import metrics
from src.data.cleaning import COL_GRUPO


def linhas_ranking_grupos(
    df_ano: pd.DataFrame,
    df_dim: pd.DataFrame,
    ano: int,
    valor: metrics.Valor = "liquido",
    criterio_mes: metrics.CriterioMes = metrics.CRITERIO_MES_OFICIAL,
    hoje: _dt.date | None = None,
    meses_fechados: int | None = None,
) -> list[dict]:
    """Consolida o recorte anual já filtrado por GRUPO, sem joins ou deduplicação.

    Empates são resolvidos pelo nome oficial do grupo em ordem crescente.
    A participação usa todos os grupos elegíveis do recorte, antes do Top 5.
    O YoY compara somente meses encerrados quando ``meses_fechados`` é
    informado. O valor do ranking segue anual, incluindo meses em andamento.
    """
    agregado = metrics.agregado_por_dimensao(df_ano, COL_GRUPO, valor)
    if agregado.empty:
        return []
    total = float(agregado["valor"].sum())
    tendencias = metrics.tendencia_por_dimensao(
        df_dim, COL_GRUPO, ano, valor, criterio_mes, hoje, meses_fechados,
    )
    ordenado = agregado.sort_values(
        ["valor", COL_GRUPO], ascending=[False, True], kind="stable",
    )
    return [
        {
            "nome": linha[COL_GRUPO],
            "valor": float(linha["valor"]),
            "pct": float(linha["valor"]) / total * 100.0 if total > 0 else None,
            "tendencia": tendencias.get(linha[COL_GRUPO]),
        }
        for _, linha in ordenado.head(5).iterrows()
    ]
