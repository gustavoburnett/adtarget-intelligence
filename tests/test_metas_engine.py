"""Regras puras de metas, com vendas e metas inteiramente sintéticas."""

import datetime as dt
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pandas as pd
import pytest

from src.data import metas, metrics
from src.data.cleaning import (
    COL_GRUPO,
    COL_MES_GANHO_DATA,
    COL_MES_VEICULACAO_DATA,
    COL_STATUS,
    COL_VALOR_BRUTO,
    COL_VALOR_LIQUIDO,
    COL_VEICULO,
)
from src.data.metas_schema import COL_LINHA_ORIGEM, COLUNAS_METAS, ErroDeMetas

REF = dt.date(2026, 3, 15)


def _meta(mes=1, valor=100, grupo="G", veiculo="", nivel="GRUPO", **extras):
    linha = {
        "NIVEL_META": nivel, "GRUPO": grupo, "VEICULO": veiculo,
        "ANO": 2026, "MES": mes, "VALOR_META": valor, "ATIVO": "SIM",
        "REVISAO": 1, "CRIADO_EM": "2026-01-01T00:00:00-03:00", "MOTIVO": "Teste",
    }
    linha.update(extras)
    return linha


def _metas(*linhas):
    return pd.DataFrame(linhas, columns=COLUNAS_METAS)


def _venda(mes="2026-01-01", valor=50, grupo="G", veiculo="V", status="FATURADO", ganho=None):
    return {
        COL_GRUPO: grupo, COL_VEICULO: veiculo, COL_STATUS: status,
        COL_VALOR_LIQUIDO: valor, COL_VALOR_BRUTO: valor * 10,
        COL_MES_VEICULACAO_DATA: mes, COL_MES_GANHO_DATA: ganho or mes,
    }


def _vendas(*linhas):
    df = pd.DataFrame(linhas, columns=list(_venda()))
    for coluna in (COL_MES_VEICULACAO_DATA, COL_MES_GANHO_DATA):
        df[coluna] = pd.to_datetime(df[coluna])
    return df


def _avaliar(vendas, plano, ano=2026, referencia=REF):
    return metas.avaliar_metas(vendas, plano, ano, data_referencia=referencia)


@pytest.mark.parametrize("ano,referencia,esperado", [
    (2026, dt.date(2026, 1, 1), 0),
    (2026, dt.date(2026, 1, 31), 0),
    (2026, dt.date(2026, 2, 1), 1),
    (2026, dt.date(2026, 3, 15), 2),
    (2026, dt.date(2026, 12, 31), 11),
    (2026, dt.date(2027, 1, 1), 12),
    (2025, dt.date(2026, 3, 15), 12),
    (2027, dt.date(2026, 3, 15), 0),
    (2026, dt.datetime(2026, 3, 1, 2, 59, tzinfo=dt.timezone.utc), 1),
    (2026, dt.datetime(2026, 3, 1, 3, 0, tzinfo=dt.timezone.utc), 2),
])
def test_meses_encerrados_calendario_e_fuso(ano, referencia, esperado):
    assert metas.meses_encerrados(ano, data_referencia=referencia) == esperado


@pytest.mark.parametrize("ano", [True, 2026.5, "2026", 0, 10000])
def test_ano_selecionado_invalido_e_rejeitado(ano):
    with pytest.raises(ValueError):
        metas.meses_encerrados(ano, data_referencia=REF)


def test_vigencia_maior_revisao_nao_maior_timestamp_e_sem_mutacao():
    plano = _metas(
        _meta(valor=100),
        _meta(valor=200, REVISAO=2, CRIADO_EM="2026-03-01T00:00:00-03:00"),
        _meta(valor=300, REVISAO=3, CRIADO_EM="2026-02-01T00:00:00-03:00"),
        _meta(nivel="VEICULO", veiculo="V", valor=70),
        _meta(mes=2, valor=400),
    )
    antes = plano.copy(deep=True)
    vigente = metas.vigencia(plano, data_referencia=REF)
    assert len(vigente) == 3
    grupo_jan = vigente[(vigente["NIVEL_META"] == "GRUPO") & (vigente["MES"] == 1)].iloc[0]
    assert grupo_jan["REVISAO"] == 3
    assert grupo_jan["VALOR_META"] == Decimal(300)
    assert COL_LINHA_ORIGEM in vigente
    assert set(vigente["NIVEL_META"]) == {"GRUPO", "VEICULO"}
    pd.testing.assert_frame_equal(plano, antes)


def test_grupo_cobre_todos_veiculos_e_domina_detalhamento():
    resultado = _avaliar(
        _vendas(_venda(valor=10, veiculo="A"), _venda(valor=20, veiculo="B")),
        _metas(_meta(valor=50), _meta(nivel="VEICULO", veiculo="A", valor=999)),
    )
    janeiro = resultado.meses[0]
    assert janeiro.meta == Decimal(50)
    assert janeiro.realizado == Decimal(30)
    assert janeiro.perimetro == (metas.EntidadeMeta("GRUPO", "G"),)
    assert resultado.meta_anual == Decimal(50)


def test_grupo_inativo_domina_veiculo_ativo_e_exclui_venda():
    resultado = _avaliar(
        _vendas(_venda()),
        _metas(_meta(valor=0, ATIVO="NAO"), _meta(nivel="VEICULO", veiculo="V")),
    )
    janeiro = resultado.meses[0]
    assert janeiro.estado_meta == "inativa"
    assert janeiro.perimetro == ()
    assert janeiro.meta_centavos == 0
    assert janeiro.realizado == 0
    assert resultado.realizado_ytd == 0


def test_meta_de_veiculo_respeita_par_grupo_veiculo():
    resultado = _avaliar(
        _vendas(
            _venda(valor=10, grupo="A", veiculo="MESMO NOME"),
            _venda(valor=90, grupo="B", veiculo="MESMO NOME"),
            _venda(valor=80, grupo="A", veiculo="OUTRO"),
        ),
        _metas(_meta(grupo="A", nivel="VEICULO", veiculo="MESMO NOME")),
    )
    assert resultado.realizado_ytd == 10
    assert resultado.meses[0].perimetro == (metas.EntidadeMeta("VEICULO", "A", "MESMO NOME"),)


def test_soma_veiculos_ativos_exclui_veiculo_inativo():
    resultado = _avaliar(
        _vendas(
            _venda(valor=10, veiculo="A"), _venda(valor=200, veiculo="B"),
            _venda(valor=20, veiculo="C"),
        ),
        _metas(
            _meta(nivel="VEICULO", veiculo="A", valor=50),
            _meta(nivel="VEICULO", veiculo="B", valor=0, ATIVO="NAO"),
            _meta(nivel="VEICULO", veiculo="C", valor=30),
        ),
    )
    assert resultado.meta_ytd == 80
    assert resultado.realizado_ytd == 30
    assert [e.veiculo for e in resultado.meses[0].perimetro] == ["A", "C"]


def test_soma_centavos_usa_inteiro_python_sem_overflow_int64():
    valor = Decimal("60000000000000000.00")
    resultado = _avaliar(
        _vendas(), _metas(_meta(valor=valor, grupo="A"), _meta(valor=valor, grupo="B")),
    )
    assert resultado.meta_ytd_centavos == 12000000000000000000
    assert resultado.meta_anual == valor * 2
    assert resultado.meses[0].estado_meta == "ativa"


def test_nivel_pode_mudar_entre_meses_sem_rateio():
    resultado = _avaliar(
        _vendas(*[
            _venda(mes=f"2026-0{mes}-01", valor=valor, veiculo=veiculo)
            for mes in (1, 2) for veiculo, valor in (("A", 10), ("B", 20))
        ]),
        _metas(_meta(valor=100), _meta(mes=2, valor=50, nivel="VEICULO", veiculo="A")),
    )
    assert resultado.realizado_ytd == 40
    assert resultado.meta_ytd == 150
    assert resultado.meses[0].realizado == 30
    assert resultado.meses[1].realizado == 10


def test_entrada_ausencia_e_saida_sao_distintas():
    resultado = _avaliar(
        _vendas(*[_venda(mes=f"2026-0{mes}-01") for mes in range(1, 5)]),
        _metas(_meta(mes=2), _meta(mes=3, valor=0, ATIVO="NAO")),
        referencia=dt.date(2026, 5, 1),
    )
    assert [m.estado_meta for m in resultado.meses[:4]] == ["ausente", "ativa", "inativa", "ausente"]
    assert [m.realizado for m in resultado.meses[:4]] == [0, 50, 0, 0]
    assert resultado.realizado_ytd == 50


def test_zero_ativo_permanece_perimetro_sem_percentual_inventado():
    resultado = _avaliar(_vendas(_venda()), _metas(_meta(valor=0)))
    janeiro = resultado.meses[0]
    assert janeiro.estado_meta == "zero_ativa"
    assert janeiro.perimetro
    assert janeiro.realizado == 50
    assert janeiro.atingimento_pct is None
    assert resultado.atingimento_ytd_pct is None
    assert resultado.meta_anual_conquistada_pct is None
    assert resultado.cobertura_plano_pct is None
    assert resultado.estado == "sem_meta_periodo"


@pytest.mark.parametrize("nome,canonico", [("Carrega +", "CARREGA+"), ("Rádio Melodia", "MELODIA")])
def test_alias_nos_dois_anos_e_em_metas_sem_mutar_fontes(nome, canonico):
    vendas = _vendas(
        _venda(valor=20, grupo=canonico), _venda(mes="2025-01-01", valor=10, grupo=nome),
    )
    plano = _metas(_meta(grupo=nome))
    vendas_antes, metas_antes = vendas.copy(deep=True), plano.copy(deep=True)
    resultado = _avaliar(vendas, plano)
    assert resultado.realizado_ytd == 20
    assert resultado.realizado_anterior_ytd == 10
    assert resultado.yoy_pct == 100
    assert resultado.meses[0].perimetro[0].grupo == canonico
    pd.testing.assert_frame_equal(vendas, vendas_antes)
    pd.testing.assert_frame_equal(plano, metas_antes)


def test_nome_parecido_nao_entra_por_aproximacao():
    resultado = _avaliar(
        _vendas(_venda(grupo="CARREGA++", valor=999), _venda(grupo="CARREGA+", valor=10)),
        _metas(_meta(grupo="CARREGA+")),
    )
    assert resultado.realizado_ytd == 10


def test_perimetro_brasil247_carrega_e_sem_meta_reconcilia_vendas_sinteticas():
    plano = _metas(*[
        linha
        for mes in range(1, 13)
        for linha in (
            _meta(
                mes=mes, grupo="BRASIL 247", valor=10 if mes <= 3 else 0,
                ATIVO="SIM" if mes <= 3 else "NAO",
            ),
            _meta(mes=mes, grupo="Carrega +", valor=10),
        )
    ])
    vendas = _vendas(*[
        linha
        for mes in range(1, 13)
        for linha in (
            _venda(mes=f"2026-{mes:02d}-01", grupo="BRASIL 247", valor=2),
            _venda(mes=f"2026-{mes:02d}-01", grupo="CARREGA+", valor=10),
            _venda(mes=f"2026-{mes:02d}-01", grupo="SISTEMA VERDES MARES", valor=70),
            _venda(mes=f"2025-{mes:02d}-01", grupo="BRASIL 247", valor=3),
            _venda(mes=f"2025-{mes:02d}-01", grupo="Carrega +", valor=5),
        )
    ])
    antes = vendas.copy(deep=True)
    resultado = _avaliar(vendas, plano, referencia=dt.date(2026, 5, 1))
    assert resultado.meses[2].realizado == 12
    assert resultado.meses[3].realizado == 10
    assert resultado.meses[2].realizado_anterior == 8
    assert resultado.meses[3].realizado_anterior == 5
    assert resultado.realizado_ytd == 46
    assert resultado.realizado_anterior_ytd == 29
    datas = vendas[COL_MES_VEICULACAO_DATA]
    total_ytd = Decimal(str(metrics.vendas(vendas[(datas.dt.year == 2026) & (datas.dt.month <= 4)])))
    fora = Decimal(70 * 4 + 2)
    assert total_ytd == resultado.realizado_ytd + fora
    assert metrics.vendas(vendas) == metrics.vendas(antes)
    pd.testing.assert_frame_equal(vendas, antes)


@pytest.mark.parametrize("status", sorted(metrics.STATUS_VENDAS))
def test_os_seis_status_oficiais_entram(status):
    resultado = _avaliar(_vendas(_venda(valor=7, status=status)), _metas(_meta()))
    assert resultado.realizado_ytd == 7


@pytest.mark.parametrize("status", ["CANCELADO", "BONIFICADO", "DESCONHECIDO"])
def test_status_fora_da_venda_nao_entra_nem_cria_base_yoy(status):
    resultado = _avaliar(
        _vendas(_venda(status=status), _venda(mes="2025-01-01", status=status)),
        _metas(_meta()),
    )
    assert resultado.realizado_ytd == 0
    assert resultado.realizado_anterior_ytd is None
    assert resultado.yoy_pct is None


def test_vendas_liquidas_veiculacao_e_metricas_oficiais_sem_faturado(monkeypatch):
    original = metrics.vendas
    chamadas = []

    def oficial(df, valor="liquido"):
        chamadas.append(valor)
        return original(df, valor)

    def proibido(*args, **kwargs):
        raise AssertionError("Metas não pode chamar faturado")

    monkeypatch.setattr(metrics, "vendas", oficial)
    monkeypatch.setattr(metrics, "faturado", proibido)
    resultado = _avaliar(
        _vendas(
            _venda(mes="2026-01-01", ganho="2026-12-01", valor=7),
            _venda(mes="2026-12-01", ganho="2026-01-01", valor=99),
            _venda(mes=None, valor=1000),
        ),
        _metas(_meta(), _meta(mes=12)),
    )
    assert resultado.realizado_ytd == 7
    assert chamadas and set(chamadas) == {"liquido"}


def test_mes_corrente_e_futuro_nao_entram_no_realizado():
    resultado = _avaliar(
        _vendas(*[_venda(mes=f"2026-0{mes}-01", valor=mes * 10) for mes in range(1, 5)]),
        _metas(*[_meta(mes=mes) for mes in range(1, 5)]),
    )
    assert resultado.realizado_ytd == 30
    assert resultado.meta_ytd == 200
    assert [m.estado_mes for m in resultado.meses[:4]] == ["encerrado", "encerrado", "em_andamento", "futuro"]
    assert resultado.meses[2].realizado is None
    assert resultado.meses[3].realizado_acumulado is None
    assert resultado.meses[2].atingimento_pct is None
    assert resultado.meses[2].yoy_pct is None


def test_yoy_like_for_like_usa_perimetro_do_ano_selecionado_por_mes():
    resultado = _avaliar(
        _vendas(
            _venda(valor=30, grupo="A"),
            _venda(mes="2026-02-01", valor=40, grupo="B"),
            _venda(mes="2025-01-01", valor=10, grupo="A"),
            _venda(mes="2025-01-01", valor=999, grupo="B"),
            _venda(mes="2025-02-01", valor=999, grupo="A"),
            _venda(mes="2025-02-01", valor=20, grupo="B"),
        ),
        _metas(_meta(grupo="A"), _meta(mes=2, grupo="B")),
    )
    assert resultado.realizado_anterior_ytd == 30
    assert resultado.meses[0].yoy_pct == 200
    assert resultado.meses[1].yoy_pct == 100
    assert resultado.yoy_pct == Decimal(40) / Decimal(30) * 100


def test_anterior_anual_completo_usa_perimetros_dos_meses_futuros():
    resultado = _avaliar(
        _vendas(_venda(mes="2025-01-01", valor=10), _venda(mes="2025-12-01", valor=90)),
        _metas(*[_meta(mes=mes) for mes in range(1, 13)]),
    )
    assert resultado.realizado_anterior_ytd == 10
    assert resultado.meses[-1].realizado_anterior == 90
    assert resultado.meses[-1].realizado_anterior_acumulado == 100
    assert resultado.meses[-1].realizado_acumulado is None
    assert resultado.meses[-1].meta_acumulada == 1200


def test_anterior_com_entidade_inativa_exclui_vendas_depois_da_saida():
    resultado = _avaliar(
        _vendas(_venda(mes="2025-01-01", valor=10), _venda(mes="2025-02-01", valor=999)),
        _metas(_meta(), _meta(mes=2, valor=0, ATIVO="NAO")),
    )
    assert resultado.realizado_anterior_ytd == 10
    assert resultado.meses[1].realizado_anterior is None
    assert resultado.meses[1].realizado_anterior_acumulado == 10


@pytest.mark.parametrize("anterior", [None, 0, -10])
def test_yoy_sem_base_positiva_nao_divide(anterior):
    linhas = [_venda(valor=50)]
    if anterior is not None:
        linhas.append(_venda(mes="2025-01-01", valor=anterior))
    resultado = _avaliar(_vendas(*linhas), _metas(_meta()))
    assert resultado.meses[0].yoy_pct is None
    assert resultado.yoy_pct is None


def test_realizado_nao_arredonda_pi_nem_mes_e_invariantes_exatos():
    vendas = _vendas(_venda(valor=0.0042), _venda(mes="2026-02-01", valor=0.0039))
    resultado = _avaliar(vendas, _metas(_meta(), _meta(mes=2)))
    assert resultado.meses[0].realizado == Decimal("0.0042")
    assert resultado.meses[1].realizado == Decimal("0.0039")
    assert resultado.realizado_ytd == Decimal("0.0081")
    assert resultado.realizado_ytd.quantize(Decimal("0.01")) == Decimal("0.01")
    assert sum(m.realizado for m in resultado.meses[:2]) == resultado.realizado_ytd
    assert sum(m.meta_centavos for m in resultado.meses[:2]) == resultado.meta_ytd_centavos
    assert resultado.meses[1].realizado_acumulado == resultado.realizado_ytd
    assert resultado.meses[1].meta_acumulada_centavos == resultado.meta_ytd_centavos
    assert resultado.meses[-1].meta_acumulada_centavos == resultado.meta_anual_centavos


def test_formula_dos_kpis_forecast_e_pontos_percentuais():
    resultado = _avaliar(
        _vendas(
            _venda(valor=120), _venda(mes="2026-02-01", valor=80),
            _venda(mes="2025-01-01", valor=50), _venda(mes="2025-02-01", valor=50),
        ),
        _metas(*[_meta(mes=mes) for mes in range(1, 13)]),
    )
    assert resultado.meta_anual == 1200
    assert resultado.meta_ytd == 200
    assert resultado.realizado_ytd == 200
    assert resultado.atingimento_ytd_pct == 100
    assert resultado.saldo_ytd == 0
    assert resultado.meta_anual_conquistada_pct == Decimal(200) / Decimal(1200) * 100
    assert resultado.gap_anual == 1000
    assert resultado.necessidade_media == 100
    assert resultado.plano_futuro == 1000
    assert resultado.cobertura_plano_pct == 100
    assert resultado.forecast == 1200
    assert resultado.projetado_atingimento_pct == 100
    assert resultado.yoy_pct == 100


@pytest.mark.parametrize("realizado,saldo,gap", [(50, -50, 50), (100, 0, 0), (150, 50, -50)])
def test_saldo_ytd_e_gap_anual_tem_sinais_opostos(realizado, saldo, gap):
    resultado = _avaliar(_vendas(_venda(valor=realizado)), _metas(_meta()))
    assert resultado.saldo_ytd == saldo
    assert resultado.gap_anual == gap
    assert resultado.meses[0].saldo == saldo
    if gap <= 0:
        assert resultado.cobertura_plano_pct is None


@pytest.mark.parametrize("referencia,forecast", [
    (dt.date(2026, 1, 15), None),
    (dt.date(2026, 2, 15), None),
    (dt.date(2026, 3, 15), Decimal(600)),
    (dt.date(2027, 1, 1), None),
])
def test_forecast_conta_meses_calendario_e_suprime_em_ano_encerrado(referencia, forecast):
    resultado = _avaliar(
        _vendas(_venda(valor=100)), _metas(*[_meta(mes=mes) for mes in range(1, 13)]),
        referencia=referencia,
    )
    assert resultado.forecast == forecast
    if forecast is None:
        assert resultado.projetado_atingimento_pct is None


def test_ano_encerrado_suprime_projecoes_e_preserva_resultado_final():
    resultado = _avaliar(
        _vendas(_venda(mes="2025-12-01", valor=70)),
        _metas(_meta(mes=12, ANO=2025)), ano=2025,
    )
    assert resultado.estado == "ano_encerrado"
    assert resultado.meses_encerrados == 12
    assert resultado.meses_restantes == 0
    assert resultado.realizado_ytd == 70
    assert resultado.gap_anual == 30
    assert resultado.necessidade_media is None
    assert resultado.plano_futuro is None
    assert resultado.cobertura_plano_pct is None
    assert resultado.forecast is None
    assert resultado.meses[-1].realizado_acumulado == 70


def test_janeiro_sem_mes_encerrado_preserva_plano_e_lacunas():
    resultado = _avaliar(
        _vendas(_venda()), _metas(_meta()), referencia=dt.date(2026, 1, 15),
    )
    assert resultado.estado == "aguardando_mes_encerrado"
    assert resultado.realizado_ytd == 0
    assert resultado.atingimento_ytd_pct is None
    assert all(m.realizado is None and m.realizado_acumulado is None for m in resultado.meses)
    assert resultado.meses[0].estado_mes == "em_andamento"
    assert resultado.meta_anual == 100
    assert resultado.plano_futuro == 100


def test_ano_futuro_todos_meses_abertos_e_metas_conhecidas():
    resultado = _avaliar(_vendas(), _metas(_meta(ANO=2027)), ano=2027)
    assert resultado.meses_encerrados == 0
    assert all(m.estado_mes == "futuro" for m in resultado.meses)
    assert resultado.meta_anual == 100
    assert resultado.realizado_ytd == 0


def test_sem_metas_e_sem_meta_ytd_sao_estados_separados():
    vendas = _vendas(_venda())
    vazio = _avaliar(vendas, _metas())
    futuro = _avaliar(vendas, _metas(_meta(mes=12)))
    assert vazio.estado == "sem_metas"
    assert futuro.estado == "sem_meta_periodo"
    assert vazio.meta_anual == 0
    assert futuro.meta_anual == 100
    assert vazio.realizado_ytd == futuro.realizado_ytd == 0
    assert vazio.atingimento_ytd_pct is futuro.atingimento_ytd_pct is None


@pytest.mark.parametrize("zero_ativo", [False, True])
def test_sem_meta_ytd_suprime_percentuais_e_preserva_moeda(zero_ativo):
    linhas = [_meta(mes=12)]
    if zero_ativo:
        linhas.append(_meta(valor=0))
    resultado = _avaliar(_vendas(_venda(valor=50)), _metas(*linhas))
    assert resultado.estado == "sem_meta_periodo"
    assert resultado.realizado_ytd == (50 if zero_ativo else 0)
    assert resultado.meta_anual == 100
    assert resultado.plano_futuro == 100
    assert resultado.forecast == (300 if zero_ativo else 0)
    assert resultado.atingimento_ytd_pct is None
    assert resultado.meta_anual_conquistada_pct is None
    assert resultado.cobertura_plano_pct is None
    assert resultado.projetado_atingimento_pct is None


def test_mes_encerrado_sem_vendas_e_zero_real_e_nao_lacuna():
    resultado = _avaliar(_vendas(_venda(mes="2025-01-01", valor=10)), _metas(_meta()))
    assert resultado.meses[0].realizado == 0
    assert resultado.meses[0].atingimento_pct == 0
    assert resultado.meses[0].yoy_pct == -100
    assert resultado.meses[2].realizado is None


def test_resultado_e_entidades_sao_imutaveis():
    resultado = _avaliar(_vendas(), _metas(_meta()))
    with pytest.raises(FrozenInstanceError):
        resultado.ano = 2025
    with pytest.raises(FrozenInstanceError):
        resultado.meses[0].meta_centavos = 0
    with pytest.raises(FrozenInstanceError):
        resultado.meses[0].perimetro[0].grupo = "OUTRO"


def test_engine_propaga_falha_de_schema_sem_consolidacao_parcial():
    with pytest.raises(ErroDeMetas):
        _avaliar(_vendas(), _metas(_meta(), _meta(mes=2, ATIVO="NAO", valor=100)))


def test_metricas_e_fontes_existentes_permanecem_invariantes():
    vendas = _vendas(_venda(grupo="Carrega +"), _venda(grupo="OUTRO", valor=90))
    plano = _metas(_meta(grupo="CARREGA+"))
    antes = vendas.copy(deep=True)
    venda_total = metrics.vendas(vendas)
    bruto_total = metrics.vendas(vendas, "bruto")
    ytd = metrics.ytd(vendas, 2026, hoje=REF)
    _avaliar(vendas, plano)
    pd.testing.assert_frame_equal(vendas, antes)
    assert metrics.vendas(vendas) == venda_total
    assert metrics.vendas(vendas, "bruto") == bruto_total
    assert metrics.ytd(vendas, 2026, hoje=REF) == ytd
