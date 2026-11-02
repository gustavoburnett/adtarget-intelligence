"""Limites monetários com PIs sintéticos; valores brutos não são arredondados."""

from decimal import Decimal, ROUND_HALF_UP

import pytest

from pages_content import metas_resultados as pagina
from src.data import metas, metrics
from tests.test_metas_engine import REF, _meta, _metas, _venda, _vendas


@pytest.mark.parametrize("diferenca,esperado", [
    ("0", "0"),
    ("-0.000000000003", "0"),
    ("0.000000000006", "0"),
    ("-0.004999", "0"),
    ("0.004999", "0"),
    ("-0.005", "-0.005"),
    ("0.005", "0.005"),
    ("-0.01", "-0.01"),
    ("0.01", "0.01"),
    ("-1.992", "-1.992"),
])
def test_fronteira_de_zero_e_monetaria_sem_arredondar_diferencas_reais(
    diferenca, esperado,
):
    referencia = Decimal("90000000000.12")
    atual = referencia + Decimal(diferenca)
    assert metas.diferenca_monetaria(atual, referencia) == Decimal(esperado)


def _avaliar(pis, meta):
    vendas = _vendas(*[_venda(valor=valor) for valor in pis])
    plano = _metas(_meta(valor=meta), _meta(mes=3, valor=0))
    fechado = metas.avaliar_metas(vendas, plano, 2026, data_referencia=REF)
    pulso = metas.avaliar_pulso(vendas, plano, 2026, data_referencia=REF)
    parceiro, = metas.avaliar_parceiros(vendas, plano, 2026, data_referencia=REF)
    return vendas, plano, fechado, pulso, parceiro


@pytest.mark.parametrize("pis,meta", [
    ([10000.10, 20000.10], 30000.20),
    ([10000.10, 20000.20, 30000.30], 60000.60),
])
def test_cem_por_cento_economico_preserva_residuo_bruto_sem_saldo_fantasma(pis, meta):
    vendas, _, fechado, pulso, parceiro = _avaliar(pis, meta)
    bruto = Decimal(str(metrics.vendas(vendas, "liquido")))
    assert bruto != Decimal(str(meta))  # Os dois sinais do defeito reproduzido.
    assert fechado.realizado_ytd == bruto
    assert fechado.meses[0].realizado == bruto
    assert fechado.meses[1].realizado_acumulado == bruto
    assert pulso.total_vendido_ano == bruto
    assert parceiro.realizado_ytd == bruto
    assert fechado.atingimento_ytd_pct == bruto / fechado.meta_ytd * 100
    assert pulso.percentual_meta_ja_vendida == bruto / pulso.meta_anual * 100
    assert fechado.forecast == bruto / 2 * 12
    assert fechado.saldo_ytd == fechado.meses[0].saldo == Decimal(0)
    assert fechado.meses[1].saldo_acumulado == Decimal(0)
    assert fechado.gap_anual == pulso.gap_comercial == Decimal(0)
    assert parceiro.saldo_ytd == parceiro.pulso.gap_comercial == Decimal(0)
    assert fechado.necessidade_media == pulso.necessidade_media_comercial == Decimal(0)
    assert fechado.cobertura_plano_pct is None
    assert parceiro.status == "acima_da_meta"
    assert parceiro.pulso.status == "meta_atingida"


@pytest.mark.parametrize("segundo,sinal,status_ytd,status_anual", [
    (20000.09, -1, "proximo_da_meta", "abaixo_da_meta"),
    (20000.11, 1, "acima_da_meta", "meta_superada"),
])
def test_um_centavo_real_abaixo_ou_acima_de_cem_nao_e_absorvido(
    segundo, sinal, status_ytd, status_anual,
):
    _, _, fechado, pulso, parceiro = _avaliar([10000.10, segundo], 30000.20)
    saldo_bruto = fechado.realizado_ytd - fechado.meta_ytd
    assert fechado.saldo_ytd == saldo_bruto
    assert fechado.saldo_ytd * sinal > 0
    assert abs(saldo_bruto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == Decimal("0.01")
    assert fechado.gap_anual == -saldo_bruto
    assert pulso.gap_comercial == -saldo_bruto
    assert parceiro.status == status_ytd
    assert parceiro.pulso.status == status_anual


@pytest.mark.parametrize("segundo,status", [
    (17000.25, "abaixo_da_meta"),
    (17000.26, "proximo_da_meta"),
    (17000.27, "proximo_da_meta"),
])
def test_noventa_por_cento_com_multiplos_pis_respeita_centavo_real(segundo, status):
    _, _, fechado, _, parceiro = _avaliar([10000.01, segundo], 30000.30)
    assert parceiro.status == status
    assert parceiro.realizado_ytd == fechado.realizado_ytd
    assert parceiro.atingimento_ytd_pct == fechado.atingimento_ytd_pct
    if segundo == 17000.26:
        assert parceiro.atingimento_ytd_pct < 90  # Ruído bruto continua auditável.
        assert metas.diferenca_monetaria(
            parceiro.realizado_ytd, parceiro.meta_ytd * Decimal("0.9"),
        ) == 0


@pytest.mark.parametrize("pis,meta", [
    ([10000.10, 20000.10], 30000.20),
    ([10000.10, 20000.20, 30000.30], 60000.60),
])
def test_apresentacao_cem_e_gap_zero_nao_mostra_deficit_ou_superavit_fantasma(pis, meta):
    _, plano, fechado, pulso, parceiro = _avaliar(pis, meta)
    hero = pagina._hero(fechado)
    anual = pagina._meta_anual(pulso)
    projecao = pagina._projecao(fechado, pulso)
    parceiros = pagina._parceiros(
        (parceiro,), pulso, fechado, metas.vigencia(plano, data_referencia=REF),
    )
    assert "100,0%" in hero
    assert "Saldo YTD" in hero
    assert "Déficit YTD" not in hero and "Superávit YTD" not in hero
    assert "Meta anual atingida" in anual
    assert "ainda precisam ser vendidos" not in anual
    assert "Meta superada em" not in anual
    assert "Meta anual já atingida" in projecao
    assert "Meta anual já superada" not in projecao
    assert "ainda precisamos conquistar" not in projecao
    assert "✓ Acima do ritmo" in parceiros
    assert "Déficit YTD" not in parceiros and "Superávit YTD" not in parceiros
    assert "Meta anual superada em" not in parceiros


def test_gap_zero_nao_produz_cobertura_astronomica_com_plano_futuro_positivo():
    vendas = _vendas(_venda(valor=10000.10), _venda(valor=20000.10))
    plano = _metas(_meta(valor=15000.10), _meta(mes=10, valor=15000.10))
    fechado = metas.avaliar_metas(vendas, plano, 2026, data_referencia=REF)
    pulso = metas.avaliar_pulso(vendas, plano, 2026, data_referencia=REF)
    assert fechado.plano_futuro == Decimal("15000.10")
    assert fechado.gap_anual == pulso.gap_comercial == 0
    assert fechado.cobertura_plano_pct is None
    assert fechado.necessidade_media == pulso.necessidade_media_comercial == 0
    assert fechado.saldo_ytd == fechado.realizado_ytd - fechado.meta_ytd


def test_pis_e_meses_subcentavo_acumulam_sem_normalizacao_prematura():
    vendas = _vendas(
        _venda(valor=0.0042), _venda(mes="2026-02-01", valor=0.0039),
        _venda(mes="2026-03-01", valor=0.004),
        _venda(mes="2026-04-01", valor=0.008),
    )
    plano = _metas(*[_meta(mes=mes, valor=1) for mes in range(1, 13)])
    fechado = metas.avaliar_metas(vendas, plano, 2026, data_referencia=REF)
    pulso = metas.avaliar_pulso(vendas, plano, 2026, data_referencia=REF)
    assert fechado.meses[0].realizado == Decimal("0.0042")
    assert fechado.meses[1].realizado == Decimal("0.0039")
    assert fechado.realizado_ytd == Decimal("0.0081")
    assert pulso.carteira_futura == Decimal("0.012")
    assert pulso.total_vendido_ano == Decimal("0.0201")
    assert fechado.saldo_ytd == Decimal("-1.9919")
    assert fechado.forecast == Decimal("0.0486")


@pytest.mark.parametrize("ajuste,status", [
    (-0.01, "abaixo_da_meta"),
    (0, "meta_atingida"),
    (0.01, "meta_superada"),
])
def test_valores_grandes_fracionarios_preservam_precision_material(ajuste, status):
    vendas, _, fechado, pulso, parceiro = _avaliar(
        [10000000.10, 20000000.10 + ajuste], 30000000.20,
    )
    bruto = Decimal(str(metrics.vendas(vendas, "liquido")))
    assert fechado.realizado_ytd == pulso.total_vendido_ano == bruto
    assert fechado.realizado_ytd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == (
        Decimal("30000000.20") + Decimal(str(ajuste))
    )
    assert parceiro.pulso.status == status
    if ajuste:
        assert pulso.gap_comercial == pulso.meta_anual - bruto
    else:
        assert pulso.gap_comercial == 0
