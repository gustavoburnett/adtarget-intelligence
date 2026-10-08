"""Fundação visual local: assets, acessibilidade e navegação nativa, offline."""

from base64 import b64decode
import datetime as dt
from html.parser import HTMLParser
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pandas as pd
import pytest
import streamlit as st

from src.components import cards, design_styles, shell
from src.components.design_tokens import COLOR
from tests.test_metas_app_routing import PAGINAS_PRINCIPAIS, _entrada


ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "assets/AdTarget_Intelligence_logo.svg"
NEGATIVO = LOGO.with_name("AdTarget_Intelligence_logo_negative.svg")


class _Texto(HTMLParser):
    def __init__(self):
        super().__init__()
        self.partes = []

    def handle_data(self, data):
        self.partes.append(data)


@pytest.fixture(autouse=True)
def _cache_isolado():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def test_variante_negativa_altera_somente_as_duas_cores_autorizadas():
    original = list(ET.fromstring(LOGO.read_bytes()).iter())
    negativo = list(ET.fromstring(NEGATIVO.read_bytes()).iter())
    assert len(original) == len(negativo)
    alteracoes = []
    for antes, depois in zip(original, negativo, strict=True):
        assert antes.tag == depois.tag
        assert antes.text == depois.text
        assert antes.tail == depois.tail
        atributos_antes, atributos_depois = dict(antes.attrib), dict(depois.attrib)
        if atributos_antes.get("fill") != atributos_depois.get("fill"):
            assert atributos_antes.pop("fill") == COLOR["identity-ink"]
            esperado = (
                COLOR["side-eyebrow"]
                if antes.get("id") == "product-descriptor"
                else COLOR["identity-ivory"]
            )
            assert atributos_depois.pop("fill") == esperado
            alteracoes.append(esperado)
        assert atributos_antes == atributos_depois
    assert alteracoes == [COLOR["identity-ivory"], COLOR["side-eyebrow"]]
    assert any(elemento.get("fill") == COLOR["identity-green"] for elemento in negativo)


def test_fonte_inter_local_e_licenca_sao_entregues_sem_cdn():
    estilo = shell.font_style()
    fonte = re.search(r'data:font/woff2;base64,([A-Za-z0-9+/=]+)', estilo)
    assert fonte is not None
    bytes_fonte = b64decode(fonte.group(1), validate=True)
    assert bytes_fonte == (ROOT / "static/fonts/InterVariable.woff2").read_bytes()
    assert bytes_fonte.startswith(b"wOF2")
    assert 'font-family:"Inter"' in estilo
    assert 'Arial, Helvetica, sans-serif' in estilo
    assert 'font-display:swap' in estilo
    assert "https://" not in estilo and "http://" not in estilo
    licenca = (ROOT / "static/fonts/OFL-Inter.txt").read_text()
    assert "SIL OPEN FONT LICENSE" in licenca


def test_sidebar_preserva_timestamp_real_e_somente_editoriais_aprovados():
    for horario, minutos in ((dt.datetime(2026, 10, 7, 12, 34), 0),
                             (dt.datetime(2026, 10, 7, 8, 15), 259)):
        html = shell.sidebar_footer(horario, minutos)
        texto = _Texto()
        texto.feed(html)
        assert texto.partes == [
            f"Sincronizado às {horario:%H:%M} · há {minutos} min",
            "Dados que impulsionam grandes negócios.",
            "AdTarget Intelligence", "2026",
        ]
        assert "<svg" not in html and "<img" not in html
        assert "Inteligência em mídia. Resultados no seu negócio." not in html
        assert "Sprint" not in html and "v1." not in html


@pytest.mark.parametrize("auditoria", [False, True])
def test_icones_nao_alteram_valores_do_radio_roteamento_ou_leitura_das_fontes(
    monkeypatch, auditoria,
):
    app, vendas, _, leituras, renders = _entrada(
        monkeypatch, "Performance Comercial", auditoria=auditoria,
    )
    antes = vendas.copy(deep=True)
    destinos = PAGINAS_PRINCIPAIS + (["🔧 Auditoria (dev)"] if auditoria else [])
    for destino in destinos:
        app.radio(key="nav_pagina").set_value(destino).run(timeout=20)
        assert not app.exception
        navegacao = app.radio(key="nav_pagina")
        assert navegacao.value == destino
        assert app.session_state["nav_pagina"] == destino
        assert navegacao.index == destinos.index(destino)
        assert renders[-1][0] == destino
        pd.testing.assert_frame_equal(renders[-1][1], antes)
        assert navegacao.options == [shell.navigation_label(nome) for nome in destinos]
        assert all(opcao.endswith(" " + nome.removeprefix("🔧 "))
                   for opcao, nome in zip(navegacao.options, destinos, strict=True))
    assert leituras == {"vendas": 1, "metas": 1}
    pd.testing.assert_frame_equal(vendas, antes)


def _luminancia(hexadecimal):
    rgb = [int(hexadecimal[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [canal / 12.92 if canal <= 0.04045 else ((canal + 0.055) / 1.055) ** 2.4
              for canal in rgb]
    return sum(canal * peso for canal, peso in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))


@pytest.mark.parametrize("frente,fundo,minimo", [
    ("side-text", "side-bg", 4.5),
    ("side-text-muted", "side-bg", 4.5),
    ("side-eyebrow", "side-bg", 4.5),
    ("focus-ring-dark", "side-bg", 3.0),
    ("focus-ring", "surface-page", 3.0),
])
def test_contraste_da_sidebar_e_foco_atende_minimo(frente, fundo, minimo):
    luminosidades = sorted((_luminancia(COLOR[frente]), _luminancia(COLOR[fundo])))
    assert (luminosidades[1] + 0.05) / (luminosidades[0] + 0.05) >= minimo


def test_estilo_nao_oculta_input_nativo_ou_controle_de_reabertura():
    # AppTest não executa CSS: o fechamento/reabertura é validado no navegador.
    # Esta proteção evita retirar o input da árvore acessível por acidente.
    css = re.sub(r'/\*.*?\*/', '', design_styles.CSS_SHELL, flags=re.DOTALL)
    for seletor, declaracoes in re.findall(r'([^{}]+)\{([^}]+)\}', css):
        if "input" in seletor:
            assert "display:none" not in declaracoes.replace(" ", "")
            assert "visibility:hidden" not in declaracoes.replace(" ", "")
    regras_reabrir = re.findall(r'[^{}]*stExpandSidebarButton[^{}]*\{([^}]+)\}',
                               cards.CSS_GLOBAL + css)
    assert regras_reabrir
    assert all("display:none" not in regra.replace(" ", "") and
               "visibility:hidden" not in regra.replace(" ", "")
               for regra in regras_reabrir)


def test_wrapper_da_tabela_nao_recorta_toolbar_nativa():
    # Streamlit posiciona a toolbar acima do wrapper. AppTest não executa CSS;
    # o download e a rolagem continuam exigindo a prova real no navegador.
    from src.components import analitico_styles, veiculos_styles

    css = re.sub(r'/\*.*?\*/', '', cards.CSS_GLOBAL + design_styles.CSS_SHELL
                 + analitico_styles.CSS_ANALITICO_COMERCIAL
                 + veiculos_styles.CSS_VEICULOS, flags=re.DOTALL)
    regras = [declaracoes for seletor, declaracoes
              in re.findall(r'([^{}]+)\{([^}]+)\}', css)
              if '[data-testid="stDataFrame"]' in seletor]
    assert regras
    for declaracoes in regras:
        for propriedade, valor in re.findall(r'([\w-]+)\s*:\s*([^;]+)', declaracoes):
            if propriedade in {"overflow", "overflow-x", "overflow-y"}:
                assert valor.strip() == "visible"
    assert 'border:1px solid #F0F2F4;border-radius:12px;' in cards.CSS_GLOBAL
