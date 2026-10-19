"""Contratos comerciais do novo recorte mensal; dados inteiramente sintéticos."""

import datetime as dt
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pandas as pd
import pytest

from src.components.monthly_groups_data import (
    contribuicoes_grupo,
    grupos_disponiveis,
    preparar_grupo,
)
from src.data import metas as engine
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

REF = dt.date(2026, 10, 19)


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


def _preparar(vendas, plano, grupo="G", ano=2026, referencia=REF):
    return preparar_grupo(vendas, plano, ano, grupo, data_referencia=referencia)


def test_seletor_unifica_metas_inativas_e_vendas_elegiveis_do_ano():
    vendas = _vendas(
        _venda(grupo="SISTEMA VERDES MARES"),
        _venda(grupo="CARREGA +"),
        _venda(grupo="CARREGA+"),
        _venda(grupo="CANCELADO", status="CANCELADO"),
        _venda(grupo="BONIFICADO", status="BONIFICADO"),
        _venda(grupo="OUTRO ANO", ano=2025),
        _venda(grupo=""),
    )
    plano = _plano(
        _meta(grupo="BRASIL 247", valor=0, ATIVO="NAO"),
        _meta(grupo="FORBES"),
        _meta(grupo="META OUTRO ANO", ANO=2025),
    )
    assert grupos_disponiveis(vendas, plano, 2026, data_referencia=REF) == (
        "BRASIL 247", "CARREGA+", "FORBES", "SISTEMA VERDES MARES",
    )


def test_reconciliacao_mensal_usa_contratos_originais_e_separa_carteira():
    vendas = _vendas(
        _venda(valor=70), _venda(mes=9, valor=20),
        _venda(mes=10, valor=500), _venda(mes=12, valor=50),
        _venda(grupo="OUTRO", valor=9999),
    )
    plano = _plano(*(_meta(mes=mes) for mes in range(1, 13)))
    grupo = _preparar(vendas, plano)
    assert grupo.resultado == engine.avaliar_metas(vendas, plano, 2026, data_referencia=REF)
    assert grupo.pulso == engine.avaliar_pulso(vendas, plano, 2026, data_referencia=REF)
    assert grupo.parceiro == engine.avaliar_parceiros(vendas, plano, 2026, data_referencia=REF)[0]
    assert grupo.realizado_ytd == 90
    assert grupo.carteira_futura == 550
    assert grupo.total_vendido_ano == 640
    assert grupo.meta_anual == 1200
    assert grupo.gap_comercial == 560
    assert sum((m.vendido for m in grupo.meses), Decimal(0)) == grupo.total_vendido_ano
    assert grupo.parceiro.status == "abaixo_da_meta"
    assert grupo.meses[9].atingimento_pct == 500
    assert grupo.meses[9].estado_mes == "em_andamento"
    assert grupo.meses[11].estado_mes == "futuro"


@pytest.mark.parametrize("status", [
    "A VEICULAR", "EM VEICULAÇÃO", "CHECKING", "AGUARD. DOC. VEÍCULO", "FATURADO", "DIRETO",
])
def test_preserva_status_oficial_e_valor_liquido_por_veiculacao(status):
    grupo = _preparar(_vendas(_venda(status=status, valor=30)), _plano(_meta()))
    assert grupo.total_vendido_ano == 30
    assert grupo.meses[0].vendido == 30
    assert grupo.meses[0].atingimento_pct == 30
    assert grupo.meses[0].desvio == -70


@pytest.mark.parametrize("status", ["CANCELADO", "BONIFICADO", "DESCONHECIDO"])
def test_status_inelegivel_nao_vira_registro_nem_atingimento(status):
    grupo = _preparar(_vendas(_venda(status=status)), _plano(_meta()))
    assert grupo.meses[0].registros == 0
    assert grupo.meses[0].vendido == 0
    assert grupo.meses[0].atingimento_pct is None
    assert grupo.meses[0].desvio is None


def test_mes_sem_registros_omite_comparativos_sem_alterar_ytd_engine():
    grupo = _preparar(_vendas(), _plano(_meta()))
    mes = grupo.meses[0]
    assert mes.meta == 100
    assert mes.vendido == 0
    assert mes.atingimento_pct is None
    assert mes.desvio is None
    assert grupo.resultado.atingimento_ytd_pct == 0
    assert grupo.resultado.saldo_ytd == -100
    assert grupo.parceiro.status == "abaixo_da_meta"


def test_registro_zero_explicito_difere_de_ausencia_de_registros():
    grupo = _preparar(_vendas(_venda(valor=0)), _plano(_meta()))
    assert grupo.meses[0].registros == 1
    assert grupo.meses[0].atingimento_pct == 0
    assert grupo.meses[0].desvio == -100
    assert grupo.meses[0].veiculos[0].valor == 0
    assert grupo.meses[0].veiculos[0].percentual is None


def test_meta_zero_ativa_preserva_vendas_sem_divisao_ou_meta_inventada():
    grupo = _preparar(_vendas(_venda(valor=20)), _plano(_meta(valor=0)))
    assert grupo.tem_metas
    assert grupo.meses[0].estado_meta == "zero_ativa"
    assert grupo.meses[0].meta == 0
    assert grupo.meses[0].vendido == 20
    assert grupo.meses[0].atingimento_pct is None
    assert grupo.meses[0].desvio == 20
    assert grupo.meta_anual == 0
    assert grupo.gap_comercial is None


def test_brasil247_nao_importa_vendas_depois_da_vigencia_nem_oculta_fora():
    grupo = _preparar(
        _vendas(_venda(mes=3, valor=70, grupo="BRASIL 247"),
                _venda(mes=4, valor=900, grupo="BRASIL 247"),
                _venda(mes=10, valor=800, grupo="BRASIL 247")),
        _plano(_meta(mes=3, grupo="BRASIL 247"),
               _meta(mes=4, grupo="BRASIL 247", valor=0, ATIVO="NAO"),
               _meta(mes=10, grupo="BRASIL 247", valor=0, ATIVO="NAO")),
        grupo="BRASIL 247",
    )
    assert grupo.total_vendido_ano == 70
    assert grupo.realizado_ytd == 70
    assert grupo.carteira_futura == 0
    assert grupo.fora_perimetro_anual == 1700
    assert grupo.meses[3].estado_meta == "inativa"
    assert grupo.meses[3].meta is None
    assert grupo.meses[3].vendido == 0
    assert grupo.meses[3].fora_perimetro == 900
    assert grupo.meses[9].fora_perimetro == 800
    assert grupo.meses[3].atingimento_pct is None
    assert grupo.meses[3].desvio is None
    assert grupo.contribuicoes[0].valor == 70


def test_mes_ausente_em_grupo_com_metas_fica_fora_do_perimetro():
    grupo = _preparar(
        _vendas(_venda(valor=20), _venda(mes=2, valor=80)), _plano(_meta()),
    )
    assert grupo.total_vendido_ano == 20
    assert grupo.meses[1].estado_meta == "ausente"
    assert grupo.meses[1].meta is None
    assert grupo.meses[1].fora_perimetro == 80
    assert grupo.meses[1].atingimento_pct is None
    assert grupo.meses[1].desvio is None


def test_sem_meta_anual_mostra_vendas_integrais_sem_gap_ou_percentuais():
    grupo = _preparar(
        _vendas(_venda(grupo="SISTEMA VERDES MARES", valor=40),
                _venda(grupo="SISTEMA VERDES MARES", mes=10, valor=80)),
        _plano(_meta(grupo="OUTRO")), grupo="SISTEMA VERDES MARES",
    )
    assert not grupo.tem_metas
    assert grupo.parceiro is None
    assert grupo.meta_anual is None
    assert grupo.gap_comercial is None
    assert grupo.realizado_ytd == 40
    assert grupo.carteira_futura == 80
    assert grupo.total_vendido_ano == 120
    assert grupo.fora_perimetro_anual == 0
    assert all(m.meta is None and m.atingimento_pct is None and m.desvio is None for m in grupo.meses)
    assert grupo.contribuicoes[0].valor == 120


def test_meta_somente_em_outro_ano_nao_fabrica_meta_para_selecao():
    grupo = _preparar(_vendas(_venda(valor=30)), _plano(_meta(ANO=2025)))
    assert not grupo.tem_metas
    assert grupo.meta_anual is None
    assert grupo.total_vendido_ano == 30


def test_disney_contribuicoes_por_veiculo_nao_rateiam_meta_do_grupo():
    grupo = _preparar(
        _vendas(_venda(grupo="DISNEY", veiculo="DISNEY+", valor=60),
                _venda(grupo="DISNEY", veiculo="ESPN", valor=40),
                _venda(grupo="DISNEY", veiculo="ESPN", mes=10, valor=100),
                _venda(grupo="OUTRO", veiculo="ESPN", valor=999)),
        _plano(_meta(grupo="DISNEY", valor=200),
               _meta(grupo="DISNEY", mes=10, valor=200)), grupo="DISNEY",
    )
    assert grupo.meta_anual == 400
    assert [(v.veiculo, v.valor, v.percentual) for v in grupo.contribuicoes] == [
        ("ESPN", Decimal(140), Decimal(70)),
        ("DISNEY+", Decimal(60), Decimal(30)),
    ]
    assert [(v.veiculo, v.valor) for v in contribuicoes_grupo(grupo, 1)] == [
        ("DISNEY+", Decimal(60)), ("ESPN", Decimal(40)),
    ]
    assert contribuicoes_grupo(grupo) == grupo.contribuicoes
    assert not hasattr(grupo.contribuicoes[0], "meta")


def test_precedencia_grupo_inativo_domina_meta_de_veiculo_ativa():
    grupo = _preparar(
        _vendas(_venda(valor=30)),
        _plano(_meta(valor=0, ATIVO="NAO"),
               _meta(valor=100, veiculo="V", nivel="VEICULO")),
    )
    assert grupo.meses[0].estado_meta == "inativa"
    assert grupo.meses[0].vendido == 0
    assert grupo.meses[0].fora_perimetro == 30
    assert grupo.meses[0].veiculos == ()


def test_meta_veiculo_respeita_par_comercial_mesmo_com_indices_duplicados():
    vendas = _vendas(_venda(veiculo="V", valor=30), _venda(veiculo="W", valor=80))
    vendas.index = [0, 0]
    grupo = _preparar(vendas, _plano(_meta(veiculo="V", nivel="VEICULO")))
    assert grupo.meses[0].vendido == 30
    assert grupo.meses[0].fora_perimetro == 80
    assert grupo.meses[0].registros == 1
    assert grupo.contribuicoes[0].veiculo == "V"


def test_perimetro_soma_metas_de_veiculos_sem_fabricar_meta_do_grupo():
    grupo = _preparar(
        _vendas(_venda(veiculo="V1", valor=30), _venda(veiculo="V2", valor=60),
                _venda(veiculo="SEM META", valor=500)),
        _plano(_meta(valor=100, veiculo="V1", nivel="VEICULO"),
               _meta(valor=200, veiculo="V2", nivel="VEICULO")),
    )
    assert grupo.meses[0].meta == 300
    assert grupo.meses[0].vendido == 90
    assert grupo.meses[0].atingimento_pct == 30
    assert grupo.meses[0].fora_perimetro == 500
    assert grupo.total_vendido_ano == 90
    assert [v.veiculo for v in grupo.contribuicoes] == ["V2", "V1"]


def test_revisao_mais_alta_vigente_nao_e_escolhida_pelo_timestamp():
    grupo = _preparar(
        _vendas(_venda(valor=30)),
        _plano(_meta(valor=100, CRIADO_EM="2026-02-01T00:00:00-03:00"),
               _meta(valor=200, REVISAO=2, CRIADO_EM="2026-01-01T00:00:00-03:00")),
    )
    assert grupo.meses[0].meta == 200
    assert grupo.meses[0].atingimento_pct == 15


@pytest.mark.parametrize("origem,canonico", [
    ("CARREGA +", "CARREGA+"), ("RÁDIO MELODIA", "MELODIA"),
])
def test_aplica_somente_alias_aprovado_em_copias(origem, canonico):
    grupo = _preparar(
        _vendas(_venda(grupo=origem, valor=30)),
        _plano(_meta(grupo=canonico)), grupo=origem,
    )
    assert grupo.grupo == canonico
    assert grupo.total_vendido_ano == 30


def test_nao_cria_alias_entre_carrega_e_carrega_mais():
    grupo = _preparar(
        _vendas(_venda(grupo="CARREGA", valor=30)),
        _plano(_meta(grupo="CARREGA+")), grupo="CARREGA+",
    )
    assert grupo.total_vendido_ano == 0
    assert grupo.meses[0].registros == 0


@pytest.mark.parametrize("ano,fechados,carteira", [(2025, 12, 0), (2026, 9, 30), (2027, 0, 30)])
def test_anos_historico_atual_e_futuro_reutilizam_fechamento_existente(ano, fechados, carteira):
    grupo = _preparar(
        _vendas(_venda(mes=10, ano=ano, valor=30)),
        _plano(_meta(mes=10, ANO=ano)), ano=ano,
    )
    assert grupo.resultado.meses_encerrados == fechados
    assert grupo.carteira_futura == carteira
    assert grupo.total_vendido_ano == 30


def test_referencia_timezone_preserva_fechamento_calendario_sao_paulo():
    referencia = dt.datetime(2026, 10, 1, 1, 0, tzinfo=dt.timezone.utc)
    grupo = _preparar(
        _vendas(_venda(mes=9, valor=30)), _plano(_meta(mes=9)),
        referencia=referencia,
    )
    assert grupo.resultado.data_referencia == dt.date(2026, 9, 30)
    assert grupo.meses[8].estado_mes == "em_andamento"
    assert grupo.realizado_ytd == 0
    assert grupo.carteira_futura == 30


def test_grupo_sem_metas_nem_vendas_preserva_estados_vazios():
    grupo = _preparar(_vendas(), _plano())
    assert grupo.total_vendido_ano == 0
    assert grupo.realizado_ytd == 0
    assert grupo.carteira_futura == 0
    assert grupo.contribuicoes == ()
    assert grupos_disponiveis(_vendas(), _plano(), 2026, data_referencia=REF) == ()


def test_conserva_precisao_original_sem_arredondamento_por_registro():
    grupo = _preparar(
        _vendas(*(_venda(valor=0.0049, veiculo=f"V{i % 3}") for i in range(17)),
                _venda(mes=10, valor=0.0317)),
        _plano(_meta(valor=1), _meta(mes=10, valor=1)),
    )
    assert grupo.total_vendido_ano > Decimal("0.11")
    assert grupo.total_vendido_ano < Decimal("0.12")
    soma_veiculos = sum((v.valor for v in grupo.contribuicoes), Decimal(0))
    assert abs(soma_veiculos - grupo.total_vendido_ano) < Decimal("0.000000001")


def test_nao_muta_fontes_e_snapshot_e_imutavel():
    vendas = _vendas(_venda(grupo="RÁDIO MELODIA", veiculo="v", valor=30))
    plano = _plano(_meta(grupo="MELODIA"))
    vendas_antes, plano_antes = vendas.copy(deep=True), plano.copy(deep=True)
    grupo = _preparar(vendas, plano, grupo="MELODIA")
    grupos_disponiveis(vendas, plano, 2026, data_referencia=REF)
    pd.testing.assert_frame_equal(vendas, vendas_antes)
    pd.testing.assert_frame_equal(plano, plano_antes)
    with pytest.raises(FrozenInstanceError):
        grupo.grupo = "OUTRO"


@pytest.mark.parametrize("mes", [0, 13, True, "1"])
def test_contribuicoes_rejeita_mes_invalido(mes):
    grupo = _preparar(_vendas(), _plano())
    with pytest.raises(ValueError):
        contribuicoes_grupo(grupo, mes)


def test_schema_invalido_nao_e_ocultado_pelo_filtro_de_grupo():
    with pytest.raises(ErroDeMetas):
        _preparar(_vendas(), _plano(_meta(grupo="OUTRO", valor=-1)))


@pytest.mark.parametrize("grupo", ["", "  ", None])
def test_grupo_vazio_rejeitado_sem_acessar_fonte(grupo):
    with pytest.raises(ValueError):
        _preparar(_vendas(), _plano(), grupo=grupo)
