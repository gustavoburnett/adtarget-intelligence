"""Quinta área: apresentação B sobre o adaptador financeiro oficial."""
import json
from pathlib import Path
import streamlit as st
from src.data.carteira import preparar
from src.data.metas_schema import ErroDeMetas
from src.components.shell import font_style

@st.cache_data(show_spinner='Carregando carteira…', ttl=900)
def _snapshot(dados, metas, referencia):
    return preparar(dados, metas, data_referencia=referencia)

def documento(payload, sincronizado_em=None, contexto=None):
    payload = dict(payload, context=contexto, appUrl="https://adtarget-intelligence-e7ftyu8hg9jcek5gaguhpm.streamlit.app/")
    template = (Path(__file__).parents[1]/'src/components/carteira_b.html').read_text()
    # Escape script boundaries even for adversarial PI/client/campaign names.
    data = json.dumps(payload, ensure_ascii=False, allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return template.replace('__CARTEIRA_DATA__',data).replace('__REFERENCE__',payload['reference']).replace('__SYNC__',str(sincronizado_em or 'não informada')).replace('__INVALID__',str(payload['unassignedMonth'])).replace('</head>',font_style()+'</head>')

def render(dados, *, metas_df=None, erro_metas=None, sincronizado_em=None):
    if erro_metas is not None or metas_df is None:
        st.error('Não foi possível carregar a carteira. Metas indisponíveis; nenhum zero financeiro foi presumido.')
        if st.button('Tentar novamente',key='carteira_retry'): st.cache_data.clear(); st.rerun()
        return
    from src.data.metas import data_local
    try:
        payload = _snapshot(dados,metas_df,data_local())
        html = documento(payload,sincronizado_em,st.query_params.get("carteira"))
    except (ErroDeMetas,ValueError,KeyError) as error:
        st.error('Não foi possível carregar a carteira. Confira a integridade do snapshot de vendas e metas.')
        if st.button('Tentar novamente',key='carteira_retry'): _snapshot.clear(); st.rerun()
        return
    st.iframe(html,height=900)
