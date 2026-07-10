"""Alertas de qualidade — detectam, NUNCA corrigem (documentos 02 e 03).

Implementa os 5 alertas oficiais do documento 02, executados sempre depois
da limpeza (cleaning.limpar_dataframe) e antes/junto do cálculo de métricas.
Cada verificação retorna uma estrutura com contagem, valores envolvidos e as
linhas afetadas, para alimentar o bloco de Alertas de Qualidade da página
Analítico Faturamento.

Nenhuma função deste módulo altera o DataFrame recebido.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.data.cleaning import (
    COL_GRUPO,
    COL_NOTA_FISCAL,
    COL_STATUS,
    COL_VALOR_BRUTO,
    COL_VALOR_LIQUIDO,
    COL_VEICULO,
    STATUS_VALIDOS,
)

#: Textos literais que caracterizam ausência de Nota Fiscal (documento 01)
_TEXTOS_SEM_NF = frozenset({"SEM NF", "SEM NOTA"})


@dataclass
class AlertaQualidade:
    """Resultado de uma verificação de qualidade.

    - codigo: identificador estável do alerta (1 a 5, documento 02)
    - titulo: descrição curta para exibição
    - quantidade: número de ocorrências encontradas
    - detalhes: informações adicionais (ex: valores somados)
    - linhas: DataFrame com as linhas afetadas (para auditoria)
    """

    codigo: str
    titulo: str
    quantidade: int
    detalhes: dict[str, Any] = field(default_factory=dict)
    linhas: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def possui_ocorrencias(self) -> bool:
        return self.quantidade > 0


def _nf_ausente(valor: Any) -> bool:
    """NF ausente = célula em branco OU texto literal "SEM NF"/"SEM NOTA"."""
    if valor is None:
        return True
    texto = str(valor).strip().upper()
    return texto == "" or texto in _TEXTOS_SEM_NF


def faturado_sem_nota_fiscal(df: pd.DataFrame) -> AlertaQualidade:
    """Alerta 1: linhas com status FATURADO sem Nota Fiscal preenchida.

    Vendas DIRETO nunca têm NF por desenho (documento 01) e por isso o
    alerta é restrito ao status FATURADO.
    """
    mascara = (df[COL_STATUS] == "FATURADO") & df[COL_NOTA_FISCAL].map(_nf_ausente)
    afetadas = df[mascara]
    return AlertaQualidade(
        codigo="1",
        titulo="Linhas FATURADO sem Nota Fiscal",
        quantidade=len(afetadas),
        linhas=afetadas,
    )


def veiculo_com_multiplos_grupos(df: pd.DataFrame) -> AlertaQualidade:
    """Alerta 3: veículo associado a mais de um Grupo na base carregada.

    Verificação genérica e permanente (decisão 18). Não corrige nada:
    apenas sinaliza para correção manual na planilha de origem.
    """
    base = df[(df[COL_VEICULO] != "") & (df[COL_GRUPO] != "")]
    grupos_por_veiculo = base.groupby(COL_VEICULO)[COL_GRUPO].nunique()
    inconsistentes = grupos_por_veiculo[grupos_por_veiculo > 1]
    mapa = {
        veiculo: sorted(base.loc[base[COL_VEICULO] == veiculo, COL_GRUPO].unique())
        for veiculo in inconsistentes.index
    }
    afetadas = df[df[COL_VEICULO].isin(inconsistentes.index)]
    return AlertaQualidade(
        codigo="3",
        titulo="Veículo associado a mais de um Grupo",
        quantidade=len(inconsistentes),
        detalhes={"veiculos": mapa},
        linhas=afetadas,
    )


def status_desconhecido(df: pd.DataFrame) -> AlertaQualidade:
    """Alerta 4: status fora do vocabulário controlado (8 status oficiais).

    Como o campo STATUS é obrigatório na planilha, um valor em branco
    também é sinalizado aqui (exibido como "(VAZIO)"), funcionando de
    guarda-corpo caso a regra de preenchimento seja violada na origem.
    """
    mascara = ~df[COL_STATUS].isin(STATUS_VALIDOS)
    afetadas = df[mascara]
    valores = sorted(
        ("(VAZIO)" if v == "" else v) for v in afetadas[COL_STATUS].unique()
    )
    return AlertaQualidade(
        codigo="4",
        titulo="Status não reconhecido pelo vocabulário controlado",
        quantidade=len(afetadas),
        detalhes={"valores": valores},
        linhas=afetadas,
    )


def cancelado_bonificado_com_valor(df: pd.DataFrame) -> AlertaQualidade:
    """Alerta 5: PI CANCELADO ou BONIFICADO com valor diferente de zero.

    O comportamento esperado é valor zerado nesses status; qualquer exceção
    é sinalizada individualmente para verificação manual (decisão 24 —
    motivada pelo caso real de 1 linha CANCELADO de R$ 17.172 em 2024).
    """
    mascara = df[COL_STATUS].isin(["CANCELADO", "BONIFICADO"]) & (
        (df[COL_VALOR_BRUTO] != 0) | (df[COL_VALOR_LIQUIDO] != 0)
    )
    afetadas = df[mascara]
    return AlertaQualidade(
        codigo="5",
        titulo="PI cancelado/bonificado com valor diferente de zero",
        quantidade=len(afetadas),
        detalhes={
            "valor_bruto": float(afetadas[COL_VALOR_BRUTO].sum()),
            "valor_liquido": float(afetadas[COL_VALOR_LIQUIDO].sum()),
        },
        linhas=afetadas,
    )


def executar_todas(df: pd.DataFrame) -> list[AlertaQualidade]:
    """Executa as 4 verificações vigentes.

    O antigo alerta 2 (linhas sem status) foi removido em 2026-07-09:
    o campo STATUS passou a ser obrigatório na planilha. Os códigos dos
    demais alertas foram preservados para rastreabilidade com a
    documentação original.
    """
    return [
        faturado_sem_nota_fiscal(df),
        veiculo_com_multiplos_grupos(df),
        status_desconhecido(df),
        cancelado_bonificado_com_valor(df),
    ]
