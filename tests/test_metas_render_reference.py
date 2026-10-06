"""Uma renderização usa uma única data local, mesmo atravessando meia-noite."""

import datetime as dt
from functools import wraps

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pages_content import metas_resultados as pagina
from src.data import metas, metas_schema
from src.data.cleaning import (
    COL_GRUPO,
    COL_MES_GANHO_DATA,
    COL_MES_VEICULACAO_DATA,
    COL_STATUS,
    COL_VALOR_BRUTO,
    COL_VALOR_LIQUIDO,
    COL_VEICULO,
)
from src.data.loader import COL_ANO_ABA


def _fontes_sinteticas():
    vendas = pd.DataFrame([
        {
            COL_GRUPO: "G", COL_VEICULO: "V", COL_STATUS: "FATURADO",
            COL_VALOR_LIQUIDO: 50, COL_VALOR_BRUTO: 100,
            COL_MES_VEICULACAO_DATA: pd.Timestamp(ano, mes, 1),
            COL_MES_GANHO_DATA: pd.Timestamp(ano, mes, 1), COL_ANO_ABA: ano,
        }
        for ano in (2025, 2026) for mes in range(1, 13)
    ])
    plano = pd.DataFrame([
        {
            "NIVEL_META": "GRUPO", "GRUPO": "G", "VEICULO": "",
            "ANO": 2026, "MES": mes, "VALOR_META": 100, "ATIVO": "SIM",
            "REVISAO": 1, "CRIADO_EM": "2026-01-01T00:00:00-03:00",
            "MOTIVO": "Teste sintético",
        }
        for mes in range(1, 13)
    ], columns=metas_schema.COLUNAS_METAS)
    return vendas, plano


def _executar(vendas, plano, referencia):
    from pages_content.metas_resultados import render
    render(vendas, plano, data_referencia=referencia)


def _observar_calculos(monkeypatch):
    recebidas = {}
    resultados = {}

    def observar(nome, original):
        @wraps(original)
        def chamada(*args, **kwargs):
            recebidas[nome] = kwargs.get("data_referencia")
            resultado = original(*args, **kwargs)
            resultados[nome] = resultado
            return resultado
        return chamada

    for nome in (
        "validar_metas", "avaliar_metas", "avaliar_pulso", "avaliar_parceiros",
        "vigencia", "revisoes_retroativas", "coexistencia_niveis",
    ):
        monkeypatch.setattr(pagina, nome, observar(nome, getattr(pagina, nome)))
    mostrar_graficos = pagina._mostrar_graficos

    def graficos(resultado, pulso):
        resultados["graficos"] = (resultado, pulso)
        # Executa os gráficos reais, inclusive a guarda de referências iguais.
        mostrar_graficos(resultado, pulso)

    monkeypatch.setattr(pagina, "_mostrar_graficos", graficos)
    return recebidas, resultados


def _verificar_render(app, recebidas, resultados, referencia, encerrados):
    assert not app.exception
    assert len(app.get("plotly_chart")) == 2
    assert len(recebidas) == 7
    assert set(recebidas.values()) == {referencia}
    fechado = resultados["avaliar_metas"]
    pulso = resultados["avaliar_pulso"]
    assert resultados["graficos"] == (fechado, pulso)
    assert fechado.data_referencia == pulso.data_referencia == referencia
    assert fechado.meses_encerrados == pulso.meses_encerrados == encerrados
    assert fechado.realizado_ytd == 50 * encerrados
    assert len(resultados["avaliar_parceiros"]) == 1
    assert resultados["avaliar_parceiros"][0].realizado_ytd == 50 * encerrados
    for resultado in (fechado, pulso):
        assert [mes.mes for mes in resultado.meses if mes.estado_mes == "encerrado"] == list(range(1, encerrados + 1))
        em_andamento = [mes.mes for mes in resultado.meses if mes.estado_mes == "em_andamento"]
        assert em_andamento == ([referencia.month] if referencia.year == 2026 else [])
    conteudo = "\n".join(elemento.value for elemento in app.markdown)
    mes_final = "SET" if encerrados == 9 else "NOV" if encerrados == 11 else "DEZ"
    assert f"FECHADO ATÉ {mes_final}/2026" in conteudo


@pytest.mark.parametrize("antes,depois,encerrados", [
    (dt.date(2026, 10, 31), dt.date(2026, 11, 1), 9),
    (dt.date(2026, 12, 31), dt.date(2027, 1, 1), 11),
])
def test_render_atomico_quando_relogio_atravessa_meia_noite(monkeypatch, antes, depois, encerrados):
    recebidas, resultados = _observar_calculos(monkeypatch)
    data_local_original = metas_schema.data_local
    consultas_relogio = []

    def relogio(referencia=None):
        if referencia is not None:
            return data_local_original(referencia)
        # Antes do hardening, schema e engine principal consultavam antes da
        # meia-noite; o Pulso e as demais chamadas já consultavam depois.
        instante = antes if len(consultas_relogio) < 2 else depois
        consultas_relogio.append(instante)
        return instante

    for modulo in (pagina, metas, metas_schema):
        monkeypatch.setattr(modulo, "data_local", relogio, raising=False)
    app = AppTest.from_function(_executar, args=(*_fontes_sinteticas(), None))
    app.session_state["metas_ano"] = 2026
    app.run(timeout=10)
    _verificar_render(app, recebidas, resultados, antes, encerrados)
    assert consultas_relogio == [antes]


@pytest.mark.parametrize("instante,referencia,encerrados", [
    (dt.datetime(2027, 1, 1, 2, 30, tzinfo=dt.timezone.utc), dt.date(2026, 12, 31), 11),
    (dt.datetime(2027, 1, 1, 3, 0, tzinfo=dt.timezone.utc), dt.date(2027, 1, 1), 12),
])
def test_referencia_explicita_normalizada_no_fuso_da_operacao(monkeypatch, instante, referencia, encerrados):
    recebidas, resultados = _observar_calculos(monkeypatch)
    data_local_original = metas_schema.data_local

    def sem_relogio(valor=None):
        assert valor is not None, "Uma referência explícita não deve consultar o relógio."
        return data_local_original(valor)

    for modulo in (pagina, metas, metas_schema):
        monkeypatch.setattr(modulo, "data_local", sem_relogio, raising=False)
    app = AppTest.from_function(_executar, args=(*_fontes_sinteticas(), instante))
    app.session_state["metas_ano"] = 2026
    app.run(timeout=10)
    _verificar_render(app, recebidas, resultados, referencia, encerrados)
