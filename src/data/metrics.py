"""Cálculo de métricas oficiais (documento 02 — Regras de Negócio e Métricas).

Todas as funções:
- operam sobre o DataFrame já limpo por cleaning.limpar_dataframe
- recalculam tudo a partir das linhas brutas tratadas — nenhum total
  pré-calculado da planilha é lido (decisão 16)
- aceitam os dois toggles oficiais:
    * valor: "liquido" (padrão) ou "bruto"
    * criterio_mes: "ganho" (padrão) ou "veiculacao"
  Os comparativos (YTD e mês a mês) recalculam sobre o toggle ativo
  (decisão 26), nunca ficam fixos numa combinação só.

Classificação de status (documento 02):
- Faturamento Realizado = FATURADO + DIRETO
- Pipeline em Aberto    = CHECKING + AGUARD. DOC. VEÍCULO (exibido separado)
- Fora do cálculo       = CANCELADO, BONIFICADO, SEM_STATUS
"""

from __future__ import annotations

from typing import Literal, Optional

import pandas as pd

from src.data.cleaning import (
    COL_CAMPANHA,
    COL_CLIENTE,
    COL_GRUPO,
    COL_MES_GANHO_DATA,
    COL_MES_VEICULACAO_DATA,
    COL_STATUS,
    COL_VALOR_BRUTO,
    COL_VALOR_LIQUIDO,
    COL_VEICULO,
)

# ---------------------------------------------------------------------------
# Toggles e classificação de status
# ---------------------------------------------------------------------------

Valor = Literal["liquido", "bruto"]
CriterioMes = Literal["ganho", "veiculacao"]

#: Toggle Valor Líquido x Valor Bruto -> coluna correspondente
COLUNAS_VALOR: dict[str, str] = {
    "liquido": COL_VALOR_LIQUIDO,
    "bruto": COL_VALOR_BRUTO,
}

#: Toggle Mês Ganho x Mês Veiculação -> coluna de data derivada
COLUNAS_MES: dict[str, str] = {
    "ganho": COL_MES_GANHO_DATA,
    "veiculacao": COL_MES_VEICULACAO_DATA,
}

#: Buckets oficiais de status (documento 02)
STATUS_REALIZADO = frozenset({"FATURADO", "DIRETO"})
STATUS_PIPELINE = frozenset({"CHECKING", "AGUARD. DOC. VEÍCULO"})
STATUS_FORA_DO_CALCULO = frozenset({"CANCELADO", "BONIFICADO", "SEM_STATUS"})


def coluna_valor(valor: Valor = "liquido") -> str:
    """Resolve o toggle de métrica para o nome da coluna."""
    if valor not in COLUNAS_VALOR:
        raise ValueError(f"Toggle de valor inválido: {valor!r}")
    return COLUNAS_VALOR[valor]


def coluna_mes(criterio_mes: CriterioMes = "ganho") -> str:
    """Resolve o toggle de critério de mês para o nome da coluna."""
    if criterio_mes not in COLUNAS_MES:
        raise ValueError(f"Toggle de mês inválido: {criterio_mes!r}")
    return COLUNAS_MES[criterio_mes]


def mascara_realizado(df: pd.DataFrame) -> pd.Series:
    """Linhas classificadas como Faturamento Realizado (FATURADO + DIRETO)."""
    return df[COL_STATUS].isin(STATUS_REALIZADO)


def mascara_pipeline(df: pd.DataFrame) -> pd.Series:
    """Linhas classificadas como Pipeline em Aberto."""
    return df[COL_STATUS].isin(STATUS_PIPELINE)


# ---------------------------------------------------------------------------
# KPIs principais
# ---------------------------------------------------------------------------

def faturamento_realizado(df: pd.DataFrame, valor: Valor = "liquido") -> float:
    """Faturamento Realizado = soma de FATURADO + DIRETO no recorte."""
    return float(df.loc[mascara_realizado(df), coluna_valor(valor)].sum())


def faturamento_realizado_detalhado(
    df: pd.DataFrame, valor: Valor = "liquido"
) -> dict[str, float]:
    """Faturamento Realizado com a etiqueta secundária de vendas DIRETO.

    O valor originado de DIRETO é identificado separadamente porque não
    carrega comissão de agência (documento 02).
    """
    col = coluna_valor(valor)
    realizado = df[mascara_realizado(df)]
    direto = float(realizado.loc[realizado[COL_STATUS] == "DIRETO", col].sum())
    total = float(realizado[col].sum())
    return {"total": total, "direto": direto, "faturado": total - direto}


def pipeline_em_aberto(df: pd.DataFrame, valor: Valor = "liquido") -> float:
    """Pipeline em Aberto = soma de CHECKING + AGUARD. DOC. VEÍCULO.

    Exibido sempre separado do Faturamento Realizado, nunca somado a ele.
    """
    return float(df.loc[mascara_pipeline(df), coluna_valor(valor)].sum())


def ticket_medio(df: pd.DataFrame, valor: Valor = "liquido") -> Optional[float]:
    """Ticket Médio = Faturamento Realizado ÷ quantidade de PIs realizados.

    Retorna None quando não há PI realizado no recorte (a interface exibe
    "Sem dados no recorte selecionado", nunca erro de divisão por zero).
    """
    realizado = df[mascara_realizado(df)]
    if realizado.empty:
        return None
    return float(realizado[coluna_valor(valor)].sum()) / len(realizado)


def quantidade_campanhas(df: pd.DataFrame) -> int:
    """Quantidade de Campanhas = combinações distintas de Cliente + Campanha.

    Considera APENAS linhas de Faturamento Realizado (decisão 27): campanhas
    que existem só em Pipeline não entram, porque o KPI mede volume
    operacional já concretizado.
    """
    realizado = df[mascara_realizado(df)]
    if realizado.empty:
        return 0
    return int(realizado[[COL_CLIENTE, COL_CAMPANHA]].drop_duplicates().shape[0])


def cancelado_bonificado(df: pd.DataFrame) -> dict[str, float]:
    """Indicador de Cancelado/Bonificado como CONTAGEM de PIs (documento 02).

    Não é soma monetária: na base real esses status já vêm com valor zerado.
    O valor monetário eventualmente diferente de zero (situação excepcional,
    coberta pelo alerta 5 de qualidade) é retornado como informação
    secundária, nunca como número principal do bloco.
    """
    cancelados = df[df[COL_STATUS] == "CANCELADO"]
    bonificados = df[df[COL_STATUS] == "BONIFICADO"]
    return {
        "cancelados": len(cancelados),
        "bonificados": len(bonificados),
        "valor_bruto_secundario": float(
            cancelados[COL_VALOR_BRUTO].sum() + bonificados[COL_VALOR_BRUTO].sum()
        ),
        "valor_liquido_secundario": float(
            cancelados[COL_VALOR_LIQUIDO].sum()
            + bonificados[COL_VALOR_LIQUIDO].sum()
        ),
    }


# ---------------------------------------------------------------------------
# Séries temporais e comparativos
# ---------------------------------------------------------------------------

def _realizado_do_ano(
    df: pd.DataFrame, ano: int, criterio_mes: CriterioMes
) -> pd.DataFrame:
    """Linhas de Faturamento Realizado cujo mês (no critério ativo) cai no ano.

    Linhas com mês inválido/não preenchido (NaT) ficam fora das métricas
    temporais — elas continuam contando nos KPIs não temporais.
    """
    col_mes = coluna_mes(criterio_mes)
    base = df[mascara_realizado(df)]
    return base[base[col_mes].dt.year == ano]


def evolucao_mensal(
    df: pd.DataFrame,
    ano: int,
    valor: Valor = "liquido",
    criterio_mes: CriterioMes = "ganho",
) -> dict[int, float]:
    """Faturamento Realizado por mês do ano selecionado.

    Retorna {número do mês: valor} APENAS para meses com dado. Meses sem
    dado (incluindo meses futuros) não aparecem no dicionário — a camada de
    gráfico os renderiza como lacuna, nunca como zero (documento 02).
    """
    recorte = _realizado_do_ano(df, ano, criterio_mes)
    if recorte.empty:
        return {}
    serie = recorte.groupby(recorte[coluna_mes(criterio_mes)].dt.month)[
        coluna_valor(valor)
    ].sum()
    return {int(mes): float(v) for mes, v in serie.items()}


def comparativo_mensal(
    df: pd.DataFrame,
    ano: int,
    valor: Valor = "liquido",
    criterio_mes: CriterioMes = "ganho",
) -> pd.DataFrame:
    """Comparativo mês a mês: cada mês do ano contra o mesmo mês do anterior.

    Retorna DataFrame indexado de 1 a 12 com as colunas "atual" e
    "anterior". Meses sem dado ficam como NaN (lacuna no gráfico). O ano
    anterior é sempre (ano selecionado − 1), calculado automaticamente.
    """
    atual = evolucao_mensal(df, ano, valor, criterio_mes)
    anterior = evolucao_mensal(df, ano - 1, valor, criterio_mes)
    meses = range(1, 13)
    return pd.DataFrame(
        {
            "atual": [atual.get(m) for m in meses],
            "anterior": [anterior.get(m) for m in meses],
        },
        index=pd.Index(meses, name="mes"),
        dtype=float,
    )


def ytd(
    df: pd.DataFrame,
    ano: int,
    valor: Valor = "liquido",
    criterio_mes: CriterioMes = "ganho",
) -> dict[str, Optional[float]]:
    """YTD: acumulado de janeiro até o último mês com dado no ano selecionado,
    comparado ao MESMO intervalo do ano anterior.

    Nunca compara ano parcial atual com ano completo anterior (documento 02).

    Retorno:
    - "atual": soma do ano selecionado até o mês limite
    - "anterior": soma do ano anterior no mesmo intervalo, ou None quando
      não existe nenhum dado do ano anterior ("sem comparativo disponível")
    - "variacao_pct": percentual de variação, ou None quando não calculável
    - "mes_limite": último mês com dado no ano selecionado, ou None
    """
    recorte_atual = _realizado_do_ano(df, ano, criterio_mes)
    col_mes = coluna_mes(criterio_mes)
    col_val = coluna_valor(valor)

    if recorte_atual.empty:
        mes_limite: Optional[int] = None
        total_atual = 0.0
    else:
        mes_limite = int(recorte_atual[col_mes].dt.month.max())
        total_atual = float(recorte_atual[col_val].sum())

    recorte_anterior = _realizado_do_ano(df, ano - 1, criterio_mes)
    if recorte_anterior.empty:
        # Sem dado algum do ano anterior: "sem comparativo disponível"
        return {
            "atual": total_atual,
            "anterior": None,
            "variacao_pct": None,
            "mes_limite": mes_limite,
        }

    if mes_limite is None:
        total_anterior = 0.0
    else:
        comparavel = recorte_anterior[
            recorte_anterior[col_mes].dt.month <= mes_limite
        ]
        total_anterior = float(comparavel[col_val].sum())

    variacao: Optional[float]
    if total_anterior == 0.0:
        variacao = None  # divisão por zero nunca vira erro nem percentual inválido
    else:
        variacao = (total_atual - total_anterior) / total_anterior * 100.0

    return {
        "atual": total_atual,
        "anterior": total_anterior,
        "variacao_pct": variacao,
        "mes_limite": mes_limite,
    }


# ---------------------------------------------------------------------------
# Agregações por Grupo + Veículo (regra transversal — decisão 15)
# ---------------------------------------------------------------------------

def agregado_por_grupo_veiculo(
    df: pd.DataFrame, valor: Valor = "liquido"
) -> pd.DataFrame:
    """Agregação SEMPRE pela dupla Grupo + Veículo, nunca veículo isolado.

    Motivo (documento 02): existem veículos com o mesmo nome comercial em
    grupos diferentes; agregar só pelo nome misturaria entidades distintas.

    Retorna, por par Grupo+Veículo (apenas Faturamento Realizado):
    faturamento bruto, líquido, ticket médio, quantidade de PIs e % do total
    (calculado sobre o toggle de valor ativo).
    """
    realizado = df[mascara_realizado(df)]
    if realizado.empty:
        return pd.DataFrame(
            columns=[
                COL_GRUPO,
                COL_VEICULO,
                "faturamento_bruto",
                "faturamento_liquido",
                "ticket_medio",
                "qtd_pis",
                "pct_do_total",
            ]
        )

    agg = (
        realizado.groupby([COL_GRUPO, COL_VEICULO], as_index=False)
        .agg(
            faturamento_bruto=(COL_VALOR_BRUTO, "sum"),
            faturamento_liquido=(COL_VALOR_LIQUIDO, "sum"),
            qtd_pis=(COL_STATUS, "size"),
        )
    )
    col_ref = (
        "faturamento_liquido" if valor == "liquido" else "faturamento_bruto"
    )
    agg["ticket_medio"] = agg[col_ref] / agg["qtd_pis"]
    total = agg[col_ref].sum()
    agg["pct_do_total"] = (agg[col_ref] / total * 100.0) if total else 0.0
    return agg.sort_values(col_ref, ascending=False).reset_index(drop=True)


def veiculos_ativos(df: pd.DataFrame) -> int:
    """Veículos Ativos = pares Grupo+Veículo com >=1 PI em Faturamento Realizado."""
    realizado = df[mascara_realizado(df)]
    if realizado.empty:
        return 0
    return int(realizado[[COL_GRUPO, COL_VEICULO]].drop_duplicates().shape[0])


# ---------------------------------------------------------------------------
# Agregações de apresentação (consumidas pela interface — documento 04).
# Nenhuma regra de negócio nova: apenas reorganizam os mesmos buckets e
# toggles oficiais para os gráficos e rankings dos wireframes.
# ---------------------------------------------------------------------------

#: Ordem oficial de exibição dos status (documento 04, gráfico por status)
ORDEM_STATUS = [
    "FATURADO",
    "DIRETO",
    "CHECKING",
    "AGUARD. DOC. VEÍCULO",
    "CANCELADO",
    "BONIFICADO",
    "SEM_STATUS",
]


def resumo_por_status(df: pd.DataFrame, valor: Valor = "liquido") -> pd.DataFrame:
    """Valor e contagem de PIs por status, na ordem oficial de exibição.

    Alimenta o gráfico de saúde da carteira da página Analítico Faturamento
    (documento 04). Status sem ocorrência no recorte não aparecem.
    """
    col = coluna_valor(valor)
    if df.empty:
        return pd.DataFrame(columns=[COL_STATUS, "valor", "qtd_pis"])
    agg = (
        df.groupby(COL_STATUS)
        .agg(valor=(col, "sum"), qtd_pis=(COL_STATUS, "size"))
        .reset_index()
    )
    ordem = {status: i for i, status in enumerate(ORDEM_STATUS)}
    agg["_ordem"] = agg[COL_STATUS].map(lambda s: ordem.get(s, len(ordem)))
    return agg.sort_values("_ordem").drop(columns="_ordem").reset_index(drop=True)


def evolucao_mensal_ticket_medio(
    df: pd.DataFrame,
    ano: int,
    valor: Valor = "liquido",
    criterio_mes: CriterioMes = "ganho",
) -> dict[int, float]:
    """Ticket Médio por mês do ano selecionado (documento 04, página 1).

    Mesma definição oficial do Ticket Médio (Faturamento Realizado ÷ PIs
    realizados), aplicada mês a mês. Meses sem dado não aparecem no
    dicionário (lacuna no gráfico, nunca zero).
    """
    recorte = _realizado_do_ano(df, ano, criterio_mes)
    if recorte.empty:
        return {}
    grupos = recorte.groupby(recorte[coluna_mes(criterio_mes)].dt.month)
    serie = grupos[coluna_valor(valor)].sum() / grupos.size()
    return {int(mes): float(v) for mes, v in serie.items()}


def agregado_por_dimensao(
    df: pd.DataFrame, coluna: str, valor: Valor = "liquido"
) -> pd.DataFrame:
    """Faturamento Realizado agregado por uma dimensão (Agência, Cliente...).

    Alimenta os rankings Top 5 e completos dos wireframes. Apenas linhas de
    Faturamento Realizado, ordenado do maior para o menor. Para veículo,
    usar SEMPRE agregado_por_grupo_veiculo (decisão 15), nunca esta função.
    """
    if coluna == COL_VEICULO:
        raise ValueError(
            "Agregação por veículo deve usar agregado_por_grupo_veiculo "
            "(sempre Grupo + Veículo, nunca veículo isolado — decisão 15)."
        )
    realizado = df[mascara_realizado(df)]
    if realizado.empty:
        return pd.DataFrame(columns=[coluna, "valor", "qtd_pis"])
    col = coluna_valor(valor)
    agg = (
        realizado.groupby(coluna)
        .agg(valor=(col, "sum"), qtd_pis=(coluna, "size"))
        .reset_index()
    )
    return agg.sort_values("valor", ascending=False).reset_index(drop=True)
