"""Contrato de apresentação mensal, usando fontes sintéticas e engines reais."""

import datetime as dt
from dataclasses import replace
from decimal import Decimal

import pandas as pd
import pytest

from src.components.design_tokens import COLOR, TYPOGRAPHY
from src.components.monthly_groups_charts import PERSPECTIVAS, figura_mensal
from src.components.monthly_groups_data import preparar_grupo
from src.data.cleaning import (
    COL_GRUPO, COL_MES_GANHO_DATA, COL_MES_VEICULACAO_DATA, COL_STATUS,
    COL_VALOR_BRUTO, COL_VALOR_LIQUIDO, COL_VEICULO,
)
from src.data.metas_schema import COLUNAS_METAS


def _model(grupo="DISNEY", veiculo="DISNEY+", *, sem_metas=False):
    vendas = pd.DataFrame([
        {
            COL_GRUPO: grupo, COL_VEICULO: veiculo, COL_STATUS: "FATURADO",
            COL_VALOR_LIQUIDO: valor, COL_VALOR_BRUTO: valor * 2,
            COL_MES_GANHO_DATA: pd.Timestamp(2026, mes, 1),
            COL_MES_VEICULACAO_DATA: pd.Timestamp(2026, mes, 1),
        }
        for mes, valor in ((1, 150.37), (2, 20), (4, 10), (5, 25), (6, 35), (7, 10), (7, -10), (10, 30), (12, 400))
    ])
    plano = pd.DataFrame([
        {
            "NIVEL_META": "GRUPO", "GRUPO": grupo, "VEICULO": "", "ANO": 2026,
            "MES": mes, "VALOR_META": 0 if mes in (4, 5) else 100,
            "ATIVO": "NAO" if mes == 5 else "SIM", "REVISAO": 1,
            "CRIADO_EM": "2026-01-01T00:00:00-03:00", "MOTIVO": "Teste",
        }
        for mes in range(1, 13) if mes != 6
    ], columns=COLUNAS_METAS)
    return preparar_grupo(vendas, plano.iloc[:0] if sem_metas else plano, 2026, grupo, data_referencia=dt.date(2026, 10, 19))


def _valores(trace, mobile=False):
    return list(trace.x if mobile else trace.y)


@pytest.mark.parametrize("perspectiva", PERSPECTIVAS)
@pytest.mark.parametrize("mobile", [False, True])
def test_calendario_dos_doze_meses_em_ordem_e_customdata_selecionavel(perspectiva, mobile):
    model = _model()
    figura = figura_mensal(replace(model, meses=tuple(reversed(model.meses))), perspectiva, mobile=mobile)
    for serie in figura.data:
        assert list(serie.y if mobile else serie.x) == list(range(1, 13))
        assert [item[0] for item in serie.customdata] == list(range(1, 13))
        assert all(type(item[0]) is int for item in serie.customdata)
        assert serie.hovertemplate == "%{customdata[1]}<extra></extra>"
    eixo = figura.layout.yaxis if mobile else figura.layout.xaxis
    assert list(eixo.ticktext) == ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out*", "Nov°", "Dez°"]


@pytest.mark.parametrize("mobile", [False, True])
def test_vendas_e_metas_preservam_valores_e_lacunas_do_adaptador(mobile):
    model = _model()
    figura = figura_mensal(model, mobile=mobile)
    meta, realizado, ja_vendido = figura.data
    assert _valores(meta, mobile) == [float(mes.meta) if mes.meta is not None else None for mes in model.meses]
    assert _valores(realizado, mobile) == [float(mes.vendido) if mes.estado_mes == "encerrado" else None for mes in model.meses]
    assert _valores(ja_vendido, mobile) == [float(mes.vendido) if mes.estado_mes != "encerrado" else None for mes in model.meses]
    assert _valores(meta, mobile)[3:6] == [0, None, None]
    assert _valores(realizado, mobile)[4:6] == [0, 0]
    assert meta.marker.pattern.shape == "/"
    assert meta.width > realizado.width == ja_vendido.width
    assert realizado.marker.color == COLOR["brand"]
    assert ja_vendido.marker.color == COLOR["chart-previous"]
    assert [serie.name for serie in figura.data] == ["Meta mensal", "Realizado", "Já vendido"]


@pytest.mark.parametrize("mobile", [False, True])
def test_atingimento_sem_teto_acima_de_100_e_sem_zero_ficticio(mobile):
    model = _model()
    figura = figura_mensal(model, "Atingimento", mobile=mobile)
    valores = _valores(figura.data[0], mobile)
    assert valores == [float(mes.atingimento_pct) if mes.atingimento_pct is not None else None for mes in model.meses]
    assert valores[0] == 150.37
    assert valores[11] == 400
    assert valores[2:6] == [None] * 4  # sem registros, zero ativo, inativo e ausente
    assert valores[6] == 0  # zero com registros preserva a situação financeira
    eixo_valor = figura.layout.xaxis if mobile else figura.layout.yaxis
    assert eixo_valor.range is None
    referencia = figura.layout.shapes[0]
    assert (referencia.x0, referencia.x1) == (100, 100) if mobile else (referencia.y0, referencia.y1) == (100, 100)


@pytest.mark.parametrize("mobile", [False, True])
def test_desvio_preserva_sinal_positivo_negativo_zero_e_ausencias(mobile):
    model = _model()
    figura = figura_mensal(model, "Desvio", mobile=mobile)
    valores = _valores(figura.data[0], mobile)
    assert valores == [float(mes.desvio) if mes.desvio is not None else None for mes in model.meses]
    assert valores[0] == 50.37
    assert valores[1] == -80
    assert valores[2] is None
    assert valores[3] == 10  # meta ativa zero continua sem percentual
    assert valores[4:6] == [None, None]
    assert valores[6] == -100
    assert figura.data[0].marker.color[0] == COLOR["positive"]
    assert figura.data[0].marker.color[1] == COLOR["negative"]
    assert figura.data[0].marker.color[9] == COLOR["chart-previous"]
    equilibrado = replace(model, meses=(replace(model.meses[0], vendido=Decimal(100), desvio=Decimal(0)), *model.meses[1:]))
    assert _valores(figura_mensal(equilibrado, "Desvio", mobile=mobile).data[0], mobile)[0] == 0


@pytest.mark.parametrize("perspectiva", PERSPECTIVAS)
def test_mobile_e_desktop_tem_mesmo_contrato_financeiro_e_hover(perspectiva):
    model = _model()
    desktop = figura_mensal(model, perspectiva)
    mobile = figura_mensal(model, perspectiva, mobile=True)
    assert len(desktop.data) == len(mobile.data)
    for grande, pequena in zip(desktop.data, mobile.data, strict=True):
        assert _valores(grande) == _valores(pequena, True)
        assert list(grande.customdata) == list(pequena.customdata)
        assert list(grande.text or []) == list(pequena.text or [])
    assert mobile.layout.height > desktop.layout.height


@pytest.mark.parametrize("perspectiva", PERSPECTIVAS)
def test_hover_monetario_completo_e_contribuicao_nao_inventa_meta_de_veiculo(perspectiva):
    figura = figura_mensal(_model(), perspectiva)
    hover = figura.data[0].customdata[0][1]
    assert "DISNEY · Janeiro 2026" in hover
    assert "Realizado: R$ 150,37" in hover
    assert "Meta mensal vigente: R$ 100,00" in hover
    assert "Atingimento mensal: 150,4%" in hover
    assert "Acima da meta: R$ 50,37" in hover
    assert "DISNEY+: R$ 150,37 · 100,0% das vendas" in hover
    assert "meta do veículo" not in hover.lower()


def test_hover_distingue_sem_registros_saldo_zero_ausencia_inatividade_e_zero_ativo():
    figura = figura_mensal(_model())
    hovers = [item[1] for item in figura.data[0].customdata]
    assert "Sem registros elegíveis no perímetro selecionado. Isso não comprova venda zero e não gera atingimento nem desvio." in hovers[2]
    assert "Realizado:" not in hovers[2]
    assert "Atingimento mensal" not in hovers[2]
    assert "Déficit" not in hovers[2]
    assert "Meta ativa com valor zero · percentual não calculável" in hovers[3]
    assert "Fora de vigência · meta inativa" in hovers[4]
    assert "Sem registros elegíveis no perímetro" in hovers[4]
    assert "Sem registros de vendas na fonte" not in hovers[4]
    assert "Vendas fora do perímetro de metas: R$ 25,00" in hovers[4]
    assert "Sem meta cadastrada" in hovers[5]
    assert "Vendas fora do perímetro de metas: R$ 35,00" in hovers[5]
    assert "Saldo de vendas zerado com registros" in hovers[6]
    assert "Atingimento mensal: 0,0%" in hovers[6]
    assert "Sem registros" not in hovers[6]


@pytest.mark.parametrize("mobile", [False, True])
def test_grupo_sem_metas_preserva_vendas_integrais_sem_curvas_de_comparacao(mobile):
    model = _model(grupo="SISTEMA VERDES MARES", sem_metas=True)
    vendas = figura_mensal(model, mobile=mobile)
    assert _valores(vendas.data[0], mobile) == [None] * 12
    assert _valores(vendas.data[1], mobile)[4:6] == [25, 35]
    for perspectiva in ("Atingimento", "Desvio"):
        figura = figura_mensal(model, perspectiva, mobile=mobile)
        assert _valores(figura.data[0], mobile) == [None] * 12
        assert "Sem meta cadastrada" in figura.data[0].customdata[0][1]
        assert "percentual" not in figura.data[0].customdata[0][1]
        assert not figura.layout.shapes


@pytest.mark.parametrize("perspectiva", PERSPECTIVAS)
def test_vendas_negativas_nao_sao_recortadas_em_zero(perspectiva):
    model = _model()
    negativo = replace(
        model, meses=(replace(model.meses[0], vendido=Decimal("-25.75"),
                              atingimento_pct=Decimal("-25.75"), desvio=Decimal("-125.75")), *model.meses[1:]),
    )
    figura = figura_mensal(negativo, perspectiva)
    serie = figura.data[1] if perspectiva == "Vendas × Meta" else figura.data[0]
    assert serie.y[0] == (-125.75 if perspectiva == "Desvio" else -25.75)
    assert figura.layout.yaxis.range is None
    assert "Realizado: R$ -25,75" in serie.customdata[0][1]


@pytest.mark.parametrize("perspectiva", PERSPECTIVAS)
def test_hover_aberto_e_futuro_nao_chama_carteira_de_realizado_ou_deficit(perspectiva):
    figura = figura_mensal(_model(), perspectiva)
    outubro = figura.data[0].customdata[9][1]
    dezembro = figura.data[0].customdata[11][1]
    assert "Mês em andamento" in outubro
    assert "Já vendido: R$ 30,00" in outubro
    assert "Cobertura já vendida: 30,0%" in outubro
    assert "Falta cobrir (não é déficit): R$ 70,00" in outubro
    assert "Realizado:" not in outubro
    assert "Déficit mensal" not in outubro
    assert "Mês futuro" in dezembro
    assert "Cobertura acima da meta: R$ 300,00" in dezembro


@pytest.mark.parametrize("perspectiva", PERSPECTIVAS)
@pytest.mark.parametrize("mobile", [False, True])
def test_selecao_mensal_nao_muda_valores_e_nao_inventa_pontos(perspectiva, mobile):
    model = _model()
    original = figura_mensal(model, perspectiva, mobile=mobile)
    selecionada = figura_mensal(model, perspectiva, mobile=mobile, mes_selecionado=5)
    assert len(original.data) == len(selecionada.data)
    for antes, depois in zip(original.data, selecionada.data, strict=True):
        assert _valores(antes, mobile) == _valores(depois, mobile)
        assert antes.selectedpoints is None
        assert list(depois.selectedpoints) == [4]
        assert depois.customdata[4][0] == 5


def test_nomes_de_grupo_e_veiculo_sao_escapados_no_hover():
    figura = figura_mensal(_model(grupo='<img src=x onerror="alert(1)">', veiculo='<script>alert(2)</script>'))
    hover = figura.data[0].customdata[0][1]
    assert "<IMG" not in hover
    assert "<SCRIPT" not in hover
    assert "&lt;IMG SRC=X ONERROR=&quot;ALERT(1)&quot;&gt;" in hover
    assert "&lt;SCRIPT&gt;ALERT(2)&lt;/SCRIPT&gt;" in hover


@pytest.mark.parametrize("mobile", [False, True])
def test_faixas_inativas_decorativas_nao_afetam_eixo_financeiro(mobile):
    figura = figura_mensal(_model(), mobile=mobile)
    assert figura.layout.shapes
    for faixa in figura.layout.shapes:
        assert faixa.xref == "paper" if mobile else faixa.yref == "paper"
        assert faixa.layer == "below"
    assert (figura.layout.xaxis if mobile else figura.layout.yaxis).range is None


def test_estilo_reutiliza_inter_tokens_e_nao_insere_nota_sobre_eixo():
    figura = figura_mensal(_model())
    assert figura.layout.font.family == TYPOGRAPHY["family"]
    assert figura.layout.plot_bgcolor == COLOR["surface-card"]
    assert figura.layout.yaxis.tickfont.color == COLOR["text-muted"]
    assert not any("Em andamento" in anotacao.text or "Futuro" in anotacao.text for anotacao in figura.layout.annotations)
    assert figura.layout.clickmode == "event+select"


@pytest.mark.parametrize("mobile", [False, True])
def test_vendas_meta_percentuais_alinhados_fora_das_barras_e_sem_truncamento(mobile):
    model = _model()
    figura = figura_mensal(model, mobile=mobile)
    comparaveis = [mes for mes in model.meses if mes.atingimento_pct is not None]
    assert len(figura.layout.annotations) == len(comparaveis)
    assert all(serie.text is None for serie in figura.data)
    for mes, etiqueta in zip(comparaveis, figura.layout.annotations, strict=True):
        assert etiqueta.text == f"{mes.atingimento_pct:.1f}".replace(".", ",") + "%"
        assert etiqueta.xref == "paper" if mobile else etiqueta.yref == "paper"
        assert etiqueta.x == 1.03 if mobile else etiqueta.y == 1.03
        assert etiqueta.y == mes.mes if mobile else etiqueta.x == mes.mes
    assert figura.layout.annotations[0].text == "150,4%"
    assert figura.layout.annotations[-1].text == "400,0%"


def test_perspectiva_invalida_falha_expressamente():
    with pytest.raises(ValueError, match="Perspectiva"):
        figura_mensal(_model(), "projeção estimada")


@pytest.mark.parametrize("mes", [0, 13, "1", True])
def test_mes_invalido_nao_seleciona_silenciosamente(mes):
    with pytest.raises(ValueError, match="Mês selecionado"):
        figura_mensal(_model(), mes_selecionado=mes)
