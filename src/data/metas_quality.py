"""Alertas puros da camada de metas, sem corrigir ou descartar registros."""

from __future__ import annotations

import pandas as pd

from src.data.metas import vigencia
from src.data.metas_schema import validar_metas
from src.data.quality_checks import AlertaQualidade


_FUSO = "America/Sao_Paulo"
_GRUPO_MES = ["GRUPO", "ANO", "MES"]


def _inicio_mes_seguinte(ano: int, mes: int) -> pd.Timestamp:
    """Primeiro instante depois do último dia do mês, no fuso da operação."""
    return pd.Timestamp(year=ano, month=mes, day=1, tz=_FUSO) + pd.DateOffset(
        months=1
    )


def revisoes_retroativas(
    metas: pd.DataFrame, *, data_referencia=None
) -> AlertaQualidade:
    """Detecta todas as revisões >= 2 registradas após o encerramento do slot.

    A revisão inicial nunca alerta. Revisões históricas continuam auditáveis,
    mesmo quando uma revisão mais recente já estiver vigente.
    """
    base = validar_metas(metas, data_referencia=data_referencia)
    mascara = [
        revisao >= 2
        and pd.Timestamp(criado).tz_convert(_FUSO)
        >= _inicio_mes_seguinte(int(ano), int(mes))
        for revisao, criado, ano, mes in zip(
            base["REVISAO"], base["CRIADO_EM"], base["ANO"], base["MES"]
        )
    ]
    afetadas = base.loc[mascara].copy(deep=True)
    return AlertaQualidade(
        codigo="METAS_REVISAO_RETROATIVA",
        titulo="Revisões de metas após o encerramento do mês",
        quantidade=len(afetadas),
        linhas=afetadas,
    )


def coexistencia_niveis(
    metas: pd.DataFrame, *, data_referencia=None
) -> AlertaQualidade:
    """Sinaliza grupo-mês com metas vigentes nos dois níveis comerciais.

    Atividade e valor não eliminam a coexistência. A precedência de GRUPO
    evita dupla contagem na engine, mas a inconsistência continua visível.
    """
    vigentes = vigencia(metas, data_referencia=data_referencia)
    niveis = vigentes.groupby(_GRUPO_MES, sort=True)["NIVEL_META"].nunique()
    conflitos = niveis[niveis > 1].index
    chaves = pd.MultiIndex.from_frame(vigentes[_GRUPO_MES])
    afetadas = vigentes.loc[chaves.isin(conflitos)].copy(deep=True)
    return AlertaQualidade(
        codigo="METAS_COEXISTENCIA_NIVEIS",
        titulo="Metas de Grupo e Veículo no mesmo grupo e mês",
        quantidade=len(conflitos),
        detalhes={
            "grupo_meses": [
                {"GRUPO": grupo, "ANO": int(ano), "MES": int(mes)}
                for grupo, ano, mes in conflitos
            ]
        },
        linhas=afetadas,
    )
