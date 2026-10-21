"""Regressão de apresentação histórica, inclusive o limite exato da meta."""
from decimal import Decimal
import pytest
from tests.test_metas_ux import _meta, _plano, _vendas, _venda, _avaliar
from pages_content import metas_resultados as pagina

@pytest.mark.parametrize('ano',[2024,2025])
@pytest.mark.parametrize('valor,rotulo',[(99.99,'Meta não atingida'),(100,'Meta atingida'),(101,'Meta atingida')])
def test_historico_final_sem_ritmo_e_sem_projecao(ano,valor,rotulo):
    plano=_plano(_meta(ANO=ano,CRIADO_EM=f'{ano}-01-01T00:00:00-03:00'))
    vendas=_vendas(_venda(valor=valor,ano=ano))
    resultado,pulso,parceiros,vigentes=_avaliar(plano,vendas,ano=ano)
    html=pagina._parceiros(parceiros,pulso,resultado,vigentes)
    assert f'1 grupos com meta em {ano}' in html
    assert rotulo in html
    assert 'ritmo' not in html
    assert 'parceiros ativos' not in html.lower()
    assert pagina._projecao(resultado,pulso)==''
    assert 'RESULTADO FINAL' in pagina._hero(resultado)

def test_ano_corrente_preserva_apresentacao():
    plano=_plano(*(_meta(mes=m) for m in range(1,13)))
    resultado,pulso,parceiros,vigentes=_avaliar(plano,_vendas(_venda()))
    html=pagina._parceiros(parceiros,pulso,resultado,vigentes)
    assert 'ritmo' in html
    assert 'parceiros ativos' in html
    assert 'Projeção' in pagina._projecao(resultado,pulso)
