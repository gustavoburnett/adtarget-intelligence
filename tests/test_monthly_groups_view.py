"""Interação do Checkpoint 2B, offline e sem consultar credenciais ou fontes.

AppTest verifica estado e integração; orientação, toque, overflow e aparência
continuam dependendo da inspeção real no navegador.
"""

import json
import re

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pages_content import metas_resultados as pagina
from src.components import monthly_groups as view
from src.components.monthly_groups_data import preparar_grupo
from src.data import metas as engine
from src.data.cleaning import COL_MES_VEICULACAO_DATA
from src.data.loader import COL_ANO_ABA
from tests.test_monthly_groups_data import REF, _meta, _plano, _venda, _vendas


def _fontes():
    plano = _plano(
        *(_meta(mes=mes, grupo=grupo) for grupo in ("DISNEY", "TEADS") for mes in range(1, 13)),
        *(_meta(mes=mes, grupo="BRASIL 247", valor=100 if mes <= 3 else 0,
                ATIVO="SIM" if mes <= 3 else "NAO") for mes in range(1, 13)),
        _meta(grupo="FORBES"),
    )
    vendas = _vendas(
        _venda(grupo="DISNEY", veiculo="DISNEY+", valor=60),
        _venda(grupo="DISNEY", veiculo="ESPN", valor=40),
        _venda(grupo="DISNEY", veiculo="ESPN", mes=10, valor=80),
        _venda(grupo="DISNEY", veiculo="ESPN", mes=12, valor=20),
        _venda(grupo="DISNEY", valor=35, ano=2025),
        _venda(grupo="TEADS", valor=1100),
        _venda(grupo="BRASIL 247", mes=3, valor=25),
        _venda(grupo="BRASIL 247", mes=4, valor=300),
        _venda(grupo="BRASIL 247", mes=10, valor=200),
        _venda(grupo="SISTEMA VERDES MARES", valor=12),
        _venda(grupo="SISTEMA VERDES MARES", mes=10, valor=8),
    )
    vendas[COL_ANO_ABA] = vendas[COL_MES_VEICULACAO_DATA].dt.year
    return vendas, plano


def _executar(vendas, plano, referencia):
    from pages_content.metas_resultados import render
    render(vendas, plano, data_referencia=referencia)


def _pagina(*, ano=2026):
    app = AppTest.from_function(_executar, args=(*_fontes(), REF))
    app.session_state["metas_ano"] = ano
    app.run(timeout=20)
    assert not app.exception
    return app


def _html(app):
    return "\n".join(element.value for element in app.markdown)


def _summary(app):
    return re.search(r'<div class="atg-group-summary".*?(?=<h3|$)', _html(app), re.DOTALL).group()


def _figuras(app):
    return [json.loads(element.proto.spec) for element in app.get("plotly_chart")]


def test_nova_secao_posicionada_apos_graficos_antes_parceiros_com_seletor_completo():
    app = _pagina()
    html = _html(app)
    titulos = ("Evolução Mensal", "Evolução Acumulada", "Desempenho Mensal por Grupo", "Metas por parceiro")
    assert [html.index(titulo) for titulo in titulos] == sorted(html.index(titulo) for titulo in titulos)
    assert app.selectbox(key="_group_monthly_grupo").options == [
        "BRASIL 247", "DISNEY", "FORBES", "SISTEMA VERDES MARES", "TEADS",
    ]
    assert app.selectbox(key="_group_monthly_grupo").value == "DISNEY"
    assert len(_figuras(app)) == 4
    assert app.button_group(key="metas_ano").value == 2026
    assert not app.error


@pytest.mark.parametrize("perspectiva", ["Vendas × Meta", "Atingimento", "Desvio"])
def test_perspectivas_nativas_preservam_resumo_anual_ytd_e_graficos_consolidados(perspectiva):
    app = _pagina()
    resumo = _summary(app)
    consolidados = _figuras(app)[:2]
    app.button_group(key="_group_monthly_perspectiva").set_value(perspectiva).run(timeout=20)
    assert not app.exception
    assert app.button_group(key="_group_monthly_perspectiva").value == perspectiva
    assert _summary(app) == resumo
    assert _figuras(app)[:2] == consolidados
    for figura in _figuras(app)[2:]:
        assert perspectiva in figura["layout"]["uirevision"]


def test_mes_por_seletor_nativo_atualiza_contribuicao_sem_trocar_ytd_ou_ano():
    app = _pagina()
    resumo, consolidados = _summary(app), _figuras(app)[:2]
    app.button_group(key=view._PERIODO).set_value("Mês").run(timeout=20)
    assert not app.exception
    assert app.selectbox(key=view._MES).value is None
    assert any("Selecione um mês" in item.value for item in app.info)
    app.selectbox(key=view._MES).set_value(10).run(timeout=20)
    assert not app.exception
    html = _html(app)
    assert 'aria-label="Detalhe Out/2026"' in html
    assert "no mês de Out/2026" in html
    assert 'title="R$ 80,00"' in html
    assert "Já vendido · carteira" in html and "Cobertura já vendida" in html
    assert _summary(app) == resumo
    assert _figuras(app)[:2] == consolidados
    app.button_group(key=view._PERIODO).set_value("Ano").run(timeout=20)
    assert not app.exception
    assert "no ano de 2026" in _html(app)
    assert 'aria-label="Detalhe Out/2026"' not in _html(app)
    assert 'title="R$ 200,00"' in _html(app)


def test_troca_de_grupo_limpa_mes_e_contribuicao_anterior_preservando_filtros_globais():
    app = _pagina()
    app.button_group(key=view._PERIODO).set_value("Mês").run(timeout=20)
    app.selectbox(key=view._MES).set_value(10).run(timeout=20)
    app.selectbox(key="_group_monthly_grupo").set_value("TEADS").run(timeout=20)
    assert not app.exception
    assert app.session_state[view._MES] is None
    assert app.button_group(key=view._PERIODO).value == "Ano"
    assert "no ano de 2026" in _html(app)
    assert "Detalhe Out/2026" not in _html(app)
    assert "122,2%" in _html(app) and "Acima do ritmo" in _html(app)
    assert app.button_group(key="metas_ano").value == 2026


def test_troca_de_ano_limpa_mes_sem_fabricar_meta_historica_ou_ocultar_vendas():
    app = _pagina()
    app.button_group(key=view._PERIODO).set_value("Mês").run(timeout=20)
    app.selectbox(key=view._MES).set_value(10).run(timeout=20)
    app.button_group(key="metas_ano").set_value(2025).run(timeout=20)
    assert not app.exception
    html = _html(app)
    assert app.session_state[view._MES] is None
    assert app.button_group(key=view._PERIODO).value == "Ano"
    assert "Não há metas cadastradas para 2025" in html
    assert "Sem meta cadastrada" in html and "Meta anual não cadastrada" in html
    assert "RITMO FECHADO" not in html and "Metas por parceiro" not in html
    assert "GAP COMERCIAL" not in html and "FORECAST" not in html
    assert 'title="R$ 35,00"' in html
    assert len(_figuras(app)) == 2  # Somente as orientações da nova visão, sem gráficos consolidados.


def test_grupo_sem_meta_nao_inventa_atingimento_gap_ou_meta_individual():
    app = _pagina()
    app.selectbox(key="_group_monthly_grupo").set_value("SISTEMA VERDES MARES").run(timeout=20)
    assert not app.exception
    resumo = _summary(app)
    assert "Sem meta cadastrada" in resumo and "Atingimento YTD não se aplica" in resumo
    assert "Gap comercial e percentual da meta anual não se aplicam" in resumo
    assert 'title="R$ 20,00"' in resumo
    assert "sem metas individuais" in _html(app)


@pytest.mark.parametrize("perspectiva", ["Atingimento", "Desvio"])
def test_sem_meta_suprime_comparacao_ficticia_e_restaura_vendas_preservando_mes(perspectiva):
    app = _pagina()
    app.selectbox(key="_group_monthly_grupo").set_value("SISTEMA VERDES MARES").run(timeout=20)
    app.button_group(key=view._PERIODO).set_value("Mês").run(timeout=20)
    app.selectbox(key=view._MES).set_value(10).run(timeout=20)
    resumo, consolidados = _summary(app), _figuras(app)[:2]
    app.button_group(key="_group_monthly_perspectiva").set_value(perspectiva).run(timeout=20)
    assert not app.exception
    assert len(_figuras(app)) == 2  # Nenhuma curva ou eixo novo inventa uma base de comparação.
    assert _figuras(app) == consolidados
    assert any(item.value == "Sem meta cadastrada para esta comparação. Consulte as vendas em Vendas × Meta."
               for item in app.info)
    assert _summary(app) == resumo
    assert app.session_state[view._MES] == 10
    assert app.button_group(key=view._PERIODO).value == "Mês"
    assert "no mês de Out/2026" in _html(app) and 'title="R$ 8,00"' in _html(app)
    app.button_group(key="_group_monthly_perspectiva").set_value("Vendas × Meta").run(timeout=20)
    assert not app.exception
    assert len(_figuras(app)) == 4
    assert _figuras(app)[:2] == consolidados
    assert not app.info
    assert _summary(app) == resumo
    assert app.session_state[view._MES] == 10
    assert 'aria-label="Detalhe Out/2026"' in _html(app)
    for figura in _figuras(app)[2:]:
        assert any(serie.get("selectedpoints") == [9] for serie in figura["data"])


def test_vigencia_brasil247_preserva_periodo_e_vendas_fora_separadas():
    app = _pagina()
    app.selectbox(key="_group_monthly_grupo").set_value("BRASIL 247").run(timeout=20)
    assert not app.exception
    resumo = _summary(app)
    assert "Operação encerrada em Mar/2026" in resumo
    assert "Jan a Mar/2026" in resumo
    assert "Já vendido Out a Dez/2026" not in resumo
    assert 'title="R$ 25,00"' in resumo and 'title="R$ 500,00"' in resumo
    assert "Fora do perímetro de metas · não somado ao atingimento oficial" in resumo
    app.button_group(key=view._PERIODO).set_value("Mês").run(timeout=20)
    app.selectbox(key=view._MES).set_value(4).run(timeout=20)
    assert not app.exception
    assert "Fora de vigência" in _html(app)
    assert "Vendas fora do perímetro" in _html(app)


@pytest.mark.parametrize("registros,esperado,proibido", [
    ((), "Sem registros elegíveis no perímetro selecionado", "Diferença para a meta"),
    ((_venda(valor=0),), "0,0%", "Sem registros elegíveis no perímetro selecionado"),
])
def test_detalhe_diferencia_sem_registros_de_zero_explicito(registros, esperado, proibido):
    modelo = preparar_grupo(_vendas(*registros), _plano(_meta()), 2026, "G", data_referencia=REF)
    html = view._detalhe(modelo.meses[0], 2026)
    assert esperado in html and proibido not in html
    if registros:
        assert "Diferença para a meta" in html and 'title="R$ 100,00"' in html
    else:
        assert "não comprova venda zero e não gera atingimento nem desvio" in html
        assert "<dt>Atingimento</dt>" not in html


def test_mes_sem_meta_com_vendas_fora_nao_afirma_ausencia_de_registros_na_fonte():
    modelo = preparar_grupo(
        _vendas(_venda(mes=2, valor=80)), _plano(_meta(mes=1)),
        2026, "G", data_referencia=REF,
    )
    html = view._detalhe(modelo.meses[1], 2026)
    assert "Sem meta cadastrada neste mês" in html
    assert "Vendas fora do perímetro" in html and 'title="R$ 80,00"' in html
    assert "Sem registros de vendas na fonte" not in html
    assert "<dt>Atingimento</dt>" not in html and "Diferença para a meta" not in html


def test_registros_fora_com_saldo_anulado_nao_viram_ausencia_de_registros_na_fonte():
    vendas = _vendas(_venda(mes=2, valor=10), _venda(mes=2, valor=-10))
    modelo = preparar_grupo(vendas, _plano(_meta(mes=1)), 2026, "G", data_referencia=REF)
    mes = modelo.meses[1]
    assert len(vendas) == 2 and mes.registros == 0 and mes.fora_perimetro == 0
    html = view._detalhe(mes, 2026)
    figura = view.monthly_groups_charts.figura_mensal(modelo)
    hover = figura.data[0].customdata[1][1]
    for texto in (html, hover):
        assert "Sem registros elegíveis no perímetro selecionado." in texto
        assert "Isso não comprova venda zero e não gera atingimento nem desvio." in texto
        assert "Sem registros de vendas na fonte" not in texto
    assert mes.atingimento_pct is None and mes.desvio is None
    assert modelo.total_vendido_ano == 0


@pytest.mark.parametrize("mes,estado", [(10, "Em andamento"), (12, "Futuro")])
def test_mes_aberto_comunica_cobertura_e_falta_cobrir_sem_deficit(mes, estado):
    modelo = preparar_grupo(_vendas(_venda(mes=mes, valor=25)), _plano(_meta(mes=mes)),
                            2026, "G", data_referencia=REF)
    html = view._detalhe(modelo.meses[mes - 1], 2026)
    assert estado in html
    assert "Já vendido · carteira" in html and "Cobertura já vendida" in html
    assert "Falta cobrir (não é déficit)" in html
    assert "<dt>Atingimento</dt>" not in html and "Diferença para a meta" not in html


def test_html_escapa_grupo_e_veiculos_recebidos_da_fonte():
    grupo, veiculo = '<script>alert("grupo")</script>', '<img src=x onerror=alert(1)>'
    modelo = preparar_grupo(_vendas(_venda(grupo=grupo, veiculo=veiculo)),
                            _plano(_meta(grupo=grupo)), 2026, grupo, data_referencia=REF)
    html = view._resumo(modelo, True, None) + view._veiculos(modelo, None)
    assert "<script>" not in html.lower() and "<img src=x" not in html.lower()
    assert "&lt;SCRIPT&gt;" in html and "&lt;IMG SRC=X ONERROR=ALERT(1)&gt;" in html


@pytest.mark.parametrize("mes", [1, 6, 12])
def test_callback_selecao_nativa_usa_apenas_identificador_mensal(monkeypatch, mes):
    estado = {"plot": {"selection": {"points": [{"customdata": [mes, "VALOR_NAO_CONFIAVEL"]}]}}}
    monkeypatch.setattr(view.st, "session_state", estado)
    view._selecionar_mes("plot")
    assert estado[view._MES] == mes
    assert estado[view._PERIODO] == "Mês"
    assert "VALOR_NAO_CONFIAVEL" not in (estado[view._MES], estado[view._PERIODO])


@pytest.mark.parametrize("payload", [
    {}, {"selection": {}}, {"selection": {"points": []}},
    *({"selection": {"points": [{"customdata": [valor]}]}} for valor in (True, 0, 13, "6", 6.5)),
    {"selection": {"points": [{"customdata": "1"}]}},
])
def test_callback_ignora_selecao_vazia_ou_mes_invalido(monkeypatch, payload):
    estado = {"plot": payload, view._MES: 3, view._PERIODO: "Ano"}
    monkeypatch.setattr(view.st, "session_state", estado)
    view._selecionar_mes("plot")
    assert estado[view._MES] == 3 and estado[view._PERIODO] == "Ano"


def test_exploracao_nao_muta_fontes_ou_contratos_financeiros_consolidados():
    vendas, plano = _fontes()
    copias = vendas.copy(deep=True), plano.copy(deep=True)
    anterior = (engine.avaliar_metas(vendas, plano, 2026, data_referencia=REF),
                engine.avaliar_pulso(vendas, plano, 2026, data_referencia=REF),
                engine.avaliar_parceiros(vendas, plano, 2026, data_referencia=REF))
    for grupo in ("DISNEY", "TEADS", "BRASIL 247", "SISTEMA VERDES MARES"):
        modelo = preparar_grupo(vendas, plano, 2026, grupo, data_referencia=REF)
        view._resumo(modelo, True, None)
        view._veiculos(modelo, None)
        for mes in modelo.meses:
            view._detalhe(mes, 2026)
    atual = (engine.avaliar_metas(vendas, plano, 2026, data_referencia=REF),
             engine.avaliar_pulso(vendas, plano, 2026, data_referencia=REF),
             engine.avaliar_parceiros(vendas, plano, 2026, data_referencia=REF))
    assert atual == anterior
    pd.testing.assert_frame_equal(vendas, copias[0])
    pd.testing.assert_frame_equal(plano, copias[1])
