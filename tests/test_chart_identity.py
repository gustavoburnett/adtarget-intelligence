"""Real Streamlit identity regression; no production data or credentials."""
import pytest
from streamlit.testing.v1 import AppTest
from tests.test_design_analitico_veiculos import _fonte, _pagina
from src.data import cleaning


def render_twins():
    import pandas as pd
    from src.components.charts import grafico_barra_horizontal
    data = pd.DataFrame({'label': ['TEADS'], 'value': [123.45]})
    for key in ('groups', 'vehicles'):
        grafico_barra_horizontal(data, 'label', 'value', key,
                                 estilo_veiculos=True, key=key)


def test_identical_figures_have_distinct_stable_ids():
    app = AppTest.from_function(render_twins).run()
    assert not app.exception
    ids = [c.proto.id for c in app.get('plotly_chart')]
    assert len(ids) == len(set(ids)) == 2
    app.run()
    assert not app.exception
    assert ids == [c.proto.id for c in app.get('plotly_chart')]


@pytest.mark.parametrize('group', ['TEADS', 'DISNEY'])
@pytest.mark.parametrize('value', ['Valor Líquido', 'Valor Bruto'])
@pytest.mark.parametrize('month', ['Mês (Veiculação)', 'Mês (Ganho)'])
@pytest.mark.parametrize('year', [2025, 2026])
def test_vehicle_filters(group, value, month, year):
    df = _fonte()
    df.loc[df[cleaning.COL_GRUPO].eq('TEADS'), cleaning.COL_AGENCIA] = 'PROPEG'
    agency = 'PROPEG' if group == 'TEADS' else 'AGÊNCIA DISNEY'
    app = _pagina(fonte=df, grupos=[group], agencias=[agency],
                  ano=year, valor=value, criterio=month)
    ids = [c.proto.id for c in app.get('plotly_chart')]
    assert len(ids) == len(set(ids))
    app.run()
    assert not app.exception
    assert ids == [c.proto.id for c in app.get('plotly_chart')]
