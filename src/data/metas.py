"""Engine pura de Metas e Resultados, sem interface ou escrita na fonte.

Metas usam centavos inteiros. O realizado conserva a precisão retornada por
``metrics.vendas``: não há arredondamento por PI nem por mês. A apresentação
deve arredondar somente o resultado final, nunca somar rótulos formatados.

O perímetro é mensal, após vigência e precedência. O comparativo anterior
reutiliza esse mesmo perímetro do ano selecionado, inclusive nos meses que
ainda não encerraram, para compor a série anterior completa.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from numbers import Integral
from typing import Literal

import pandas as pd

from src.data import metrics
from src.data.cleaning import COL_GRUPO, COL_VEICULO
from src.data.metas_schema import (
    COL_VALOR_META_CENTAVOS,
    data_local,
    normalizar_entidade,
    validar_metas,
)

Referencia = dt.date | dt.datetime | None
EstadoMes = Literal["encerrado", "em_andamento", "futuro"]
EstadoMeta = Literal["ausente", "inativa", "zero_ativa", "ativa"]
EstadoResultado = Literal[
    "ativo", "sem_metas", "aguardando_mes_encerrado", "sem_meta_periodo", "ano_encerrado"
]
_ZERO = Decimal(0)
_CEM = Decimal(100)
_SLOT = ["NIVEL_META", "GRUPO", "VEICULO", "ANO", "MES"]


@dataclass(frozen=True, order=True)
class EntidadeMeta:
    """Alvo canônico; VEICULO é sempre acompanhado de seu grupo."""

    nivel_meta: Literal["GRUPO", "VEICULO"]
    grupo: str
    veiculo: str = ""


@dataclass(frozen=True)
class MesMetas:
    """Indicadores de um mês e acumulados até ele; dinheiro em reais salvo *_centavos.

    ``realizado`` e seu acumulado são None em mês aberto/futuro. Ausência de
    vendas anteriores é None, não um zero que invente uma base de YoY.
    ``realizado_anterior_acumulado`` carrega a soma disponível entre meses
    sem vendas anteriores e permanece None até a primeira base disponível.
    """

    mes: int
    estado_mes: EstadoMes
    estado_meta: EstadoMeta
    perimetro: tuple[EntidadeMeta, ...]
    meta_centavos: int
    realizado: Decimal | None
    realizado_anterior: Decimal | None
    meta_acumulada_centavos: int
    realizado_acumulado: Decimal | None
    realizado_anterior_acumulado: Decimal | None
    atingimento_pct: Decimal | None
    saldo: Decimal | None
    yoy_pct: Decimal | None
    atingimento_acumulado_pct: Decimal | None
    saldo_acumulado: Decimal | None
    yoy_acumulado_pct: Decimal | None

    @property
    def meta(self) -> Decimal:
        return Decimal(self.meta_centavos) / _CEM

    @property
    def meta_acumulada(self) -> Decimal:
        return Decimal(self.meta_acumulada_centavos) / _CEM


@dataclass(frozen=True)
class ResultadoMetas:
    """Contrato compartilhado pelas duas visões de metas, sem dados de UI.

    Campos *_pct contêm pontos percentuais (100 significa 100%). Saldo YTD
    positivo é superávit; gap anual positivo é o valor que ainda falta.
    Necessidade segue literalmente gap/meses restantes. Cobertura é None
    quando não há gap positivo; esses casos não têm divisão interpretável.
    """

    ano: int
    data_referencia: dt.date
    meses_encerrados: int
    meses_restantes: int
    estado: EstadoResultado
    meses: tuple[MesMetas, ...]
    meta_anual_centavos: int
    meta_ytd_centavos: int
    plano_futuro_centavos: int
    realizado_ytd: Decimal
    realizado_anterior_ytd: Decimal | None
    atingimento_ytd_pct: Decimal | None
    saldo_ytd: Decimal
    meta_anual_conquistada_pct: Decimal | None
    gap_anual: Decimal
    necessidade_media: Decimal | None
    cobertura_plano_pct: Decimal | None
    forecast: Decimal | None
    projetado_atingimento_pct: Decimal | None
    yoy_pct: Decimal | None

    @property
    def meta_anual(self) -> Decimal:
        return Decimal(self.meta_anual_centavos) / _CEM

    @property
    def meta_ytd(self) -> Decimal:
        return Decimal(self.meta_ytd_centavos) / _CEM

    @property
    def plano_futuro(self) -> Decimal | None:
        if not self.meses_restantes:
            return None
        return Decimal(self.plano_futuro_centavos) / _CEM


def meses_encerrados(ano: int, *, data_referencia: Referencia = None) -> int:
    """Meses-calendário encerrados em São Paulo, sem depender de vendas.

    O último dia inteiro deve ter passado: inclusive em 31/12, dezembro do
    ano corrente ainda está aberto. Anos anteriores têm 12, futuros zero.
    Este helper não é consumido pelo YTD da Performance nem pelo Radar.
    """
    if isinstance(ano, bool) or not isinstance(ano, Integral) or not 1 <= ano <= 9999:
        raise ValueError("O ano selecionado deve ser um inteiro válido.")
    hoje = data_local(data_referencia)
    if ano < hoje.year:
        return 12
    if ano > hoje.year:
        return 0
    return hoje.month - 1


def vigencia(
    metas: pd.DataFrame, *, data_referencia: Referencia = None
) -> pd.DataFrame:
    """Maior revisão por slot, antes da precedência, preservando linhas de origem.

    Mantém simultaneamente GRUPO e VEICULO vigentes para permitir o alerta
    de coexistência. Não altera o dataframe recebido, inclusive se ele já
    estiver normalizado pelo schema.
    """
    normalizadas = validar_metas(metas, data_referencia=data_referencia)
    return (
        normalizadas.sort_values(_SLOT + ["REVISAO"], kind="stable")
        .drop_duplicates(_SLOT, keep="last")
        .sort_values(_SLOT, kind="stable")
        .reset_index(drop=True)
        .copy()
    )


def _selecionar_niveis(metas_mes: pd.DataFrame) -> pd.DataFrame:
    """GRUPO domina o grupo-mês, inclusive inativo; não faz rateio."""
    grupos = metas_mes.loc[metas_mes["NIVEL_META"] == "GRUPO", "GRUPO"]
    return metas_mes.loc[
        (metas_mes["NIVEL_META"] == "GRUPO") | ~metas_mes["GRUPO"].isin(grupos)
    ]


def _estado_meta(selecionadas: pd.DataFrame) -> EstadoMeta:
    if selecionadas.empty:
        return "ausente"
    ativas = selecionadas[selecionadas["ATIVO"] == "SIM"]
    if ativas.empty:
        return "inativa"
    if sum(int(valor) for valor in ativas[COL_VALOR_META_CENTAVOS]) == 0:
        return "zero_ativa"
    return "ativa"


def _perimetro(selecionadas: pd.DataFrame) -> tuple[EntidadeMeta, ...]:
    return tuple(sorted(
        EntidadeMeta(linha.NIVEL_META, linha.GRUPO, linha.VEICULO)
        for linha in selecionadas[selecionadas["ATIVO"] == "SIM"].itertuples()
    ))


def _vendas_do_mes(
    vendas: pd.DataFrame, ano: int, mes: int, perimetro: tuple[EntidadeMeta, ...]
) -> pd.DataFrame:
    col_mes = metrics.coluna_mes("veiculacao")
    dentro = pd.Series(False, index=vendas.index)
    for entidade in perimetro:
        mascara = vendas[COL_GRUPO] == entidade.grupo
        if entidade.nivel_meta == "VEICULO":
            mascara &= vendas[COL_VEICULO] == entidade.veiculo
        dentro |= mascara
    return vendas.loc[
        dentro & (vendas[col_mes].dt.year == ano) & (vendas[col_mes].dt.month == mes)
    ]


def _percentual(numerador: Decimal, denominador: Decimal) -> Decimal | None:
    return numerador / denominador * _CEM if denominador > 0 else None


def _yoy(atual: Decimal, anterior: Decimal | None) -> Decimal | None:
    return _percentual(atual - anterior, anterior) if anterior is not None else None


def avaliar_metas(
    vendas_df: pd.DataFrame,
    metas_df: pd.DataFrame,
    ano: int,
    *,
    data_referencia: Referencia = None,
) -> ResultadoMetas:
    """Calcula o ano com vendas já limpas e o log METAS (bruto ou normalizado).

    Não recebe filtros Grupo, Líquido/Bruto ou Ganho/Veiculação: o recorte
    é sempre consolidado, líquido e veiculação. Alias é aplicado apenas
    às cópias desta camada. Falhas de schema são propagadas explicitamente.
    """
    hoje = data_local(data_referencia)
    encerrados = meses_encerrados(ano, data_referencia=hoje)
    restantes = 12 - encerrados
    metas = vigencia(metas_df, data_referencia=hoje)
    metas_ano = metas.loc[metas["ANO"] == ano]
    vendas = vendas_df.copy(deep=True)
    for coluna in (COL_GRUPO, COL_VEICULO):
        vendas[coluna] = vendas[coluna].map(normalizar_entidade)

    meses: list[MesMetas] = []
    meta_acumulada_centavos = 0
    realizado_acumulado = _ZERO
    anterior_acumulado = _ZERO
    tem_anterior = False
    for mes in range(1, 13):
        selecionadas = _selecionar_niveis(metas_ano[metas_ano["MES"] == mes])
        perimetro = _perimetro(selecionadas)
        meta_centavos = sum(
            int(valor)
            for valor in selecionadas.loc[
                selecionadas["ATIVO"] == "SIM", COL_VALOR_META_CENTAVOS
            ]
        )
        meta_acumulada_centavos += meta_centavos
        estado_mes: EstadoMes = (
            "encerrado" if mes <= encerrados
            else "em_andamento" if ano == hoje.year and mes == hoje.month
            else "futuro"
        )
        anterior_df = _vendas_do_mes(vendas, ano - 1, mes, perimetro)
        anterior = (
            Decimal(str(metrics.vendas(anterior_df, "liquido")))
            if metrics.mascara_vendas(anterior_df).any() else None
        )
        if anterior is not None:
            anterior_acumulado += anterior
            tem_anterior = True
        anterior_soma = anterior_acumulado if tem_anterior else None
        realizado = None
        atual_soma = None
        if estado_mes == "encerrado":
            atual_df = _vendas_do_mes(vendas, ano, mes, perimetro)
            realizado = Decimal(str(metrics.vendas(atual_df, "liquido")))
            realizado_acumulado += realizado
            atual_soma = realizado_acumulado
        meta_reais = Decimal(meta_centavos) / _CEM
        meta_soma_reais = Decimal(meta_acumulada_centavos) / _CEM
        meses.append(MesMetas(
            mes=mes,
            estado_mes=estado_mes,
            estado_meta=_estado_meta(selecionadas),
            perimetro=perimetro,
            meta_centavos=meta_centavos,
            realizado=realizado,
            realizado_anterior=anterior,
            meta_acumulada_centavos=meta_acumulada_centavos,
            realizado_acumulado=atual_soma,
            realizado_anterior_acumulado=anterior_soma,
            atingimento_pct=_percentual(realizado, meta_reais) if realizado is not None else None,
            saldo=realizado - meta_reais if realizado is not None else None,
            yoy_pct=_yoy(realizado, anterior) if realizado is not None else None,
            atingimento_acumulado_pct=(
                _percentual(atual_soma, meta_soma_reais) if atual_soma is not None else None
            ),
            saldo_acumulado=atual_soma - meta_soma_reais if atual_soma is not None else None,
            yoy_acumulado_pct=_yoy(atual_soma, anterior_soma) if atual_soma is not None else None,
        ))

    meta_anual_centavos = sum(m.meta_centavos for m in meses)
    meta_ytd_centavos = sum(m.meta_centavos for m in meses[:encerrados])
    futuro_centavos = sum(m.meta_centavos for m in meses[encerrados:])
    meta_ytd = Decimal(meta_ytd_centavos) / _CEM
    meta_anual = Decimal(meta_anual_centavos) / _CEM
    anterior_ytd = meses[encerrados - 1].realizado_anterior_acumulado if encerrados else None
    gap = meta_anual - realizado_acumulado
    forecast = realizado_acumulado / Decimal(encerrados) * 12 if 2 <= encerrados < 12 else None
    percentuais_disponiveis = encerrados > 0 and meta_ytd_centavos > 0
    estado: EstadoResultado = (
        "sem_metas" if metas_ano.empty
        else "aguardando_mes_encerrado" if not encerrados
        else "sem_meta_periodo" if meta_ytd_centavos == 0
        else "ano_encerrado" if not restantes
        else "ativo"
    )
    return ResultadoMetas(
        ano=int(ano),
        data_referencia=hoje,
        meses_encerrados=encerrados,
        meses_restantes=restantes,
        estado=estado,
        meses=tuple(meses),
        meta_anual_centavos=meta_anual_centavos,
        meta_ytd_centavos=meta_ytd_centavos,
        plano_futuro_centavos=futuro_centavos,
        realizado_ytd=realizado_acumulado,
        realizado_anterior_ytd=anterior_ytd,
        atingimento_ytd_pct=(
            _percentual(realizado_acumulado, meta_ytd) if percentuais_disponiveis else None
        ),
        saldo_ytd=realizado_acumulado - meta_ytd,
        meta_anual_conquistada_pct=(
            _percentual(realizado_acumulado, meta_anual) if percentuais_disponiveis else None
        ),
        gap_anual=gap,
        necessidade_media=gap / Decimal(restantes) if restantes else None,
        cobertura_plano_pct=(
            _percentual(Decimal(futuro_centavos) / _CEM, gap)
            if restantes and percentuais_disponiveis else None
        ),
        forecast=forecast,
        projetado_atingimento_pct=(
            _percentual(forecast, meta_anual)
            if forecast is not None and percentuais_disponiveis else None
        ),
        yoy_pct=_yoy(realizado_acumulado, anterior_ytd) if encerrados else None,
    )


TipoValorPulso = Literal["realizado", "ja_vendido"]
EstadoPulso = Literal["ativo", "sem_metas", "sem_meta_anual", "ano_encerrado"]
StatusParceiroPulso = Literal[
    "sem_meta_anual", "meta_superada", "meta_atingida", "abaixo_da_meta"
]


@dataclass(frozen=True)
class MesPulso:
    """Venda oficial no perímetro mensal, inclusive em mês aberto/futuro.

    ``tipo_valor`` distingue o realizado de meses encerrados do valor já
    vendido para veiculação em meses que ainda não encerraram. Nenhuma
    venda futura é renomeada como realizado.
    """

    mes: int
    estado_mes: EstadoMes
    meta_centavos: int
    vendido: Decimal
    tipo_valor: TipoValorPulso

    @property
    def meta(self) -> Decimal:
        return Decimal(self.meta_centavos) / _CEM


@dataclass(frozen=True)
class ParceiroPulso:
    """Consolidado do grupo após vigência e precedência de cada mês.

    Metas de veículos, quando aplicáveis, são somadas no seu próprio grupo,
    sem ratear metas de grupo. ``status`` informa a conquista comercial da
    meta anual; não indica se o parceiro está ativo no mês atual.
    """

    grupo: str
    meta_anual_centavos: int
    realizado_meses_encerrados: Decimal
    ja_vendido_meses_restantes: Decimal
    total_vendido_ano: Decimal
    percentual_meta_ja_vendida: Decimal | None
    gap_comercial: Decimal
    status: StatusParceiroPulso

    @property
    def meta_anual(self) -> Decimal:
        return Decimal(self.meta_anual_centavos) / _CEM


@dataclass(frozen=True)
class ResultadoPulso:
    """Snapshot comercial do ano, separado do YTD oficial e do forecast.

    ``total_vendido_ano`` soma realizado de meses encerrados e carteira
    futura existente na fonte. Não filtra DATA DE CRIAÇÃO nem estima vendas.
    Todos os valores de venda vêm de ``metrics.vendas(..., 'liquido')`` no
    mês de veiculação e no perímetro ativo daquele mês. Campos percentuais
    contêm pontos percentuais (100 significa 100%).
    """

    ano: int
    data_referencia: dt.date
    meses_encerrados: int
    meses_restantes: int
    estado: EstadoPulso
    meta_anual_centavos: int
    meta_restante_centavos: int
    realizado_meses_encerrados: Decimal
    carteira_futura: Decimal
    total_vendido_ano: Decimal
    percentual_meta_ja_vendida: Decimal | None
    gap_comercial: Decimal
    necessidade_media_comercial: Decimal | None
    cobertura_futura_ja_vendida_pct: Decimal | None
    meses: tuple[MesPulso, ...]
    parceiros: tuple[ParceiroPulso, ...]

    @property
    def meta_anual(self) -> Decimal:
        return Decimal(self.meta_anual_centavos) / _CEM

    @property
    def meta_restante(self) -> Decimal:
        return Decimal(self.meta_restante_centavos) / _CEM


def avaliar_pulso(
    vendas_df: pd.DataFrame,
    metas_df: pd.DataFrame,
    ano: int,
    *,
    data_referencia: Referencia = None,
) -> ResultadoPulso:
    """Aplica P(m) a todas as vendas já existentes para o ano selecionado.

    O fechado é obtido integralmente de ``avaliar_metas``. Vendas do mês em
    andamento e dos meses futuros são avaliadas com os mesmos helpers e
    regras oficiais, em cópias dos dados. Não há I/O nem alteração da fonte.

    Percentuais comerciais dependem da sua própria meta positiva, inclusive
    quando ainda não há mês encerrado. Sem meses restantes, necessidade e
    cobertura futura são None; a carteira futura é zero.
    """
    fechado = avaliar_metas(
        vendas_df, metas_df, ano, data_referencia=data_referencia
    )
    metas = vigencia(metas_df, data_referencia=fechado.data_referencia)
    metas_ano = metas.loc[metas["ANO"] == fechado.ano]
    vendas = vendas_df.copy(deep=True)
    for coluna in (COL_GRUPO, COL_VEICULO):
        vendas[coluna] = vendas[coluna].map(normalizar_entidade)

    grupos = sorted(set(metas_ano["GRUPO"]))
    metas_por_grupo = dict.fromkeys(grupos, 0)
    fechado_por_grupo = dict.fromkeys(grupos, _ZERO)
    futuro_por_grupo = dict.fromkeys(grupos, _ZERO)
    meses: list[MesPulso] = []
    carteira_futura = _ZERO
    for mes_fechado in fechado.meses:
        vendas_mes = _vendas_do_mes(
            vendas, fechado.ano, mes_fechado.mes, mes_fechado.perimetro
        )
        encerrado = mes_fechado.estado_mes == "encerrado"
        if encerrado:
            # Reutilizar o valor oficial preserva exatamente o YTD validado.
            vendido = mes_fechado.realizado
        else:
            vendido = Decimal(str(metrics.vendas(vendas_mes, "liquido")))
            carteira_futura += vendido
        meses.append(MesPulso(
            mes=mes_fechado.mes,
            estado_mes=mes_fechado.estado_mes,
            meta_centavos=mes_fechado.meta_centavos,
            vendido=vendido,
            tipo_valor="realizado" if encerrado else "ja_vendido",
        ))

        selecionadas = _selecionar_niveis(
            metas_ano[metas_ano["MES"] == mes_fechado.mes]
        )
        ativas = selecionadas[selecionadas["ATIVO"] == "SIM"]
        for grupo in grupos:
            metas_por_grupo[grupo] += sum(
                int(valor) for valor in ativas.loc[
                    ativas["GRUPO"] == grupo, COL_VALOR_META_CENTAVOS
                ]
            )
            vendido_grupo = Decimal(str(metrics.vendas(
                vendas_mes[vendas_mes[COL_GRUPO] == grupo], "liquido"
            )))
            if encerrado:
                fechado_por_grupo[grupo] += vendido_grupo
            else:
                futuro_por_grupo[grupo] += vendido_grupo

    parceiros: list[ParceiroPulso] = []
    for grupo in grupos:
        meta_centavos = metas_por_grupo[grupo]
        meta_anual = Decimal(meta_centavos) / _CEM
        total = fechado_por_grupo[grupo] + futuro_por_grupo[grupo]
        gap = meta_anual - total
        status: StatusParceiroPulso = (
            "sem_meta_anual" if meta_centavos == 0
            else "meta_superada" if gap < 0
            else "meta_atingida" if gap == 0
            else "abaixo_da_meta"
        )
        parceiros.append(ParceiroPulso(
            grupo=grupo,
            meta_anual_centavos=meta_centavos,
            realizado_meses_encerrados=fechado_por_grupo[grupo],
            ja_vendido_meses_restantes=futuro_por_grupo[grupo],
            total_vendido_ano=total,
            percentual_meta_ja_vendida=_percentual(total, meta_anual),
            gap_comercial=gap,
            status=status,
        ))

    total_vendido = fechado.realizado_ytd + carteira_futura
    gap_comercial = fechado.meta_anual - total_vendido
    meta_restante = Decimal(fechado.plano_futuro_centavos) / _CEM
    estado: EstadoPulso = (
        "sem_metas" if metas_ano.empty
        else "sem_meta_anual" if fechado.meta_anual_centavos == 0
        else "ano_encerrado" if not fechado.meses_restantes
        else "ativo"
    )
    return ResultadoPulso(
        ano=fechado.ano,
        data_referencia=fechado.data_referencia,
        meses_encerrados=fechado.meses_encerrados,
        meses_restantes=fechado.meses_restantes,
        estado=estado,
        meta_anual_centavos=fechado.meta_anual_centavos,
        meta_restante_centavos=fechado.plano_futuro_centavos,
        realizado_meses_encerrados=fechado.realizado_ytd,
        carteira_futura=carteira_futura,
        total_vendido_ano=total_vendido,
        percentual_meta_ja_vendida=_percentual(total_vendido, fechado.meta_anual),
        gap_comercial=gap_comercial,
        necessidade_media_comercial=(
            gap_comercial / Decimal(fechado.meses_restantes)
            if fechado.meses_restantes else None
        ),
        cobertura_futura_ja_vendida_pct=(
            _percentual(carteira_futura, meta_restante)
            if fechado.meses_restantes else None
        ),
        meses=tuple(meses),
        parceiros=tuple(parceiros),
    )


StatusParceiroMetas = Literal[
    "acima_da_meta", "proximo_da_meta", "abaixo_da_meta",
    "sem_meta_periodo", "aguardando_mes_encerrado",
]


@dataclass(frozen=True)
class ParceiroMetas:
    """Duas réguas separadas: ritmo fechado e compromisso comercial anual.

    O status depende exclusivamente do atingimento da meta dos meses
    encerrados. Vendas futuras permanecem em ``pulso`` e não melhoram o
    status fechado. A meta do grupo nunca é rateada pelos seus veículos.
    """

    grupo: str
    meta_ytd_centavos: int
    realizado_ytd: Decimal
    atingimento_ytd_pct: Decimal | None
    saldo_ytd: Decimal
    status: StatusParceiroMetas
    pulso: ParceiroPulso

    @property
    def meta_ytd(self) -> Decimal:
        return Decimal(self.meta_ytd_centavos) / _CEM


def avaliar_parceiros(
    vendas_df: pd.DataFrame,
    metas_df: pd.DataFrame,
    ano: int,
    *,
    data_referencia: Referencia = None,
) -> tuple[ParceiroMetas, ...]:
    """Consolida parceiros pela meta YTD e preserva seu Pulso Atual.

    Vigência, atividade e precedência são aplicadas separadamente em cada
    mês. O realizado fechado é reutilizado do consolidado oficial por
    parceiro do pulso, sem alteração de precisão ou arredondamento mensal.
    Percentuais contêm pontos percentuais (100 significa 100%). Não há
    classificação financeira quando a meta YTD é zero ou inexistente.
    """
    pulso = avaliar_pulso(
        vendas_df, metas_df, ano, data_referencia=data_referencia
    )
    metas = vigencia(metas_df, data_referencia=pulso.data_referencia)
    metas_ano = metas.loc[metas["ANO"] == pulso.ano]
    meta_ytd_por_grupo = dict.fromkeys(
        (parceiro.grupo for parceiro in pulso.parceiros), 0
    )
    for mes in range(1, pulso.meses_encerrados + 1):
        selecionadas = _selecionar_niveis(metas_ano[metas_ano["MES"] == mes])
        for linha in selecionadas[selecionadas["ATIVO"] == "SIM"].itertuples():
            meta_ytd_por_grupo[linha.GRUPO] += int(
                getattr(linha, COL_VALOR_META_CENTAVOS)
            )

    parceiros: list[ParceiroMetas] = []
    for compromisso in pulso.parceiros:
        meta_centavos = meta_ytd_por_grupo[compromisso.grupo]
        meta_ytd = Decimal(meta_centavos) / _CEM
        realizado = compromisso.realizado_meses_encerrados
        atingimento = (
            _percentual(realizado, meta_ytd)
            if pulso.meses_encerrados else None
        )
        status: StatusParceiroMetas = (
            "aguardando_mes_encerrado" if not pulso.meses_encerrados
            else "sem_meta_periodo" if atingimento is None
            else "acima_da_meta" if atingimento >= 100
            else "proximo_da_meta" if atingimento >= 90
            else "abaixo_da_meta"
        )
        parceiros.append(ParceiroMetas(
            grupo=compromisso.grupo,
            meta_ytd_centavos=meta_centavos,
            realizado_ytd=realizado,
            atingimento_ytd_pct=atingimento,
            saldo_ytd=realizado - meta_ytd,
            status=status,
            pulso=compromisso,
        ))
    return tuple(parceiros)


def cobertura_mensal_pulso(mes: MesPulso) -> Decimal | None:
    """Percentual já vendido frente à meta mensal; sem base positiva, None.

    Não converte venda futura em realizado. A nomenclatura da apresentação
    deve respeitar ``mes.tipo_valor`` e ``mes.estado_mes``.
    """
    return _percentual(mes.vendido, mes.meta)
