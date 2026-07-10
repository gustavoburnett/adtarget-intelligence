"""Cálculo dos indicadores comerciais oficiais.

REGRA VIGENTE (definida pelo responsável do projeto em 2026-07-09,
supersedendo a versão 0.2 da documentação — pendente registro v0.3):

| Indicador    | Status somados                                            |
|--------------|-----------------------------------------------------------|
| **Vendas**   | A VEICULAR, EM VEICULAÇÃO, CHECKING, AGUARD. DOC. VEÍCULO,|
|              | FATURADO, DIRETO                                          |
| **Faturado** | FATURADO, DIRETO                                          |
| **Em Aberto**| A VEICULAR, EM VEICULAÇÃO, CHECKING, AGUARD. DOC. VEÍCULO |

Identidade garantida: **Em Aberto = Vendas − Faturado**.
CANCELADO e BONIFICADO ficam fora de qualquer soma (apenas contagem).

Todas as funções:
- operam sobre o DataFrame já limpo por cleaning.limpar_dataframe
- recalculam tudo a partir das linhas brutas tratadas — nenhum total
  pré-calculado da planilha é lido
- aceitam os dois toggles oficiais:
    * valor: "liquido" (padrão) ou "bruto"
    * criterio_mes: CRITERIO_MES_OFICIAL ("veiculacao", regra oficial
      v0.4) como padrão, "ganho" como análise alternativa
  Os comparativos (YTD e mês a mês) recalculam sobre o toggle ativo.

As métricas derivadas (YTD, evolução mensal, Ticket Médio, Quantidade de
Campanhas, rankings e agregações) usam a base **Vendas**, coerente com o
indicador principal da visão comercial.
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

#: REGRA OFICIAL DE NEGÓCIO (v0.4, 2026-07-10) — FONTE ÚNICA DE VERDADE.
#: O KPI oficial de Vendas da AdTarget usa MÊS (VEICULAÇÃO) como critério
#: temporal padrão, em todo o produto. MÊS (GANHO) permanece disponível
#: apenas como análise alternativa, via toggle. Nenhum outro ponto do
#: código define o critério padrão: toda função de métrica usa esta
#: constante como default, e o toggle da interface inicializa a partir
#: dela (src/components/filters.py).
CRITERIO_MES_OFICIAL: CriterioMes = "veiculacao"

#: Rótulos de exibição do critério temporal (uso em interface/relatórios)
ROTULOS_CRITERIO_MES: dict[str, str] = {
    "ganho": "Mês (Ganho)",
    "veiculacao": "Mês (Veiculação)",
}

#: Buckets oficiais (regra comercial de 2026-07-09)
STATUS_FATURADO = frozenset({"FATURADO", "DIRETO"})
STATUS_EM_ABERTO = frozenset(
    {"A VEICULAR", "EM VEICULAÇÃO", "CHECKING", "AGUARD. DOC. VEÍCULO"}
)
STATUS_VENDAS = STATUS_FATURADO | STATUS_EM_ABERTO
STATUS_FORA_DO_CALCULO = frozenset({"CANCELADO", "BONIFICADO"})


def coluna_valor(valor: Valor = "liquido") -> str:
    """Resolve o toggle de métrica para o nome da coluna."""
    if valor not in COLUNAS_VALOR:
        raise ValueError(f"Toggle de valor inválido: {valor!r}")
    return COLUNAS_VALOR[valor]


def coluna_mes(criterio_mes: CriterioMes = CRITERIO_MES_OFICIAL) -> str:
    """Resolve o toggle de critério de mês para o nome da coluna."""
    if criterio_mes not in COLUNAS_MES:
        raise ValueError(f"Toggle de mês inválido: {criterio_mes!r}")
    return COLUNAS_MES[criterio_mes]


def mascara_vendas(df: pd.DataFrame) -> pd.Series:
    """Linhas classificadas como Vendas (tudo exceto cancelado/bonificado
    e status fora do vocabulário)."""
    return df[COL_STATUS].isin(STATUS_VENDAS)


def mascara_faturado(df: pd.DataFrame) -> pd.Series:
    """Linhas já faturadas (FATURADO + DIRETO)."""
    return df[COL_STATUS].isin(STATUS_FATURADO)


def mascara_em_aberto(df: pd.DataFrame) -> pd.Series:
    """Linhas vendidas e ainda não faturadas."""
    return df[COL_STATUS].isin(STATUS_EM_ABERTO)


# ---------------------------------------------------------------------------
# Indicadores principais
# ---------------------------------------------------------------------------

def vendas(df: pd.DataFrame, valor: Valor = "liquido") -> float:
    """Vendas = soma dos 6 status de venda, no recorte de filtros."""
    return float(df.loc[mascara_vendas(df), coluna_valor(valor)].sum())


def faturado(df: pd.DataFrame, valor: Valor = "liquido") -> float:
    """Faturado = soma de FATURADO + DIRETO."""
    return float(df.loc[mascara_faturado(df), coluna_valor(valor)].sum())


def em_aberto(df: pd.DataFrame, valor: Valor = "liquido") -> float:
    """Em Aberto = campanhas vendidas ainda não faturadas.

    Por construção dos buckets, equivale a Vendas − Faturado.
    """
    return float(df.loc[mascara_em_aberto(df), coluna_valor(valor)].sum())


def vendas_detalhado(df: pd.DataFrame, valor: Valor = "liquido") -> dict[str, float]:
    """Vendas com a decomposição oficial: total, faturado e em aberto."""
    total = vendas(df, valor)
    ja_faturado = faturado(df, valor)
    return {
        "total": total,
        "faturado": ja_faturado,
        "em_aberto": total - ja_faturado,
    }


def ticket_medio(df: pd.DataFrame, valor: Valor = "liquido") -> Optional[float]:
    """Ticket Médio = Vendas ÷ quantidade de PIs na base Vendas.

    Retorna None quando não há PI no recorte (a interface exibe
    "Sem dados no recorte selecionado", nunca erro de divisão por zero).
    """
    base = df[mascara_vendas(df)]
    if base.empty:
        return None
    return float(base[coluna_valor(valor)].sum()) / len(base)


def quantidade_campanhas(df: pd.DataFrame) -> int:
    """Quantidade de Campanhas = combinações distintas de Cliente + Campanha
    na base Vendas (cancelados/bonificados fora)."""
    base = df[mascara_vendas(df)]
    if base.empty:
        return 0
    return int(base[[COL_CLIENTE, COL_CAMPANHA]].drop_duplicates().shape[0])


def cancelado_bonificado(df: pd.DataFrame) -> dict[str, float]:
    """Indicador de Cancelado/Bonificado como CONTAGEM de PIs.

    Não é soma monetária: esses status vêm com valor zerado na origem.
    O valor eventualmente diferente de zero (excepcional, coberto pelo
    alerta de qualidade) é retornado como informação secundária.
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
# Séries temporais e comparativos (base Vendas)
# ---------------------------------------------------------------------------

def _vendas_do_ano(
    df: pd.DataFrame, ano: int, criterio_mes: CriterioMes
) -> pd.DataFrame:
    """Linhas da base Vendas cujo mês (no critério ativo) cai no ano.

    Linhas com mês inválido/não preenchido (NaT) ficam fora das métricas
    temporais — elas continuam contando nos KPIs não temporais.
    """
    col_mes = coluna_mes(criterio_mes)
    base = df[mascara_vendas(df)]
    return base[base[col_mes].dt.year == ano]


def evolucao_mensal(
    df: pd.DataFrame,
    ano: int,
    valor: Valor = "liquido",
    criterio_mes: CriterioMes = CRITERIO_MES_OFICIAL,
) -> dict[int, float]:
    """Vendas por mês do ano selecionado.

    Retorna {número do mês: valor} APENAS para meses com dado. Meses sem
    dado (incluindo meses futuros) não aparecem no dicionário — a camada de
    gráfico os renderiza como lacuna, nunca como zero.
    """
    recorte = _vendas_do_ano(df, ano, criterio_mes)
    if recorte.empty:
        return {}
    serie = recorte.groupby(recorte[coluna_mes(criterio_mes)].dt.month)[
        coluna_valor(valor)
    ].sum()
    return {int(mes): float(v) for mes, v in serie.items()}


def evolucao_mensal_ticket_medio(
    df: pd.DataFrame,
    ano: int,
    valor: Valor = "liquido",
    criterio_mes: CriterioMes = CRITERIO_MES_OFICIAL,
) -> dict[int, float]:
    """Ticket Médio (base Vendas) mês a mês, com lacuna em mês sem dado."""
    recorte = _vendas_do_ano(df, ano, criterio_mes)
    if recorte.empty:
        return {}
    grupos = recorte.groupby(recorte[coluna_mes(criterio_mes)].dt.month)
    serie = grupos[coluna_valor(valor)].sum() / grupos.size()
    return {int(mes): float(v) for mes, v in serie.items()}


def comparativo_mensal(
    df: pd.DataFrame,
    ano: int,
    valor: Valor = "liquido",
    criterio_mes: CriterioMes = CRITERIO_MES_OFICIAL,
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
    criterio_mes: CriterioMes = CRITERIO_MES_OFICIAL,
) -> dict[str, Optional[float]]:
    """YTD de Vendas: acumulado de janeiro até o último mês com dado no ano
    selecionado, comparado ao MESMO intervalo do ano anterior.

    Nunca compara ano parcial atual com ano completo anterior.

    Retorno:
    - "atual": soma do ano selecionado até o mês limite
    - "anterior": soma do ano anterior no mesmo intervalo, ou None quando
      não existe nenhum dado do ano anterior ("sem comparativo disponível")
    - "variacao_pct": percentual de variação, ou None quando não calculável
    - "mes_limite": último mês com dado no ano selecionado, ou None
    """
    recorte_atual = _vendas_do_ano(df, ano, criterio_mes)
    col_mes = coluna_mes(criterio_mes)
    col_val = coluna_valor(valor)

    if recorte_atual.empty:
        mes_limite: Optional[int] = None
        total_atual = 0.0
    else:
        mes_limite = int(recorte_atual[col_mes].dt.month.max())
        total_atual = float(recorte_atual[col_val].sum())

    recorte_anterior = _vendas_do_ano(df, ano - 1, criterio_mes)
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

    Motivo: existem veículos com o mesmo nome comercial em grupos
    diferentes; agregar só pelo nome misturaria entidades distintas.

    Retorna, por par Grupo+Veículo (base Vendas): vendas bruto, vendas
    líquido, ticket médio, quantidade de PIs e % do total (calculado sobre
    o toggle de valor ativo).
    """
    base = df[mascara_vendas(df)]
    if base.empty:
        return pd.DataFrame(
            columns=[
                COL_GRUPO,
                COL_VEICULO,
                "vendas_bruto",
                "vendas_liquido",
                "ticket_medio",
                "qtd_pis",
                "pct_do_total",
            ]
        )

    agg = (
        base.groupby([COL_GRUPO, COL_VEICULO], as_index=False)
        .agg(
            vendas_bruto=(COL_VALOR_BRUTO, "sum"),
            vendas_liquido=(COL_VALOR_LIQUIDO, "sum"),
            qtd_pis=(COL_STATUS, "size"),
        )
    )
    col_ref = "vendas_liquido" if valor == "liquido" else "vendas_bruto"
    agg["ticket_medio"] = agg[col_ref] / agg["qtd_pis"]
    total = agg[col_ref].sum()
    agg["pct_do_total"] = (agg[col_ref] / total * 100.0) if total else 0.0
    return agg.sort_values(col_ref, ascending=False).reset_index(drop=True)


def veiculos_ativos(df: pd.DataFrame) -> int:
    """Veículos Ativos = pares Grupo+Veículo com >=1 PI na base Vendas."""
    base = df[mascara_vendas(df)]
    if base.empty:
        return 0
    return int(base[[COL_GRUPO, COL_VEICULO]].drop_duplicates().shape[0])


# ---------------------------------------------------------------------------
# Agregações de apresentação (consumidas pela interface)
# ---------------------------------------------------------------------------

#: Ordem oficial de exibição dos status (ciclo de vida comercial)
ORDEM_STATUS = [
    "A VEICULAR",
    "EM VEICULAÇÃO",
    "CHECKING",
    "AGUARD. DOC. VEÍCULO",
    "FATURADO",
    "DIRETO",
    "CANCELADO",
    "BONIFICADO",
]


def resumo_por_status(df: pd.DataFrame, valor: Valor = "liquido") -> pd.DataFrame:
    """Valor e contagem de PIs por status, na ordem oficial de exibição.

    Alimenta o gráfico de saúde da carteira da página Analítico Comercial.
    Status sem ocorrência no recorte não aparecem.
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


def agregado_por_dimensao(
    df: pd.DataFrame, coluna: str, valor: Valor = "liquido"
) -> pd.DataFrame:
    """Vendas agregadas por uma dimensão (Grupo, Agência, Cliente...).

    Alimenta os rankings Top 5 e completos. Base Vendas, ordenado do maior
    para o menor. Para veículo, usar SEMPRE agregado_por_grupo_veiculo
    (decisão 15), nunca esta função.
    """
    if coluna == COL_VEICULO:
        raise ValueError(
            "Agregação por veículo deve usar agregado_por_grupo_veiculo "
            "(sempre Grupo + Veículo, nunca veículo isolado — decisão 15)."
        )
    base = df[mascara_vendas(df)]
    if base.empty:
        return pd.DataFrame(columns=[coluna, "valor", "qtd_pis"])
    col = coluna_valor(valor)
    agg = (
        base.groupby(coluna)
        .agg(valor=(col, "sum"), qtd_pis=(coluna, "size"))
        .reset_index()
    )
    return agg.sort_values("valor", ascending=False).reset_index(drop=True)
