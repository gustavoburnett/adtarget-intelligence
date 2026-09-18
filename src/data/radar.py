"""Radar Executivo: mudanças determinísticas sobre a base Vendas da Release 1.0.

Risco e dados_desatualizados são reservados, sem detecção nesta sprint.
Meses ausentes não são convertidos em zero para comprovar recordes.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal, Mapping

import pandas as pd

from src.data import metrics
from src.data.cleaning import COL_GRUPO

TipoInsight = Literal["risco", "queda", "destaque", "crescimento"]
StatusRadar = Literal["ativo", "silencio", "dados_desatualizados", "dados_insuficientes"]
Periodo = tuple[dt.date, dt.date]


@dataclass(frozen=True)
class CTA:
    id: str
    texto: str
    destino: str | None = None


CTAS: Mapping[str, CTA] = {
    "crescimento": CTA("acompanhar_parceiro", "Acompanhe este parceiro."),
    "queda": CTA("verificar_parceiro", "Verifique este parceiro."),
    "destaque": CTA("acompanhar_tendencia", "Acompanhe esta tendência."),
}


@dataclass(frozen=True)
class Insight:
    id: str
    tipo: TipoInsight
    dimensao: str
    entidade: str
    periodo_atual: Periodo
    periodo_anterior: Periodo
    valor_atual: float
    valor_anterior: float
    variacao_pct: float
    magnitude: float
    referencia_comparacao: str
    cta: CTA


@dataclass(frozen=True)
class RadarState:
    status: StatusRadar
    insights: tuple[Insight, ...]
    avaliado_em: dt.datetime
    sincronizado_em: dt.datetime | None
    ano: int
    valor: metrics.Valor
    criterio_mes: metrics.CriterioMes
    regras_avaliadas: tuple[str, ...]
    regras_sem_comparacao: tuple[str, ...]


def _periodo(ano: int, mes: int) -> Periodo:
    fim = pd.Timestamp(year=ano, month=mes, day=1) + pd.offsets.MonthEnd(0)
    return dt.date(ano, 1, 1), fim.date()


def avaliar_radar(
    dados: pd.DataFrame,
    ano: int,
    *,
    agora: dt.datetime,
    valor: metrics.Valor = "liquido",
    criterio_mes: metrics.CriterioMes = metrics.CRITERIO_MES_OFICIAL,
    sincronizado_em: dt.datetime | None = None,
    ctas: Mapping[str, CTA] | None = None,
) -> RadarState:
    """Avalia o recorte dimensional completo, antes do filtro de ano.

    Seleciona o maior crescimento e a maior queda de Grupo, mais um
    recorde consolidado. Empates usam nome do Grupo. Ano futuro não tem
    comparação confiável. Silêncio exige ao menos uma regra avaliável;
    regras sem comparação permanecem explicitadas no resultado.

    Destaque: último mês COM dado no ano selecionado, anterior ao mês
    corrente, contra os 12 meses consecutivos anteriores COM dado.
    A idade da sincronização nunca decide a atualidade do conteúdo.
    """
    col_mes = metrics.coluna_mes(criterio_mes)
    col_valor = metrics.coluna_valor(valor)
    base = dados.loc[metrics.mascara_vendas(dados)]
    insights: list[Insight] = []
    avaliadas: list[str] = []
    sem_comparacao: list[str] = []
    ctas = CTAS if ctas is None else ctas
    limite = agora.month if ano == agora.year else 12
    atual = base.loc[
        (base[col_mes].dt.year == ano) & (base[col_mes].dt.month <= limite)
    ]
    anterior = base.loc[
        (base[col_mes].dt.year == ano - 1) & (base[col_mes].dt.month <= limite)
    ]
    somas_atual = atual.groupby(COL_GRUPO)[col_valor].sum()
    somas_anterior = anterior.groupby(COL_GRUPO)[col_valor].sum()
    candidatos: dict[str, list[Insight]] = {"queda": [], "crescimento": []}
    comparaveis = 0
    tem_periodo_atual = (
        (dados[col_mes].dt.year == ano) & (dados[col_mes].dt.month <= limite)
    ).any()
    if ano <= agora.year and tem_periodo_atual:
        for grupo in sorted(set(somas_atual.index) | set(somas_anterior.index)):
            v_ant = float(somas_anterior.get(grupo, 0.0))
            if not grupo or v_ant <= 0:
                continue
            comparaveis += 1
            v_atual = float(somas_atual.get(grupo, 0.0))
            variacao = (v_atual - v_ant) / v_ant * 100.0
            tipo = "crescimento" if variacao >= 15 else "queda" if variacao <= -15 else None
            if tipo is None:
                continue
            p_atual, p_ant = _periodo(ano, limite), _periodo(ano - 1, limite)
            candidatos[tipo].append(Insight(
                id=f"{tipo}:{grupo}:{ano}:{limite}", tipo=tipo,
                dimensao=COL_GRUPO, entidade=str(grupo),
                periodo_atual=p_atual, periodo_anterior=p_ant,
                valor_atual=v_atual, valor_anterior=v_ant,
                variacao_pct=variacao, magnitude=abs(variacao),
                referencia_comparacao=(
                    f"{p_atual[0]:%m/%Y}–{p_atual[1]:%m/%Y} vs "
                    f"{p_ant[0]:%m/%Y}–{p_ant[1]:%m/%Y} (mesmo período do ano anterior)"
                ), cta=ctas[tipo],
            ))
    for tipo in ("queda", "crescimento"):
        (avaliadas if comparaveis else sem_comparacao).append(tipo)
        if candidatos[tipo]:
            insights.append(sorted(candidatos[tipo], key=lambda i: (-i.magnitude, i.entidade))[0])

    # Reutiliza a evolução oficial; nunca infere zero para meses ausentes.
    series: dict[pd.Period, float] = {}
    for a in sorted(base[col_mes].dropna().dt.year.unique()):
        if int(a) > ano:
            continue
        for mes, total in metrics.evolucao_mensal(base, int(a), valor, criterio_mes).items():
            series[pd.Period(year=int(a), month=mes, freq="M")] = total
    mes_corrente = pd.Period(agora.date(), freq="M")
    completos = [p for p in series if p.year == ano and p < mes_corrente]
    destaque_avaliavel = False
    if completos:
        ultimo = max(completos)
        janela = [ultimo - n for n in range(12, 0, -1)]
        if all(p in series for p in janela):
            max_anterior = max(series[p] for p in janela)
            # Sem base positiva, não há magnitude percentual confiável.
            if max_anterior > 0:
                destaque_avaliavel = True
                total = series[ultimo]
                if total > max_anterior:
                    variacao = (total - max_anterior) / max_anterior * 100.0
                    insights.append(Insight(
                        id=f"destaque:{ultimo}", tipo="destaque",
                        dimensao="consolidado", entidade="Recorte selecionado",
                        periodo_atual=(ultimo.start_time.date(), ultimo.end_time.date()),
                        periodo_anterior=(janela[0].start_time.date(), janela[-1].end_time.date()),
                        valor_atual=total, valor_anterior=max_anterior,
                        variacao_pct=variacao, magnitude=variacao,
                        referencia_comparacao=(
                            f"{ultimo.month:02d}/{ultimo.year} vs máximo mensal de "
                            f"{janela[0].month:02d}/{janela[0].year}–"
                            f"{janela[-1].month:02d}/{janela[-1].year} (12 meses completos)"
                        ), cta=ctas["destaque"],
                    ))
    (avaliadas if destaque_avaliavel else sem_comparacao).append("destaque")
    prioridade = {"queda": 0, "destaque": 1, "crescimento": 2}
    ordenados = tuple(sorted(insights, key=lambda i: (prioridade[i.tipo], -i.magnitude, i.id))[:5])
    status = "ativo" if ordenados else "silencio" if avaliadas else "dados_insuficientes"
    return RadarState(status, ordenados, agora, sincronizado_em, ano, valor, criterio_mes,
                      tuple(avaliadas), tuple(sem_comparacao))
