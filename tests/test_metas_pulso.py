"""Pulso comercial puro; fixtures sintéticas e nenhum dado da fonte real."""

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


def _venda(mes=1, valor=10, grupo="G", veiculo="V", status="FATURADO", ano=2026, ganho=None):
    return {
        COL_GRUPO: grupo, COL_VEICULO: veiculo, COL_STATUS: status,
        COL_VALOR_LIQUIDO: valor, COL_VALOR_BRUTO: valor * 10,
        COL_MES_VEICULACAO_DATA: f"{ano}-{mes:02d}-01",
        COL_MES_GANHO_DATA: ganho or f"{ano}-{mes:02d}-01",
    }


def _vendas(*linhas):
    df = pd.DataFrame(linhas, columns=list(_venda()))
    for coluna in (COL_MES_VEICULACAO_DATA, COL_MES_GANHO_DATA):
        df[coluna] = pd.to_datetime(df[coluna])
    return df


def _avaliar(vendas, plano, ano=2026, referencia=REF):
    return metas.avaliar_pulso(vendas, plano, ano, data_referencia=referencia)


def _ano_com_carteira():
    plano = _plano(*[_meta(mes=mes) for mes in range(1, 13)])
    vendas = _vendas(
        *[_venda(mes=mes) for mes in range(1, 10)],
        _venda(mes=10, valor=40), _venda(mes=11, valor=50), _venda(mes=12, valor=60),
    )
    return vendas, plano


def test_pulso_reconcilia_fechado_carteira_total_e_indicadores_comerciais():
    vendas, plano = _ano_com_carteira()
    resultado = _avaliar(vendas, plano)
    assert resultado.realizado_meses_encerrados == 90
    assert resultado.carteira_futura == 150
    assert resultado.total_vendido_ano == 240
    assert resultado.total_vendido_ano == (
        resultado.realizado_meses_encerrados + resultado.carteira_futura
    )
    assert resultado.meta_anual == 1200
    assert resultado.meta_restante == 300
    assert resultado.percentual_meta_ja_vendida == 20
    assert resultado.gap_comercial == 960
    assert resultado.necessidade_media_comercial == 320
    assert resultado.cobertura_futura_ja_vendida_pct == 50
    assert resultado.meses_encerrados == 9
    assert resultado.meses_restantes == 3


def test_serie_distingue_realizado_mes_corrente_e_ja_vendido_futuro():
    vendas, plano = _ano_com_carteira()
    resultado = _avaliar(vendas, plano)
    assert [mes.mes for mes in resultado.meses] == list(range(1, 13))
    assert [mes.estado_mes for mes in resultado.meses] == (
        ["encerrado"] * 9 + ["em_andamento", "futuro", "futuro"]
    )
    assert [mes.tipo_valor for mes in resultado.meses] == (
        ["realizado"] * 9 + ["ja_vendido"] * 3
    )
    assert [mes.vendido for mes in resultado.meses[-3:]] == [40, 50, 60]
    assert all(mes.meta == 100 for mes in resultado.meses)
    assert sum(mes.vendido for mes in resultado.meses) == resultado.total_vendido_ano


def test_carteira_respeita_perimetro_de_cada_mes_e_entrada_futura():
    plano = _plano(_meta(mes=10, grupo="A"), _meta(mes=11, grupo="B"))
    resultado = _avaliar(
        _vendas(
            _venda(mes=10, grupo="A", valor=40),
            _venda(mes=11, grupo="A", valor=900),
            _venda(mes=10, grupo="B", valor=800),
            _venda(mes=11, grupo="B", valor=50),
            _venda(mes=12, grupo="A", valor=700),
        ),
        plano,
    )
    assert resultado.carteira_futura == 90
    assert resultado.total_vendido_ano == 90
    assert [mes.vendido for mes in resultado.meses[-3:]] == [40, 50, 0]


def test_brasil247_futuro_inativo_exclui_venda_sem_excluir_historico_ativo():
    plano = _plano(*[
        _meta(
            mes=mes, grupo="BRASIL 247", valor=100 if mes <= 3 else 0,
            ATIVO="SIM" if mes <= 3 else "NAO",
        )
        for mes in range(1, 13)
    ])
    resultado = _avaliar(
        _vendas(_venda(mes=3, grupo="BRASIL 247", valor=70),
                _venda(mes=10, grupo="BRASIL 247", valor=999)),
        plano,
    )
    assert resultado.realizado_meses_encerrados == 70
    assert resultado.carteira_futura == 0
    assert resultado.total_vendido_ano == 70
    assert resultado.meta_anual == 300
    parceiro = resultado.parceiros[0]
    assert parceiro.grupo == "BRASIL 247"
    assert parceiro.total_vendido_ano == 70


@pytest.mark.parametrize("status", sorted(metrics.STATUS_VENDAS))
def test_pulso_inclui_os_seis_status_oficiais_de_venda(status):
    resultado = _avaliar(
        _vendas(_venda(mes=11, valor=17, status=status)), _plano(_meta(mes=11)),
    )
    assert resultado.carteira_futura == 17
    assert resultado.total_vendido_ano == 17


@pytest.mark.parametrize("status", ["CANCELADO", "BONIFICADO", "DESCONHECIDO", ""])
def test_pulso_exclui_status_fora_da_regra_oficial(status):
    resultado = _avaliar(
        _vendas(_venda(mes=11, valor=999, status=status)), _plano(_meta(mes=11)),
    )
    assert resultado.carteira_futura == 0
    assert resultado.total_vendido_ano == 0


def test_pulso_usa_liquido_e_veiculacao_em_vez_de_bruto_ganho_ou_faturamento():
    resultado = _avaliar(
        _vendas(
            _venda(mes=11, valor=25, status="A VEICULAR", ganho="2025-01-01"),
            _venda(mes=1, ano=2027, valor=900, ganho="2026-11-01"),
        ),
        _plano(_meta(mes=11)),
    )
    assert resultado.total_vendido_ano == 25
    assert resultado.carteira_futura == 25


def test_revisao_e_precedencia_grupo_inativo_dominam_veiculo_futuro():
    resultado = _avaliar(
        _vendas(_venda(mes=10, valor=999)),
        _plano(
            _meta(mes=10, valor=100),
            _meta(mes=10, valor=0, ATIVO="NAO", REVISAO=2),
            _meta(mes=10, nivel="VEICULO", veiculo="V", valor=500),
        ),
    )
    assert resultado.carteira_futura == 0
    assert resultado.meta_anual == 0
    assert resultado.percentual_meta_ja_vendida is None
    assert resultado.meses[9].meta == 0
    assert resultado.parceiros[0].meta_anual == 0


def test_meta_de_grupo_nao_e_rateada_por_veiculo_na_tabela_de_parceiros():
    resultado = _avaliar(
        _vendas(_venda(mes=10, veiculo="A", valor=20),
                _venda(mes=10, veiculo="B", valor=30)),
        _plano(_meta(mes=10, valor=100),
               _meta(mes=10, nivel="VEICULO", veiculo="A", valor=999)),
    )
    assert len(resultado.parceiros) == 1
    parceiro = resultado.parceiros[0]
    assert parceiro.grupo == "G"
    assert parceiro.meta_anual == 100
    assert parceiro.total_vendido_ano == 50
    assert parceiro.percentual_meta_ja_vendida == 50
    assert parceiro.gap_comercial == 50


def test_tabela_por_parceiro_soma_veiculos_ativos_sem_confundir_grupos():
    resultado = _avaliar(
        _vendas(
            _venda(mes=10, grupo="A", veiculo="V", valor=20),
            _venda(mes=10, grupo="A", veiculo="W", valor=30),
            _venda(mes=10, grupo="A", veiculo="INATIVO", valor=900),
            _venda(mes=10, grupo="B", veiculo="V", valor=40),
            _venda(mes=10, grupo="B", veiculo="OUTRO", valor=800),
        ),
        _plano(
            _meta(mes=10, grupo="A", nivel="VEICULO", veiculo="V", valor=60),
            _meta(mes=10, grupo="A", nivel="VEICULO", veiculo="W", valor=40),
            _meta(mes=10, grupo="A", nivel="VEICULO", veiculo="INATIVO", valor=0, ATIVO="NAO"),
            _meta(mes=10, grupo="B", nivel="VEICULO", veiculo="V", valor=200),
        ),
    )
    parceiros = {p.grupo: p for p in resultado.parceiros}
    assert set(parceiros) == {"A", "B"}
    assert parceiros["A"].meta_anual == 100
    assert parceiros["A"].total_vendido_ano == 50
    assert parceiros["B"].meta_anual == 200
    assert parceiros["B"].total_vendido_ano == 40
    assert resultado.meta_anual == 300
    assert resultado.total_vendido_ano == 90


def test_tabela_inclui_meta_sem_vendas_e_entidade_inativa_sem_lista_fixa():
    resultado = _avaliar(
        _vendas(),
        _plano(_meta(mes=10, grupo="NOVO PARCEIRO", valor=150),
               _meta(mes=10, grupo="SAIU", valor=0, ATIVO="NAO")),
    )
    parceiros = {p.grupo: p for p in resultado.parceiros}
    assert set(parceiros) == {"NOVO PARCEIRO", "SAIU"}
    assert parceiros["NOVO PARCEIRO"].total_vendido_ano == 0
    assert parceiros["NOVO PARCEIRO"].gap_comercial == 150
    assert parceiros["SAIU"].meta_anual == 0
    assert parceiros["SAIU"].percentual_meta_ja_vendida is None


@pytest.mark.parametrize("valor,meta,status", [
    (40, 100, "abaixo_da_meta"),
    (100, 100, "meta_atingida"),
    (120, 100, "meta_superada"),
    (20, 0, "sem_meta_anual"),
])
def test_status_parceiro_e_deterministico_sem_inferir_atividade(valor, meta, status):
    resultado = _avaliar(
        _vendas(_venda(mes=10, valor=valor)), _plano(_meta(mes=10, valor=meta)),
    )
    assert resultado.parceiros[0].status == status


def test_tabela_parceiro_mantem_fechado_e_ja_vendido_em_colunas_distintas():
    vendas, plano = _ano_com_carteira()
    resultado = _avaliar(vendas, plano)
    parceiro = resultado.parceiros[0]
    assert parceiro.realizado_meses_encerrados == 90
    assert parceiro.ja_vendido_meses_restantes == 150
    assert parceiro.total_vendido_ano == 240
    assert parceiro.meta_anual == 1200
    assert parceiro.percentual_meta_ja_vendida == 20
    assert parceiro.gap_comercial == 960
    assert parceiro.status == "abaixo_da_meta"


def test_perimetro_pode_mudar_de_grupo_para_veiculo_entre_meses_futuros():
    resultado = _avaliar(
        _vendas(_venda(mes=10, veiculo="A", valor=10),
                _venda(mes=10, veiculo="B", valor=20),
                _venda(mes=11, veiculo="A", valor=40),
                _venda(mes=11, veiculo="B", valor=900)),
        _plano(_meta(mes=10, valor=100),
               _meta(mes=11, nivel="VEICULO", veiculo="A", valor=200)),
    )
    assert resultado.carteira_futura == 70
    assert resultado.meta_anual == 300
    assert resultado.meses[9].vendido == 30
    assert resultado.meses[10].vendido == 40
    assert resultado.parceiros[0].meta_anual == 300
    assert resultado.parceiros[0].total_vendido_ano == 70


@pytest.mark.parametrize("alias,canonico", [("Carrega +", "CARREGA+"), ("Rádio Melodia", "MELODIA")])
def test_alias_aplicado_somente_na_camada_metas_sem_fuzzy(alias, canonico):
    vendas = _vendas(_venda(mes=11, grupo=alias, valor=20),
                     _venda(mes=11, grupo=canonico + "+", valor=999))
    plano = _plano(_meta(mes=11, grupo=canonico))
    antes_vendas, antes_plano = vendas.copy(deep=True), plano.copy(deep=True)
    resultado = _avaliar(vendas, plano)
    assert resultado.total_vendido_ano == 20
    assert resultado.parceiros[0].grupo == canonico
    pd.testing.assert_frame_equal(vendas, antes_vendas)
    pd.testing.assert_frame_equal(plano, antes_plano)


def test_zero_ativo_inclui_venda_ausente_e_inativo_excluem_sem_divisao_por_zero():
    resultado = _avaliar(
        _vendas(_venda(mes=10, grupo="ZERO", valor=20),
                _venda(mes=10, grupo="AUSENTE", valor=900),
                _venda(mes=10, grupo="INATIVO", valor=800)),
        _plano(_meta(mes=10, grupo="ZERO", valor=0),
               _meta(mes=10, grupo="INATIVO", valor=0, ATIVO="NAO")),
    )
    assert resultado.carteira_futura == 20
    assert resultado.total_vendido_ano == 20
    assert resultado.meta_anual == 0
    assert resultado.percentual_meta_ja_vendida is None
    assert resultado.cobertura_futura_ja_vendida_pct is None
    assert resultado.gap_comercial == -20


def test_janeiro_tem_pulso_comercial_sem_inventar_realizado_ytd():
    vendas = _vendas(_venda(mes=1, valor=80), _venda(mes=12, valor=100))
    plano = _plano(*[_meta(mes=mes) for mes in range(1, 13)])
    ref = dt.date(2026, 1, 5)
    oficial = metas.avaliar_metas(vendas, plano, 2026, data_referencia=ref)
    resultado = _avaliar(vendas, plano, referencia=ref)
    assert oficial.realizado_ytd == 0
    assert oficial.atingimento_ytd_pct is None
    assert resultado.realizado_meses_encerrados == 0
    assert resultado.carteira_futura == 180
    assert resultado.total_vendido_ano == 180
    assert resultado.percentual_meta_ja_vendida == 15
    assert resultado.necessidade_media_comercial == 85
    assert resultado.cobertura_futura_ja_vendida_pct == 15
    assert resultado.meses[0].estado_mes == "em_andamento"
    assert all(mes.tipo_valor == "ja_vendido" for mes in resultado.meses)


def test_ano_encerrado_nao_tem_carteira_necessidade_ou_cobertura_futura():
    resultado = _avaliar(
        _vendas(_venda(mes=12, ano=2025, valor=200)),
        _plano(_meta(mes=12, ANO=2025, valor=100)),
        ano=2025,
    )
    assert resultado.meses_encerrados == 12
    assert resultado.meses_restantes == 0
    assert resultado.realizado_meses_encerrados == 200
    assert resultado.carteira_futura == 0
    assert resultado.total_vendido_ano == 200
    assert resultado.necessidade_media_comercial is None
    assert resultado.cobertura_futura_ja_vendida_pct is None
    assert all(mes.estado_mes == "encerrado" for mes in resultado.meses)
    assert all(mes.tipo_valor == "realizado" for mes in resultado.meses)


def test_ano_futuro_considera_todos_os_meses_como_ja_vendido_futuro():
    resultado = _avaliar(
        _vendas(_venda(mes=1, ano=2027, valor=20)),
        _plano(_meta(mes=1, ANO=2027, valor=100)),
        ano=2027,
    )
    assert resultado.realizado_meses_encerrados == 0
    assert resultado.carteira_futura == 20
    assert resultado.meses_restantes == 12
    assert all(mes.estado_mes == "futuro" for mes in resultado.meses)
    assert all(mes.tipo_valor == "ja_vendido" for mes in resultado.meses)


def test_meta_superada_mantem_gap_e_necessidade_comercial_com_sinal():
    resultado = _avaliar(
        _vendas(_venda(mes=10, valor=400)), _plano(_meta(mes=10, valor=100)),
    )
    assert resultado.percentual_meta_ja_vendida == 400
    assert resultado.gap_comercial == -300
    assert resultado.necessidade_media_comercial == -100
    assert resultado.cobertura_futura_ja_vendida_pct == 400


def test_ano_sem_meta_nao_inventa_carteira_e_percentual():
    resultado = _avaliar(_vendas(_venda(mes=10, valor=999)), _plano())
    assert resultado.realizado_meses_encerrados == 0
    assert resultado.carteira_futura == 0
    assert resultado.total_vendido_ano == 0
    assert resultado.meta_anual == 0
    assert resultado.percentual_meta_ja_vendida is None
    assert resultado.cobertura_futura_ja_vendida_pct is None
    assert resultado.parceiros == ()


def test_serie_e_parceiros_reconciliam_sem_arredondamento_por_pi_ou_mes():
    plano = _plano(_meta(mes=1, grupo="A", valor=1), _meta(mes=10, grupo="A", valor=1),
                   _meta(mes=10, grupo="B", valor=1))
    vendas = _vendas(_venda(mes=1, grupo="A", valor=0.004),
                     _venda(mes=10, grupo="A", valor=0.004),
                     _venda(mes=10, grupo="B", valor=0.004))
    resultado = _avaliar(vendas, plano)
    assert resultado.realizado_meses_encerrados == Decimal("0.004")
    assert resultado.carteira_futura == Decimal("0.008")
    assert resultado.total_vendido_ano == Decimal("0.012")
    assert sum(mes.vendido for mes in resultado.meses) == Decimal("0.012")
    assert sum(p.total_vendido_ano for p in resultado.parceiros) == Decimal("0.012")
    assert sum(p.meta_anual for p in resultado.parceiros) == resultado.meta_anual


def test_futuras_nao_modificam_qualquer_campo_oficial_ytd_ou_forecast():
    vendas, plano = _ano_com_carteira()
    sem_futuras = vendas.loc[vendas[COL_MES_VEICULACAO_DATA].dt.month <= 9].copy()
    oficial_antes = metas.avaliar_metas(sem_futuras, plano, 2026, data_referencia=REF)
    metas.avaliar_pulso(vendas, plano, 2026, data_referencia=REF)
    oficial_depois = metas.avaliar_metas(vendas, plano, 2026, data_referencia=REF)
    assert oficial_depois == oficial_antes
    assert oficial_depois.atingimento_ytd_pct == 10
    assert oficial_depois.forecast == 120
    assert oficial_depois.necessidade_media == 370


def test_reducao_da_necessidade_comercial_desconta_carteira_futura_uma_vez():
    vendas, plano = _ano_com_carteira()
    oficial = metas.avaliar_metas(vendas, plano, 2026, data_referencia=REF)
    pulso = _avaliar(vendas, plano)
    assert oficial.gap_anual == 1110
    assert pulso.gap_comercial == 960
    assert oficial.necessidade_media == 370
    assert pulso.necessidade_media_comercial == 320
    assert oficial.necessidade_media - pulso.necessidade_media_comercial == (
        pulso.carteira_futura / pulso.meses_restantes
    )


def test_pulso_nao_muta_entradas_e_contratos_sao_congelados():
    vendas, plano = _ano_com_carteira()
    vendas_antes, plano_antes = vendas.copy(deep=True), plano.copy(deep=True)
    resultado = _avaliar(vendas, plano)
    pd.testing.assert_frame_equal(vendas, vendas_antes)
    pd.testing.assert_frame_equal(plano, plano_antes)
    with pytest.raises(FrozenInstanceError):
        resultado.carteira_futura = Decimal(999)
    with pytest.raises(FrozenInstanceError):
        resultado.meses[0].vendido = Decimal(999)
    with pytest.raises(FrozenInstanceError):
        resultado.parceiros[0].gap_comercial = Decimal(999)


def test_pulso_propaga_erro_de_schema_sem_reinterpretar_meta_invalida():
    with pytest.raises(ErroDeMetas):
        _avaliar(_vendas(), _plano(_meta(mes=10, valor=-1)))
