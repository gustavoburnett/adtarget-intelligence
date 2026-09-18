"""Regras aprovadas da Sprint 2.1; fixtures isoladas, sem Sheets ou credenciais."""

import datetime as dt
from dataclasses import FrozenInstanceError

import pandas as pd
import pytest

from src.data import metrics, radar
from src.data.cleaning import COL_MES_GANHO_DATA, COL_MES_VEICULACAO_DATA

AGORA = dt.datetime(2026, 9, 18, 12)


def linha(mes, total, grupo="G", *, bruto=None, ganho=None, status="FATURADO"):
    return {
        "GRUPO": grupo, "VEICULO": "V", "CLIENTE": "C", "CAMPANHA": "Campanha", "AGENCIA": "A",
        "STATUS": status, "VALOR PI LIQUIDO": total,
        "VALOR PI BRUTO": total if bruto is None else bruto,
        COL_MES_VEICULACAO_DATA: pd.Timestamp(mes),
        COL_MES_GANHO_DATA: pd.Timestamp(mes if ganho is None else ganho),
        "ANO_ABA": pd.Timestamp(mes).year if mes is not None else 2026,
    }


def frame(*linhas):
    dados = pd.DataFrame(linhas, columns=linha("2026-01-01", 1).keys())
    for coluna in (COL_MES_GANHO_DATA, COL_MES_VEICULACAO_DATA):
        dados[coluna] = pd.to_datetime(dados[coluna])
    return dados


def avaliar(dados, ano=2026, **kwargs):
    return radar.avaliar_radar(dados, ano, agora=AGORA, **kwargs)


def recorde(total=120):
    return frame(*[
        linha(p.start_time, 100) for p in pd.period_range("2025-08", "2026-07", freq="M")
    ], linha("2026-08-01", total))


@pytest.mark.parametrize("total,tipo", [(115, "crescimento"), (85, "queda"),
                                          (114.99, None), (85.01, None), (100, None)])
def test_thresholds_inclusivos(total, tipo):
    estado = avaliar(frame(linha("2025-01-01", 100), linha("2026-01-01", total)))
    assert [i.tipo for i in estado.insights] == ([tipo] if tipo else [])
    assert estado.status == ("ativo" if tipo else "silencio")


def test_maiores_por_tipo_e_desempate_estavel():
    dados = frame(*[
        l for g, total in [("Z", 150), ("A", 150), ("B", 120), ("C", 50), ("D", 70)]
        for l in (linha("2025-01-01", 100, g), linha("2026-01-01", total, g))
    ])
    estado = avaliar(dados)
    assert [(i.tipo, i.entidade) for i in estado.insights] == [("queda", "C"), ("crescimento", "A")]
    assert avaliar(dados.sample(frac=1, random_state=3)) == estado


def test_grupo_que_desapareceu_e_queda_de_100_porcento():
    estado = avaliar(frame(linha("2025-01-01", 100, "Sumiu"), linha("2026-01-01", 100, "Outro")))
    assert estado.insights[0].entidade == "Sumiu"
    assert estado.insights[0].variacao_pct == -100


def test_periodo_carregado_sem_vendas_pode_ter_queda():
    estado = avaliar(frame(linha("2025-01-01", 100), linha("2026-01-01", 100, status="CANCELADO")))
    assert estado.insights[0].variacao_pct == -100


@pytest.mark.parametrize("anterior", [0, -100, None])
def test_base_sem_percentual_confiavel_nao_gera_insight(anterior):
    linhas = [linha("2026-01-01", 200)]
    if anterior is not None:
        linhas.append(linha("2025-01-01", anterior))
    estado = avaliar(frame(*linhas))
    assert estado.status == "dados_insuficientes"
    assert estado.insights == ()


def test_ytd_inclui_mes_corrente_e_exclui_futuro():
    estado = avaliar(frame(linha("2025-09-01", 100), linha("2025-10-01", 9999),
                           linha("2026-09-01", 120), linha("2026-10-01", 9999)))
    insight = estado.insights[0]
    assert insight.valor_atual == 120
    assert insight.valor_anterior == 100
    assert insight.periodo_atual == (dt.date(2026, 1, 1), dt.date(2026, 9, 30))
    assert "01/2025–09/2025" in insight.referencia_comparacao


def test_ano_encerrado_compara_ano_inteiro():
    estado = avaliar(frame(linha("2024-12-01", 100), linha("2025-12-01", 120)), 2025)
    assert estado.insights[0].periodo_atual[1] == dt.date(2025, 12, 31)


def test_toggles_mudam_valor_e_criterio():
    dados = frame(linha("2025-01-01", 100, bruto=100),
                  linha("2026-01-01", 120, bruto=80, ganho="2026-10-01"))
    assert avaliar(dados).insights[0].tipo == "crescimento"
    assert avaliar(dados, valor="bruto").insights[0].tipo == "queda"
    assert avaliar(dados, criterio_mes="ganho").status == "dados_insuficientes"


@pytest.mark.parametrize("status", ["CANCELADO", "BONIFICADO", "DESCONHECIDO", ""])
def test_status_excluidos_nao_influenciam_vendas(status):
    dados = frame(linha("2025-01-01", 100), linha("2026-01-01", 100),
                  linha("2026-01-01", 9999, status=status))
    assert avaliar(dados).status == "silencio"


def test_recorde_usa_ultimo_mes_e_12_anteriores():
    estado = avaliar(recorde())
    destaque = next(i for i in estado.insights if i.tipo == "destaque")
    assert destaque.valor_anterior == 100
    assert destaque.variacao_pct == 20
    assert destaque.periodo_atual == (dt.date(2026, 8, 1), dt.date(2026, 8, 31))
    assert destaque.periodo_anterior == (dt.date(2025, 8, 1), dt.date(2026, 7, 31))
    assert "12 meses completos" in destaque.referencia_comparacao


@pytest.mark.parametrize("total", [100, 90])
def test_igualdade_ou_queda_nao_e_recorde(total):
    estado = avaliar(recorde(total))
    assert "destaque" in estado.regras_avaliadas
    assert all(i.tipo != "destaque" for i in estado.insights)


def test_recorde_ignora_mes_corrente_e_futuro():
    dados = pd.concat([recorde(100), frame(linha("2026-09-01", 9999), linha("2026-10-01", 9999))])
    assert all(i.tipo != "destaque" for i in avaliar(dados).insights)


def test_pico_antigo_na_janela_nao_e_recorde_do_ultimo_mes():
    dados = recorde(100)
    dados.loc[dados[COL_MES_VEICULACAO_DATA] == pd.Timestamp("2026-07-01"), "VALOR PI LIQUIDO"] = 999
    assert all(i.tipo != "destaque" for i in avaliar(dados).insights)


def test_mes_ausente_nao_e_zero_para_comparar_recorde():
    dados = recorde().iloc[1:]
    estado = avaliar(dados)
    assert "destaque" in estado.regras_sem_comparacao
    assert all(i.tipo != "destaque" for i in estado.insights)


def test_maximo_anterior_zero_nao_gera_recorde_percentual():
    dados = recorde()
    dados.loc[dados[COL_MES_VEICULACAO_DATA] < pd.Timestamp("2026-08-01"), "VALOR PI LIQUIDO"] = 0
    assert all(i.tipo != "destaque" for i in avaliar(dados).insights)


def test_recorde_ano_encerrado_nao_usa_ano_posterior():
    dados = frame(*[linha(p.start_time, 100) for p in pd.period_range("2024-12", "2025-11", freq="M")],
                  linha("2025-12-01", 120), linha("2026-08-01", 999))
    destaque = next(i for i in avaliar(dados, 2025).insights if i.tipo == "destaque")
    assert destaque.periodo_atual[0] == dt.date(2025, 12, 1)


def test_filtro_dimensional_e_consolidacao_do_recorde():
    dados = pd.concat([recorde(120), frame(linha("2025-01-01", 1000, "Outro"),
                                          linha("2026-01-01", 500, "Outro"))])
    filtrado = dados[dados.GRUPO == "G"]
    estado = avaliar(filtrado)
    assert all(i.entidade != "Outro" for i in estado.insights)
    assert next(i for i in estado.insights if i.tipo == "destaque").valor_atual == 120


def test_prioridade_de_tipo_supera_magnitude_extrema():
    dados = pd.concat([recorde(200), frame(linha("2025-01-01", 100, "Queda"),
                                        linha("2026-01-01", 80, "Queda"),
                                        linha("2025-01-01", .001, "Explosao"),
                                        linha("2026-01-01", 1000, "Explosao"))])
    # Janeiro alto mudaria o recorde: mova a explosão para o mês corrente.
    dados.loc[(dados.GRUPO == "Explosao"), COL_MES_VEICULACAO_DATA] = pd.to_datetime(["2025-09-01", "2026-09-01"])
    estado = avaliar(dados)
    assert [i.tipo for i in estado.insights] == ["queda", "destaque", "crescimento"]
    assert estado.insights[-1].magnitude > 100000
    assert len(estado.insights) <= 5


@pytest.mark.parametrize("dados", [frame(), frame(linha(None, 100)),
                                   frame(linha("2025-01-01", 100))])
def test_sem_historico_comparavel_e_insuficiente(dados):
    assert avaliar(dados).status == "dados_insuficientes"


def test_silencio_informa_comparacao_parcial():
    estado = avaliar(frame(linha("2025-01-01", 100), linha("2026-01-01", 100)))
    assert estado.status == "silencio"
    assert set(estado.regras_avaliadas) == {"queda", "crescimento"}
    assert estado.regras_sem_comparacao == ("destaque",)


def test_ano_futuro_nao_gera_comparacao():
    assert avaliar(frame(linha("2026-01-01", 100), linha("2027-01-01", 120)), 2027).status == "dados_insuficientes"


def test_sincronizacao_antiga_nao_suprime_insights_e_risco_nao_e_gerado():
    dados = frame(linha("2025-01-01", 100), linha("2026-01-01", 120))
    estado = avaliar(dados, sincronizado_em=dt.datetime(2020, 1, 1))
    assert estado.status == "ativo"
    assert all(i.tipo != "risco" for i in estado.insights)


def test_ultimo_mes_disponivel_pode_ser_anterior_ao_mes_passado():
    dados = frame(*[linha(p.start_time, 100) for p in pd.period_range("2025-06", "2026-05", freq="M")],
                  linha("2026-06-01", 120))
    destaque = next(i for i in avaliar(dados).insights if i.tipo == "destaque")
    assert destaque.periodo_atual[0] == dt.date(2026, 6, 1)


def test_recorde_soma_grupos_no_recorte():
    dados = recorde(60)
    outro = dados.copy()
    outro["GRUPO"] = "Outro"
    outro["VALOR PI LIQUIDO"] = 10
    outro.loc[outro[COL_MES_VEICULACAO_DATA] == pd.Timestamp("2026-08-01"), "VALOR PI LIQUIDO"] = 70
    destaque = next(i for i in avaliar(pd.concat([dados, outro])).insights if i.tipo == "destaque")
    assert destaque.valor_atual == 130
    assert destaque.valor_anterior == 110


@pytest.mark.parametrize("kwargs", [{"valor": "invalido"}, {"criterio_mes": "invalido"}])
def test_toggles_invalidos_rejeitados(kwargs):
    with pytest.raises(ValueError):
        avaliar(recorde(), **kwargs)


def test_cta_configuravel_e_contrato_imutavel():
    ctas = dict(radar.CTAS, crescimento=radar.CTA("custom", "Texto aprovado"))
    estado = avaliar(frame(linha("2025-01-01", 100), linha("2026-01-01", 120)), ctas=ctas)
    assert estado.insights[0].cta.texto == "Texto aprovado"
    assert estado.insights[0].cta.destino is None
    with pytest.raises(FrozenInstanceError):
        estado.status = "silencio"


@pytest.mark.parametrize("valor", ["liquido", "bruto"])
@pytest.mark.parametrize("criterio", ["ganho", "veiculacao"])
def test_regressao_metricas_e_dados_invariantes(valor, criterio):
    dados = recorde()
    copia = dados.copy(deep=True)
    def snapshot():
        return (metrics.vendas(dados, valor), metrics.faturado(dados, valor),
                metrics.em_aberto(dados, valor), metrics.ticket_medio(dados, valor),
                metrics.quantidade_campanhas(dados),
                metrics.ytd(dados, 2026, valor, criterio, AGORA.date()),
                metrics.evolucao_mensal(dados, 2026, valor, criterio))
    antes = snapshot()
    avaliar(dados, valor=valor, criterio_mes=criterio)
    assert snapshot() == antes
    pd.testing.assert_frame_equal(dados, copia)
