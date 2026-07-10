"""FERRAMENTA TEMPORÁRIA DE DIAGNÓSTICO — auditoria de Vendas por ano.

Remover este módulo (e a aba correspondente no app.py) quando a
conciliação com a planilha estiver encerrada.

Não define nenhuma regra de negócio nova: reutiliza os buckets oficiais de
metrics.py e as colunas de cleaning.py, apenas CLASSIFICANDO por que cada
linha da aba do ano não entra no indicador Vendas exibido pelo dashboard
(base Vendas + recorte MÊS (GANHO) dentro do ano, critério padrão).
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from src.data import metrics
from src.data.cleaning import (
    COL_MES_GANHO_DATA,
    COL_STATUS,
    COL_VALOR_LIQUIDO,
    STATUS_VALIDOS,
)
from src.data.loader import COL_ANO_ABA

COL_MOTIVO = "MOTIVO_EXCLUSAO"

#: Colunas exibidas na tabela de auditoria
COLUNAS_RELATORIO = [
    "PI", "CLIENTE", "CAMPANHA", COL_VALOR_LIQUIDO, COL_STATUS, COL_MOTIVO,
]


def classificar_exclusao(linha: pd.Series, ano: int) -> Optional[str]:
    """Motivo pelo qual a linha NÃO entra em Vendas do ano; None se entra.

    Espelha (sem redefinir) as regras vigentes da v0.3 e o recorte temporal
    padrão do dashboard (MÊS GANHO dentro do ano selecionado).
    """
    status = linha[COL_STATUS]
    if status in metrics.STATUS_FORA_DO_CALCULO:
        return f"Status {status} fica fora de todas as somas (regra v0.3)"
    if status not in STATUS_VALIDOS:
        rotulo = status if status else "(VAZIO)"
        return (
            f"Status '{rotulo}' não reconhecido pelo vocabulário oficial "
            "(alerta de qualidade nº 4) — fora de todos os indicadores"
        )
    mes_ganho = linha[COL_MES_GANHO_DATA]
    if pd.isna(mes_ganho):
        return (
            "MÊS (GANHO) vazio ou inválido — fora do recorte temporal "
            "de qualquer ano no critério padrão"
        )
    if mes_ganho.year != ano:
        return (
            f"MÊS (GANHO) = {mes_ganho.strftime('%m/%Y')} — fora do recorte "
            f"de {ano} no critério padrão (Mês Ganho)"
        )
    return None


def auditar_vendas_ano(df: pd.DataFrame, ano: int) -> dict:
    """Concilia o total da aba do ano com o indicador Vendas do sistema.

    Recebe o DataFrame já limpo (mesmo objeto usado pelas páginas).

    Retorna dict com:
    - total_aba: soma de VALOR PI LIQUIDO de TODAS as linhas da aba do ano
    - vendas_sistema: Vendas do dashboard para o ano (base Vendas, ganho no ano)
    - diferenca: total_aba − vendas_sistema
    - excluidas: DataFrame das linhas da aba fora de Vendas, com COL_MOTIVO
    - total_excluidas: soma líquida das excluídas
    - outras_abas: linhas de OUTRAS abas contadas pelo sistema no ano
      (ganho no ano, lançadas em aba diferente)
    - total_outras_abas: soma líquida dessas linhas
    - residuo: diferenca − total_excluidas + total_outras_abas
      (0,00 quando as linhas listadas explicam exatamente a diferença)
    """
    aba = df[df[COL_ANO_ABA] == ano].copy()
    total_aba = float(aba[COL_VALOR_LIQUIDO].sum())

    # Indicador do sistema calculado pela PRÓPRIA função oficial
    # (metrics.vendas) sobre o mesmo recorte temporal do dashboard —
    # nenhum cálculo paralelo nesta auditoria.
    ganho_no_ano = df[COL_MES_GANHO_DATA].dt.year == ano
    vendas_sistema = metrics.vendas(df[ganho_no_ano])
    na_base_vendas = metrics.mascara_vendas(df)

    if aba.empty:
        excluidas = aba.assign(**{COL_MOTIVO: pd.Series(dtype=str)})
    else:
        aba[COL_MOTIVO] = aba.apply(classificar_exclusao, axis=1, ano=ano)
        excluidas = aba[aba[COL_MOTIVO].notna()]

    outras_abas = df[na_base_vendas & ganho_no_ano & (df[COL_ANO_ABA] != ano)]

    total_excluidas = float(excluidas[COL_VALOR_LIQUIDO].sum())
    total_outras = float(outras_abas[COL_VALOR_LIQUIDO].sum())
    diferenca = total_aba - vendas_sistema

    return {
        "total_aba": total_aba,
        "vendas_sistema": vendas_sistema,
        "diferenca": diferenca,
        "excluidas": excluidas,
        "total_excluidas": total_excluidas,
        "outras_abas": outras_abas,
        "total_outras_abas": total_outras,
        "residuo": diferenca - total_excluidas + total_outras,
    }
