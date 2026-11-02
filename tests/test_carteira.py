"""Novos cenários CV; não equivalem às definições não localizadas B1–B7."""
import datetime as dt
from copy import deepcopy
import pandas as pd
import pytest
from tests.test_metas_engine import _meta,_metas,_venda,_vendas
from src.data.carteira import preparar
from src.data import metas as engine
from pages_content.carteira_vendas import documento
REF=dt.date(2026,3,15)

def build(sales,plan): return preparar(sales,plan,data_referencia=REF,anos=[2025,2026,2027])
def cell(p,m=1,g='',grain=1):return p['slices'][f'2026|{g}|{m}|{grain}']

def test_cv01_total_dentro_fora_sem_meta_e_historico():
 p=build(_vendas(_venda(valor=40),_venda(valor=20,grupo='H')),_metas(_meta()))
 c=cell(p);assert (c['total'],c['inside'],c['out'])==(6000,4000,2000)
 assert cell(p,g='H')['target'] is None
 assert set(p['groupsByYear']['2026'])=={'G','H'}

def test_cv02_grupo_domina_veiculo_sem_duplicidade():
 p=build(_vendas(_venda(valor=40)),_metas(_meta(valor=100),_meta(valor=80,nivel='VEICULO',veiculo='V')))
 assert cell(p)['target']==10000 and cell(p)['inside']==4000

def test_cv03_grupo_inativo_nao_ressuscita_veiculo():
 p=build(_vendas(_venda()),_metas(_meta(ATIVO='NAO',valor=0),_meta(nivel='VEICULO',veiculo='V')))
 assert cell(p)['target'] is None and cell(p)['inside']==0 and cell(p)['inactive']

def test_cv04_futuro_integral_ganho_distinto_status_oficiais():
 p=build(_vendas(_venda(mes='2026-12-01',ganho='2026-01-01',valor=80,status='A VEICULAR'),_venda(valor=777,status='CANCELADO'),_venda(valor=888,status='BONIFICADO')),_metas(_meta(mes=12)))
 assert cell(p,m=12)['total']==8000 and cell(p)['total']==0
 assert len(p['rows'])==1

def test_cv05_agregacoes_e_igualdade_engine():
 sales=_vendas(*[_venda(mes=f'2026-{m:02d}-01',valor=m) for m in range(1,13)])
 plan=_metas(*[_meta(mes=m,valor=100*m) for m in range(1,13)])
 p=build(sales,plan);pulse=engine.avaliar_pulso(sales,plan,2026,data_referencia=REF)
 for grain in (1,3,6,12):
  for first in range(1,13,grain):
   c=cell(p,m=first,grain=grain)
   assert c['inside']==float(sum(m.vendido for m in pulse.meses[first-1:first-1+grain])*100)
   for field in ('total','inside','out','target'):
    assert c[field]==sum(cell(p,m=m)[field] for m in range(first,first+grain))

def test_cv06_meta_zero_ausente_parcial_e_sem_pis():
 p=build(_vendas(),_metas(_meta(valor=0),_meta(mes=2,valor=100)))
 assert cell(p)['target']==0 and cell(p)['gap'] is None and cell(p)['coverage'] is None
 assert cell(p,m=3)['target'] is None
 assert cell(p,grain=3)['partial'] and cell(p,grain=3)['gap']==10000

def test_cv07_revisao_vigencia_e_sem_mutacao():
 sales=_vendas(_venda());plan=_metas(_meta(valor=10),_meta(valor=30,REVISAO=2),_meta(valor=90,REVISAO=3,CRIADO_EM='2026-12-01T00:00:00-03:00'))
 before=sales.copy(deep=True);plan_before=plan.copy(deep=True)
 p=build(sales,plan);assert cell(p)['target']==9000
 pd.testing.assert_frame_equal(sales,before);pd.testing.assert_frame_equal(plan,plan_before)

def test_cv08_historico_total_sem_perimetro_atual_e_base_zero():
 p=build(_vendas(_venda(mes='2025-01-01',grupo='H',valor=25),_venda(valor=10)),_metas(_meta()))
 assert cell(p)['old']==2500 and cell(p)['hasOld']
 p=build(_vendas(_venda(mes='2025-01-01',valor=0)),_metas(_meta()))
 assert cell(p)['old']==0 and cell(p)['hasOld']

def test_cv09_detalhes_preservados_duplicados_nao_removidos():
 sales=_vendas(_venda(),_venda());sales['PI']='123'
 p=build(sales,_metas(_meta()));assert len(p['rows'])==2 and cell(p)['total']==10000
 assert not any(r['flag'] for r in p['rows'])

def test_cv10_dados_html_nao_executam_script():
 sales=_vendas(_venda());sales['CLIENTE']='</script><script>alert(1)</script>'
 html=documento(build(sales,_metas(_meta())))
 assert '</script><script>alert(1)' not in html
 assert '\\u003c/script\\u003e' in html
