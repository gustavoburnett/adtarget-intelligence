"""Semântica de apresentação e ranking dinâmico; somente dados sintéticos."""

import datetime as dt
import re
from decimal import Decimal
from html.parser import HTMLParser

import pandas as pd
import pytest

from pages_content import metas_resultados as pagina
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
from src.data.metas_schema import COLUNAS_METAS

REF = dt.date(2026, 10, 6)


def _meta(mes=1, valor=100, grupo="G", veiculo="", nivel="GRUPO", **extras):
    registro = {
        "NIVEL_META": nivel, "GRUPO": grupo, "VEICULO": veiculo,
        "ANO": 2026, "MES": mes, "VALOR_META": valor, "ATIVO": "SIM",
        "REVISAO": 1, "CRIADO_EM": "2026-01-01T00:00:00-03:00", "MOTIVO": "Teste",
    }
    registro.update(extras)
    return registro


def _plano(*registros):
    return pd.DataFrame(registros, columns=COLUNAS_METAS)


def _venda(mes=1, valor=10, grupo="G", veiculo="V", ano=2026):
    return {
        COL_GRUPO: grupo, COL_VEICULO: veiculo, COL_STATUS: "FATURADO",
        COL_VALOR_LIQUIDO: valor, COL_VALOR_BRUTO: valor * 10,
        COL_MES_VEICULACAO_DATA: f"{ano}-{mes:02d}-01",
        COL_MES_GANHO_DATA: f"{ano}-{mes:02d}-01",
    }


def _vendas(*registros):
    df = pd.DataFrame(registros, columns=list(_venda()))
    for coluna in (COL_MES_VEICULACAO_DATA, COL_MES_GANHO_DATA):
        df[coluna] = pd.to_datetime(df[coluna])
    return df


def _avaliar(plano, vendas=None, *, ano=2026, referencia=REF):
    base = _vendas() if vendas is None else vendas
    fechado = metas.avaliar_metas(base, plano, ano, data_referencia=referencia)
    pulso = metas.avaliar_pulso(base, plano, ano, data_referencia=referencia)
    parceiros = metas.avaliar_parceiros(base, plano, ano, data_referencia=referencia)
    vigentes = metas.vigencia(plano, data_referencia=referencia)
    return fechado, pulso, parceiros, vigentes


def _atividade(grupo, plano, *, ano=2026, referencia=REF, com_fonte=True):
    fechado, _, _, vigentes = _avaliar(plano, ano=ano, referencia=referencia)
    return pagina._atividade_parceiro(
        grupo, fechado, vigentes if com_fonte else None,
    )


def _html(plano, vendas=None, *, ano=2026, referencia=REF):
    fechado, pulso, parceiros, vigentes = _avaliar(
        plano, vendas, ano=ano, referencia=referencia,
    )
    return pagina._parceiros(parceiros, pulso, fechado, vigentes)


def _artigo(html, grupo):
    return re.search(
        r'<article\b[^>]*aria-label="' + re.escape(grupo) + r'".*?</article>',
        html, re.DOTALL,
    ).group()


class _Atributos(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elementos = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elementos.append((tag, dict(attrs)))


def test_meta_zero_ativa_pertence_a_operacao_atual():
    ativo, contexto = _atividade("G", _plano(_meta(mes=10, valor=0)))
    assert ativo is True
    assert contexto is None


def test_entrada_futura_nao_e_classificada_como_operacao_encerrada():
    ativo, contexto = _atividade("HYPR", _plano(_meta(mes=11, grupo="HYPR")))
    assert ativo is True
    assert contexto == "Meta ativa a partir de Nov/2026"


def test_inativo_no_mes_atual_com_retorno_futuro_preserva_entrada_programada():
    ativo, contexto = _atividade("G", _plano(
        _meta(mes=10, valor=0, ATIVO="NAO"), _meta(mes=11),
    ))
    assert ativo is True
    assert contexto == "Meta ativa a partir de Nov/2026"


def test_encerramento_explicito_na_fonte_preserva_ultimo_mes_ativo():
    plano = _plano(*[_meta(mes=mes) for mes in (1, 2, 3)],
                   _meta(mes=10, valor=0, ATIVO="NAO"))
    ativo, contexto = _atividade("G", plano)
    assert ativo is False
    assert contexto == "Operação encerrada em Mar/2026"


@pytest.mark.parametrize("com_fonte", [True, False])
def test_ausencia_de_meta_atual_nao_inventa_encerramento_da_operacao(com_fonte):
    ativo, contexto = _atividade("G", _plano(_meta(mes=3)), com_fonte=com_fonte)
    assert ativo is False
    assert contexto == "Última meta ativa: Mar/2026"


def test_grupo_inativo_domina_veiculo_ativo_tambem_na_classificacao_visual():
    ativo, contexto = _atividade("G", _plano(
        _meta(mes=3), _meta(mes=10, valor=0, ATIVO="NAO"),
        _meta(mes=10, nivel="VEICULO", veiculo="V", valor=999),
    ))
    assert ativo is False
    assert contexto == "Operação encerrada em Mar/2026"


def test_um_veiculo_ativo_suficiente_mantem_grupo_no_ranking_ativo():
    ativo, contexto = _atividade("G", _plano(
        _meta(mes=10, nivel="VEICULO", veiculo="A", valor=0, ATIVO="NAO"),
        _meta(mes=10, nivel="VEICULO", veiculo="B", valor=0),
    ))
    assert ativo is True
    assert contexto is None


def test_todos_veiculos_inativos_confirmam_encerramento_sem_ratear_grupo():
    ativo, contexto = _atividade("G", _plano(
        _meta(mes=3, nivel="VEICULO", veiculo="A"),
        _meta(mes=10, nivel="VEICULO", veiculo="A", valor=0, ATIVO="NAO"),
        _meta(mes=10, nivel="VEICULO", veiculo="B", valor=0, ATIVO="NAO"),
    ))
    assert ativo is False
    assert contexto == "Operação encerrada em Mar/2026"


def test_sem_perimetro_ativo_no_ano_nao_inventa_historia_operacional():
    ativo, contexto = _atividade("G", _plano(_meta(mes=10, valor=0, ATIVO="NAO")))
    assert ativo is False
    assert contexto == "Sem meta ativa no ano"
    assert "encerrada" not in contexto


def test_ano_encerrado_toma_dezembro_como_referencia_de_atividade():
    ativo, contexto = _atividade("G", _plano(
        _meta(mes=11, ANO=2025),
        _meta(mes=12, ANO=2025, valor=0, ATIVO="NAO"),
    ), ano=2025)
    assert ativo is False
    assert contexto == "Operação encerrada em Nov/2025"


def test_ano_futuro_usa_primeiro_mes_planejado_sem_confundir_com_encerramento():
    ativo, contexto = _atividade("HYPR", _plano(_meta(mes=4, ANO=2027, grupo="HYPR")), ano=2027)
    assert ativo is True
    assert contexto == "Meta ativa a partir de Abr/2027"


def test_ranking_dinamico_separa_inativo_preserva_historia_e_inclui_hypr():
    plano = _plano(*[
        _meta(mes=mes, grupo=grupo)
        for grupo in ("TEADS", "HYPR", "FORBES") for mes in (1, 10)
    ], _meta(mes=3, grupo="BRASIL 247"),
        _meta(mes=10, grupo="BRASIL 247", valor=0, ATIVO="NAO"))
    html = _html(plano, _vendas(
        _venda(grupo="TEADS", valor=123), _venda(grupo="HYPR", valor=95),
        _venda(mes=3, grupo="BRASIL 247", valor=10),
    ))
    assert "Parceiros ativos" in html and "Parceiros fora da operação" in html
    assert html.index('aria-label="TEADS"') < html.index('aria-label="HYPR"')
    assert html.index('aria-label="HYPR"') < html.index('aria-label="FORBES"')
    assert html.index("Parceiros fora da operação") < html.index('aria-label="BRASIL 247"')
    inativo = _artigo(html, "BRASIL 247")
    assert "Operação encerrada em Mar/2026" in inativo
    assert "Compromisso anual e saldo" in inativo
    assert 'title="R$ 10,00"' in inativo
    status = re.search(r'class="[^"]*atg-metas-partner-status[^"]*"', inativo).group()
    assert "atg-metas-negative" not in status


def test_forbes_zero_continua_acionavel_com_meta_e_status_de_ritmo():
    html = _html(_plano(_meta(grupo="FORBES"), _meta(mes=10, grupo="FORBES")))
    artigo = _artigo(html, "FORBES")
    assert "0,0%" in artigo
    assert "Abaixo do ritmo" in artigo
    assert "Realizado zero no período" in artigo
    assert "atg-metas-negative" in artigo
    assert "Operação encerrada" not in artigo


@pytest.mark.parametrize("valor,rotulo", [
    (122.3, "Acima do ritmo"), (95, "No ritmo"), (74, "Abaixo do ritmo"),
])
def test_status_visual_troca_so_redacao_sem_alterar_atingimento(valor, rotulo):
    plano = _plano(_meta(), _meta(mes=10))
    vendas = _vendas(_venda(valor=valor))
    fechado, pulso, parceiros, vigentes = _avaliar(plano, vendas)
    antes = parceiros
    html = pagina._parceiros(parceiros, pulso, fechado, vigentes)
    assert rotulo in html
    assert "Acima da meta" not in html
    assert "Próximo da meta" not in html
    assert "Abaixo da meta" not in html
    assert parceiros == antes
    assert parceiros[0].atingimento_ytd_pct == Decimal(str(valor))


def test_escala_comum_preserva_percentual_real_e_referencia_100():
    plano = _plano(*[
        _meta(mes=mes, grupo=grupo)
        for grupo in ("TEADS", "DISNEY") for mes in (1, 10)
    ])
    html = _html(plano, _vendas(
        _venda(grupo="TEADS", valor=122.3), _venda(grupo="DISNEY", valor=74),
    ))
    atributos = [attrs for _, attrs in _Atributos(html).elementos if "data-pct-ytd" in attrs]
    assert len(atributos) == 2
    assert {Decimal(attrs["data-scale-max"]) for attrs in atributos} == {Decimal(125)}
    assert {Decimal(attrs["data-pct-ytd"]) for attrs in atributos} == {Decimal("122.3"), Decimal(74)}
    assert "122,3%" in _artigo(html, "TEADS") and "74,0%" in _artigo(html, "DISNEY")
    assert "100%" in html
    larguras = {
        grupo: Decimal(re.search(r'atg-metas-progress-fill" style="width:([0-9.]+)%', _artigo(html, grupo)).group(1))
        for grupo in ("TEADS", "DISNEY")
    }
    assert larguras == {"TEADS": Decimal("97.84"), "DISNEY": Decimal("59.20")}
    assert larguras["TEADS"] > 80 > larguras["DISNEY"]
    assert re.search(r'\.atg-metas-progress-reference\s*\{[^}]*left:80%', pagina._CSS)


def test_percentual_extremo_so_limita_geometria_nao_dado_nem_rotulo():
    plano = _plano(_meta(), _meta(mes=10))
    vendas = _vendas(_venda(valor=400))
    fechado, pulso, parceiros, vigentes = _avaliar(plano, vendas)
    html = pagina._parceiros(parceiros, pulso, fechado, vigentes)
    assert "400,0%" in html
    assert parceiros[0].atingimento_ytd_pct == 400
    atributos = [attrs for _, attrs in _Atributos(html).elementos if "data-pct-ytd" in attrs]
    assert Decimal(atributos[0]["data-pct-ytd"]) == 400
    assert Decimal(atributos[0]["data-scale-max"]) == 125


def test_apresentacao_preserva_resultados_e_fontes_sem_mutacao():
    plano = _plano(_meta(), _meta(mes=10), _meta(mes=11, valor=0, ATIVO="NAO"))
    vendas = _vendas(_venda(valor=95), _venda(mes=10, valor=25))
    plano_antes, vendas_antes = plano.copy(deep=True), vendas.copy(deep=True)
    fechado, pulso, parceiros, vigentes = _avaliar(plano, vendas)
    vigentes_antes = vigentes.copy(deep=True)
    pagina._parceiros(parceiros, pulso, fechado, vigentes)
    assert _avaliar(plano, vendas)[:3] == (fechado, pulso, parceiros)
    pd.testing.assert_frame_equal(plano, plano_antes)
    pd.testing.assert_frame_equal(vendas, vendas_antes)
    pd.testing.assert_frame_equal(vigentes, vigentes_antes)


def test_primeira_dobra_distingue_ritmo_ytd_de_meta_anual_sem_repetir_modulos():
    plano = _plano(_meta(), _meta(mes=10))
    fechado, pulso, _, _ = _avaliar(plano, _vendas(_venda(valor=90), _venda(mes=10, valor=10)))
    hero = pagina._hero(fechado)
    anual = pagina._meta_anual(pulso)
    assert "RITMO FECHADO" in hero and "90,0%" in hero
    assert "FECHADO ATÉ SET/2026" in hero
    assert "50,0%" in anual and "Meta anual já vendida" in anual
    assert 'title="R$ 100,00"' in anual and 'title="R$ 200,00"' in anual
    assert "ainda precisam ser vendidos" in anual
    assert anual.count("<section") == 1
    assert "Pulso Atual" not in anual
    assert fechado.atingimento_ytd_pct == 90 and pulso.percentual_meta_ja_vendida == 50


def test_projecao_ordena_necessidade_forecast_plano_sem_alterar_valores():
    fechado, pulso, _, _ = _avaliar(_plano(_meta(), _meta(mes=10)), _vendas(_venda(valor=90)))
    html = pagina._projecao(fechado, pulso)
    assert html.index("NECESSIDADE COMERCIAL") < html.index("FORECAST") < html.index("PLANO FUTURO")
    assert "Run rate simples" in html
    assert 'title="R$ 36,67"' in html  # Necessidade comercial de 110 / 3.
    assert 'title="R$ 120,00"' in html  # Forecast por nove meses encerrados.
    assert 'title="R$ 100,00"' in html  # Plano futuro.


def test_apenas_inativos_continuam_acessiveis_sem_inventar_ranking_acionavel():
    html = _html(
        _plano(_meta(mes=3), _meta(mes=10, valor=0, ATIVO="NAO")),
        _vendas(_venda(mes=3, valor=20)),
    )
    assert "0 parceiros ativos" in html
    assert "Sem parceiros com meta ativa no período" in html
    assert "Parceiros fora da operação" in html
    assert 'title="R$ 20,00"' in _artigo(html, "G")
