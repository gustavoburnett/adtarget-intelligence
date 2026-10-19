"""Snapshot de apresentação mensal por grupo, sobre os contratos de Metas.

Não lê fontes nem altera engines. Metas, vigência, precedência e perímetro
vêm dos contratos existentes; os veículos apenas explicam as vendas, sem
receber metas individuais. Precisão financeira é mantida até a formatação.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

import pandas as pd

from src.data import metas as engine
from src.data import metrics
from src.data.cleaning import COL_GRUPO, COL_VEICULO
from src.data.metas_schema import normalizar_entidade

_ZERO = Decimal(0)
_CEM = Decimal(100)


@dataclass(frozen=True)
class ContribuicaoVeiculo:
    veiculo: str
    valor: Decimal
    percentual: Decimal | None


@dataclass(frozen=True)
class MesGrupo:
    mes: int
    estado_mes: engine.EstadoMes
    estado_meta: engine.EstadoMeta
    meta: Decimal | None
    vendido: Decimal
    fora_perimetro: Decimal
    registros: int
    atingimento_pct: Decimal | None
    desvio: Decimal | None
    veiculos: tuple[ContribuicaoVeiculo, ...]


@dataclass(frozen=True)
class GrupoMensal:
    grupo: str
    ano: int
    resultado: engine.ResultadoMetas
    pulso: engine.ResultadoPulso
    parceiro: engine.ParceiroMetas | None
    tem_metas: bool
    meses: tuple[MesGrupo, ...]
    contribuicoes: tuple[ContribuicaoVeiculo, ...]
    fora_perimetro_anual: Decimal

    @property
    def realizado_ytd(self) -> Decimal:
        if self.tem_metas:
            return self.resultado.realizado_ytd
        return sum(
            (mes.vendido for mes in self.meses if mes.estado_mes == "encerrado"),
            _ZERO,
        )

    @property
    def total_vendido_ano(self) -> Decimal:
        if self.tem_metas:
            return self.pulso.total_vendido_ano
        return sum((mes.vendido for mes in self.meses), _ZERO)

    @property
    def carteira_futura(self) -> Decimal:
        if self.tem_metas:
            return self.pulso.carteira_futura
        return sum(
            (mes.vendido for mes in self.meses if mes.estado_mes != "encerrado"),
            _ZERO,
        )

    @property
    def meta_anual(self) -> Decimal | None:
        return self.resultado.meta_anual if self.tem_metas else None

    @property
    def gap_comercial(self) -> Decimal | None:
        # Meta anual sem denominador positivo não recebe gap comercial novo.
        return (
            self.pulso.gap_comercial
            if self.meta_anual is not None and self.meta_anual > 0 else None
        )


def _vendas_canonicas(df: pd.DataFrame) -> pd.DataFrame:
    copia = df.copy(deep=True)
    for coluna in (COL_GRUPO, COL_VEICULO):
        copia[coluna] = copia[coluna].map(normalizar_entidade)
    return copia


def _vendas_do_ano(df: pd.DataFrame, ano: int) -> pd.DataFrame:
    coluna = metrics.coluna_mes("veiculacao")
    return df.loc[metrics.mascara_vendas(df) & (df[coluna].dt.year == ano)]


def grupos_disponiveis(
    df: pd.DataFrame,
    metas: pd.DataFrame,
    ano: int,
    *,
    data_referencia: engine.Referencia = None,
) -> tuple[str, ...]:
    """União de grupos com meta vigente ou vendas elegíveis no ano.

    Inatividade e ausência de vendas não apagam grupos com metas. Grupos
    apenas cancelados/bonificados ou de outro ano não ampliam o seletor.
    """
    engine.meses_encerrados(ano, data_referencia=data_referencia)
    vigente = engine.vigencia(metas, data_referencia=data_referencia)
    com_metas = vigente.loc[vigente["ANO"] == ano, "GRUPO"]
    com_vendas = _vendas_do_ano(_vendas_canonicas(df), ano)[COL_GRUPO]
    return tuple(sorted((set(com_metas) | set(com_vendas)) - {""}))


def _mascara_perimetro(
    vendas: pd.DataFrame, mes: engine.MesMetas
) -> pd.Series:
    """Aplica as entidades já resolvidas pela engine, sem refazer precedência."""
    dentro = pd.Series(False, index=vendas.index)
    for entidade in mes.perimetro:
        mascara = vendas[COL_GRUPO] == entidade.grupo
        if entidade.nivel_meta == "VEICULO":
            mascara &= vendas[COL_VEICULO] == entidade.veiculo
        dentro |= mascara
    return dentro


def _contribuicoes(
    valores: dict[str, Decimal], total: Decimal
) -> tuple[ContribuicaoVeiculo, ...]:
    return tuple(
        ContribuicaoVeiculo(
            veiculo=veiculo,
            valor=valor,
            percentual=valor / total * _CEM if total > 0 else None,
        )
        for veiculo, valor in sorted(valores.items(), key=lambda item: (-item[1], item[0]))
    )


def preparar_grupo(
    df: pd.DataFrame,
    metas: pd.DataFrame,
    ano: int,
    grupo: str,
    *,
    data_referencia: engine.Referencia = None,
) -> GrupoMensal:
    """Prepara doze meses líquidos/veiculação sem rateio de metas.

    Com metas no ano, vendas oficiais respeitam o perímetro de cada mês e
    as demais ficam explícitas em ``fora_perimetro``. Sem qualquer meta no
    ano, vendas integrais são consultáveis, mas não há comparativos fictícios.
    Mês sem registros mantém seu zero financeiro e omite atingimento/desvio;
    isso não muda os totais nem o ritmo YTD dos contratos existentes.
    """
    grupo = normalizar_entidade(grupo)
    if not grupo:
        raise ValueError("Selecione um grupo comercial válido.")
    vigente = engine.vigencia(metas, data_referencia=data_referencia)
    plano = vigente.loc[vigente["GRUPO"] == grupo].copy(deep=True)
    resultado = engine.avaliar_metas(
        df, plano, ano, data_referencia=data_referencia
    )
    pulso = engine.avaliar_pulso(
        df, plano, ano, data_referencia=resultado.data_referencia
    )
    parceiros = engine.avaliar_parceiros(
        df, plano, ano, data_referencia=resultado.data_referencia
    )
    parceiro = next((p for p in parceiros if p.grupo == grupo), None)
    tem_metas = not plano.loc[plano["ANO"] == ano].empty
    vendas = _vendas_do_ano(_vendas_canonicas(df), ano)
    vendas = vendas.loc[vendas[COL_GRUPO] == grupo]
    coluna_mes = metrics.coluna_mes("veiculacao")
    meses: list[MesGrupo] = []
    valores_anuais: dict[str, Decimal] = defaultdict(lambda: _ZERO)
    for base, mes_pulso in zip(resultado.meses, pulso.meses, strict=True):
        todas = vendas.loc[vendas[coluna_mes].dt.month == base.mes]
        dentro = (
            _mascara_perimetro(todas, base) if tem_metas
            else pd.Series(True, index=todas.index)
        )
        oficiais = todas.loc[dentro]
        fora = todas.loc[~dentro]
        vendido = (
            mes_pulso.vendido if tem_metas
            else Decimal(str(metrics.vendas(oficiais, "liquido")))
        )
        valores_mes: dict[str, Decimal] = {}
        for veiculo, registros in oficiais.groupby(COL_VEICULO, dropna=False):
            valor = Decimal(str(metrics.vendas(registros, "liquido")))
            valores_mes[veiculo] = valor
            valores_anuais[veiculo] += valor
        meta = base.meta if base.estado_meta in {"ativa", "zero_ativa"} else None
        comparavel = len(oficiais) > 0 and meta is not None
        meses.append(MesGrupo(
            mes=base.mes,
            estado_mes=base.estado_mes,
            estado_meta=base.estado_meta,
            meta=meta,
            vendido=vendido,
            fora_perimetro=Decimal(str(metrics.vendas(fora, "liquido"))),
            registros=len(oficiais),
            atingimento_pct=(
                vendido / meta * _CEM if comparavel and meta > 0 else None
            ),
            desvio=engine.diferenca_monetaria(vendido, meta) if comparavel else None,
            veiculos=_contribuicoes(valores_mes, vendido),
        ))
    total = (
        pulso.total_vendido_ano if tem_metas
        else sum((mes.vendido for mes in meses), _ZERO)
    )
    return GrupoMensal(
        grupo=grupo,
        ano=ano,
        resultado=resultado,
        pulso=pulso,
        parceiro=parceiro,
        tem_metas=tem_metas,
        meses=tuple(meses),
        contribuicoes=_contribuicoes(valores_anuais, total),
        fora_perimetro_anual=sum((mes.fora_perimetro for mes in meses), _ZERO),
    )


def contribuicoes_grupo(
    grupo: GrupoMensal, mes: int | None = None
) -> tuple[ContribuicaoVeiculo, ...]:
    """Consulta do ano ou mês, sempre sem metas individuais inventadas."""
    if mes is None:
        return grupo.contribuicoes
    if isinstance(mes, bool) or not isinstance(mes, int) or not 1 <= mes <= 12:
        raise ValueError("O mês selecionado deve estar entre 1 e 12.")
    return grupo.meses[mes - 1].veiculos
