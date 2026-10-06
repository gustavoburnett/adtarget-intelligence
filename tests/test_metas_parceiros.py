"""Ritmo fechado por parceiro separado do compromisso anual; fonte sintética."""

import datetime as dt
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pandas as pd
import pytest

from src.data import metas
from src.data.cleaning import (
    COL_GRUPO,
    COL_MES_GANHO_DATA,
    COL_MES_VEICULACAO_DATA,
    COL_STATUS,
    COL_VALOR_BRUTO,
    COL_VALOR_LIQUIDO,
    COL_VEICULO,
)
from src.data.metas_schema import COLUNAS_METAS, ErroDeMetas

REF = dt.date(2026, 10, 5)


def _meta(mes=1, valor=100, grupo="G", veiculo="", nivel="GRUPO", **extras):
    linha = {
        "NIVEL_META": nivel, "GRUPO": grupo, "VEICULO": veiculo,
        "ANO": 2026, "MES": mes, "VALOR_META": valor, "ATIVO": "SIM",
        "REVISAO": 1, "CRIADO_EM": "2026-01-01T00:00:00-03:00", "MOTIVO": "Teste",
    }
    linha.update(extras)
    return linha


def _plano(*linhas):
    return pd.DataFrame(linhas, columns=COLUNAS_METAS)


def _venda(mes=1, valor=10, grupo="G", veiculo="V", status="FATURADO", ano=2026):
    return {
        COL_GRUPO: grupo, COL_VEICULO: veiculo, COL_STATUS: status,
        COL_VALOR_LIQUIDO: valor, COL_VALOR_BRUTO: valor * 10,
        COL_MES_VEICULACAO_DATA: f"{ano}-{mes:02d}-01",
        COL_MES_GANHO_DATA: "2025-01-01",
    }


def _vendas(*linhas):
    df = pd.DataFrame(linhas, columns=list(_venda()))
    for coluna in (COL_MES_VEICULACAO_DATA, COL_MES_GANHO_DATA):
        df[coluna] = pd.to_datetime(df[coluna])
    return df


def _avaliar(vendas, plano, ano=2026, referencia=REF):
    return metas.avaliar_parceiros(vendas, plano, ano, data_referencia=referencia)


def test_duas_reguas_futuro_supera_meta_anual_sem_melhorar_status_fechado():
    vendas = _vendas(_venda(valor=50), _venda(mes=10, valor=500, status="A VEICULAR"))
    plano = _plano(_meta(valor=100), _meta(mes=10, valor=100))
    parceiro, = _avaliar(vendas, plano)
    assert parceiro.meta_ytd == 100
    assert parceiro.realizado_ytd == 50
    assert parceiro.atingimento_ytd_pct == 50
    assert parceiro.saldo_ytd == -50
    assert parceiro.status == "abaixo_da_meta"
    assert parceiro.pulso.meta_anual == 200
    assert parceiro.pulso.total_vendido_ano == 550
    assert parceiro.pulso.ja_vendido_meses_restantes == 500
    assert parceiro.pulso.percentual_meta_ja_vendida == 275
    assert parceiro.pulso.gap_comercial == -350
    assert parceiro.pulso.status == "meta_superada"


@pytest.mark.parametrize("valor,status", [
    (0, "abaixo_da_meta"),
    (89.99, "abaixo_da_meta"),
    (90, "proximo_da_meta"),
    (99.99, "proximo_da_meta"),
    (100, "acima_da_meta"),
    (125, "acima_da_meta"),
])
def test_status_usa_limites_exatos_do_atingimento_ytd(valor, status):
    parceiro, = _avaliar(_vendas(_venda(valor=valor)), _plano(_meta()))
    assert parceiro.status == status
    assert parceiro.atingimento_ytd_pct == Decimal(str(valor))
    assert parceiro.saldo_ytd == Decimal(str(valor)) - 100


def test_meta_ytd_inclui_so_meses_encerrados_sem_excluir_pulso_futuro():
    parceiro, = _avaliar(
        _vendas(_venda(mes=9, valor=70), _venda(mes=10, valor=200)),
        _plano(_meta(mes=9, valor=100), _meta(mes=10, valor=900)),
    )
    assert parceiro.meta_ytd_centavos == 10000
    assert parceiro.realizado_ytd == 70
    assert parceiro.atingimento_ytd_pct == 70
    assert parceiro.pulso.meta_anual == 1000
    assert parceiro.pulso.total_vendido_ano == 270


def test_meta_zero_ativa_preserva_venda_mas_nao_inventa_atingimento():
    parceiro, = _avaliar(_vendas(_venda(valor=20)), _plano(_meta(valor=0)))
    assert parceiro.meta_ytd == 0
    assert parceiro.realizado_ytd == 20
    assert parceiro.saldo_ytd == 20
    assert parceiro.atingimento_ytd_pct is None
    assert parceiro.status == "sem_meta_periodo"


def test_inatividade_mensal_exclui_venda_sem_apagar_historico_ativo():
    parceiro, = _avaliar(
        _vendas(_venda(mes=3, grupo="BRASIL 247", valor=70),
                _venda(mes=4, grupo="BRASIL 247", valor=900),
                _venda(mes=10, grupo="BRASIL 247", valor=800)),
        _plano(_meta(mes=3, grupo="BRASIL 247"),
               _meta(mes=4, grupo="BRASIL 247", valor=0, ATIVO="NAO"),
               _meta(mes=10, grupo="BRASIL 247", valor=0, ATIVO="NAO")),
    )
    assert parceiro.meta_ytd == 100
    assert parceiro.realizado_ytd == 70
    assert parceiro.atingimento_ytd_pct == 70
    assert parceiro.pulso.total_vendido_ano == 70
    assert parceiro.pulso.ja_vendido_meses_restantes == 0


def test_entidade_sem_meta_no_mes_nao_acrescenta_realizado():
    parceiro, = _avaliar(
        _vendas(_venda(mes=1, valor=20), _venda(mes=2, valor=900),
                _venda(mes=1, grupo="SEM META", valor=800)),
        _plano(_meta()),
    )
    assert parceiro.realizado_ytd == 20
    assert parceiro.meta_ytd == 100
    assert parceiro.grupo == "G"


def test_grupo_domina_detalhamento_sem_ratear_meta_nem_duplicar_vendas():
    parceiro, = _avaliar(
        _vendas(_venda(veiculo="A", valor=20), _venda(veiculo="B", valor=30)),
        _plano(_meta(valor=100), _meta(nivel="VEICULO", veiculo="A", valor=999)),
    )
    assert parceiro.meta_ytd == 100
    assert parceiro.realizado_ytd == 50
    assert parceiro.pulso.meta_anual == 100


def test_grupo_inativo_domina_meta_de_veiculo_ativa():
    parceiro, = _avaliar(
        _vendas(_venda(valor=900)),
        _plano(_meta(valor=0, ATIVO="NAO"),
               _meta(nivel="VEICULO", veiculo="V", valor=999)),
    )
    assert parceiro.meta_ytd == 0
    assert parceiro.realizado_ytd == 0
    assert parceiro.atingimento_ytd_pct is None
    assert parceiro.status == "sem_meta_periodo"


def test_veiculos_somam_meta_no_grupo_respeitando_par_exato():
    parceiros = _avaliar(
        _vendas(_venda(grupo="A", veiculo="V", valor=20),
                _venda(grupo="A", veiculo="W", valor=30),
                _venda(grupo="A", veiculo="OUTRO", valor=900),
                _venda(grupo="B", veiculo="V", valor=40)),
        _plano(_meta(grupo="A", nivel="VEICULO", veiculo="V", valor=60),
               _meta(grupo="A", nivel="VEICULO", veiculo="W", valor=40),
               _meta(grupo="B", nivel="VEICULO", veiculo="V", valor=200)),
    )
    por_grupo = {p.grupo: p for p in parceiros}
    assert por_grupo["A"].meta_ytd == 100
    assert por_grupo["A"].realizado_ytd == 50
    assert por_grupo["B"].meta_ytd == 200
    assert por_grupo["B"].realizado_ytd == 40
    assert sum(p.meta_ytd for p in parceiros) == 300
    assert sum(p.realizado_ytd for p in parceiros) == 90


def test_nivel_muda_entre_meses_sem_duplicar_parceiro():
    parceiro, = _avaliar(
        _vendas(_venda(mes=1, veiculo="A", valor=20),
                _venda(mes=1, veiculo="B", valor=30),
                _venda(mes=2, veiculo="A", valor=40),
                _venda(mes=2, veiculo="B", valor=900)),
        _plano(_meta(mes=1, valor=100),
               _meta(mes=2, valor=50, nivel="VEICULO", veiculo="A")),
    )
    assert parceiro.meta_ytd == 150
    assert parceiro.realizado_ytd == 90
    assert parceiro.atingimento_ytd_pct == 60


def test_vigencia_usa_maior_revisao_mes_a_mes():
    parceiro, = _avaliar(
        _vendas(_venda(valor=180)),
        _plano(_meta(valor=100), _meta(valor=200, REVISAO=2)),
    )
    assert parceiro.meta_ytd == 200
    assert parceiro.atingimento_ytd_pct == 90
    assert parceiro.status == "proximo_da_meta"


@pytest.mark.parametrize("alias,canonico", [
    ("Carrega +", "CARREGA+"), ("Rádio Melodia", "MELODIA"),
])
def test_alias_oficial_na_camada_metas_sem_modificar_entradas(alias, canonico):
    vendas = _vendas(_venda(grupo=alias, valor=50),
                     _venda(grupo=canonico + "+", valor=900))
    plano = _plano(_meta(grupo=canonico))
    antes_vendas, antes_plano = vendas.copy(deep=True), plano.copy(deep=True)
    parceiro, = _avaliar(vendas, plano)
    assert parceiro.grupo == canonico
    assert parceiro.realizado_ytd == 50
    pd.testing.assert_frame_equal(vendas, antes_vendas)
    pd.testing.assert_frame_equal(plano, antes_plano)


def test_janeiro_mostra_aguardando_sem_inventar_status_fechado():
    parceiro, = _avaliar(
        _vendas(_venda(valor=200)), _plano(_meta()),
        referencia=dt.date(2026, 1, 5),
    )
    assert parceiro.meta_ytd == 0
    assert parceiro.realizado_ytd == 0
    assert parceiro.atingimento_ytd_pct is None
    assert parceiro.status == "aguardando_mes_encerrado"
    assert parceiro.pulso.total_vendido_ano == 200


def test_parceiro_apenas_futuro_sem_meta_fechada_preserva_compromisso_anual():
    parceiro, = _avaliar(
        _vendas(_venda(mes=11, valor=95)), _plano(_meta(mes=11)),
    )
    assert parceiro.meta_ytd == 0
    assert parceiro.realizado_ytd == 0
    assert parceiro.atingimento_ytd_pct is None
    assert parceiro.status == "sem_meta_periodo"
    assert parceiro.pulso.percentual_meta_ja_vendida == 95


def test_ano_encerrado_usa_os_doze_meses_e_nao_tem_carteira_futura():
    parceiro, = _avaliar(
        _vendas(_venda(mes=12, ano=2025, valor=125)),
        _plano(_meta(mes=12, ANO=2025)), ano=2025,
    )
    assert parceiro.meta_ytd == parceiro.pulso.meta_anual == 100
    assert parceiro.realizado_ytd == parceiro.pulso.total_vendido_ano == 125
    assert parceiro.atingimento_ytd_pct == 125
    assert parceiro.status == "acima_da_meta"
    assert parceiro.pulso.ja_vendido_meses_restantes == 0


def test_nove_entidades_reconciliam_meta_e_realizado_sem_lista_fixa_na_engine():
    nomes = ("TEADS", "INFOMONEY", "CLIMATEMPO", "BRASIL 247", "WEBEDIA",
             "FORBES", "DISNEY", "MELODIA", "CARREGA+")
    plano = _plano(*[_meta(grupo=g, mes=m) for g in nomes for m in (1, 10)])
    vendas = _vendas(*[_venda(grupo=g, mes=m, valor=50) for g in nomes for m in (1, 10)])
    parceiros = _avaliar(vendas, plano)
    fechado = metas.avaliar_metas(vendas, plano, 2026, data_referencia=REF)
    pulso = metas.avaliar_pulso(vendas, plano, 2026, data_referencia=REF)
    assert len(parceiros) == 9
    assert {p.grupo for p in parceiros} == set(nomes)
    assert sum(p.meta_ytd for p in parceiros) == fechado.meta_ytd
    assert sum(p.realizado_ytd for p in parceiros) == fechado.realizado_ytd
    assert sum(p.pulso.total_vendido_ano for p in parceiros) == pulso.total_vendido_ano


def test_precisao_do_realizado_nao_e_arredondada_por_mes():
    parceiro, = _avaliar(
        _vendas(_venda(mes=1, valor=0.004), _venda(mes=2, valor=0.004)),
        _plano(_meta(mes=1, valor=1), _meta(mes=2, valor=1)),
    )
    assert parceiro.realizado_ytd == Decimal("0.008")
    assert parceiro.atingimento_ytd_pct == Decimal("0.4")
    assert parceiro.saldo_ytd == Decimal("-1.992")


def test_avaliacao_nao_modifica_contratos_fechado_pulso_ou_entradas():
    vendas = _vendas(_venda(valor=70), _venda(mes=11, valor=30))
    plano = _plano(_meta(), _meta(mes=11))
    antes_vendas, antes_plano = vendas.copy(deep=True), plano.copy(deep=True)
    fechado_antes = metas.avaliar_metas(vendas, plano, 2026, data_referencia=REF)
    pulso_antes = metas.avaliar_pulso(vendas, plano, 2026, data_referencia=REF)
    parceiro, = _avaliar(vendas, plano)
    assert metas.avaliar_metas(vendas, plano, 2026, data_referencia=REF) == fechado_antes
    assert metas.avaliar_pulso(vendas, plano, 2026, data_referencia=REF) == pulso_antes
    assert parceiro.pulso == pulso_antes.parceiros[0]
    pd.testing.assert_frame_equal(vendas, antes_vendas)
    pd.testing.assert_frame_equal(plano, antes_plano)
    with pytest.raises(FrozenInstanceError):
        parceiro.saldo_ytd = Decimal(999)


def test_sem_metas_retornam_parceiros_vazios_sem_inventar_entidades():
    assert _avaliar(_vendas(_venda(valor=900)), _plano()) == ()


def test_schema_invalido_e_propagado_sem_classificacao_financeira():
    with pytest.raises(ErroDeMetas):
        _avaliar(_vendas(), _plano(_meta(valor=-1)))


@pytest.mark.parametrize("valor_meta,vendido,esperado", [
    (100, 40, Decimal(40)),
    (100, 0, Decimal(0)),
    (0, 20, None),
])
def test_cobertura_mensal_pulso_usa_base_positiva_sem_inventar_percentual(
    valor_meta, vendido, esperado,
):
    pulso = metas.avaliar_pulso(
        _vendas(_venda(mes=11, valor=vendido)),
        _plano(_meta(mes=11, valor=valor_meta)),
        2026, data_referencia=REF,
    )
    novembro = pulso.meses[10]
    assert novembro.tipo_valor == "ja_vendido"
    assert metas.cobertura_mensal_pulso(novembro) == esperado


@pytest.mark.parametrize("plano", [
    _plano(), _plano(_meta(mes=11, valor=0, ATIVO="NAO")),
])
def test_cobertura_mensal_ausente_ou_inativa_e_indisponivel(plano):
    pulso = metas.avaliar_pulso(
        _vendas(_venda(mes=11, valor=900)), plano, 2026, data_referencia=REF,
    )
    assert metas.cobertura_mensal_pulso(pulso.meses[10]) is None
