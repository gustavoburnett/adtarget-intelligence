"""Marca oficial e navegação compartilhada, sem carregar a fonte real."""

from base64 import b64decode
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pytest
import streamlit as st

from src.components import cards
from tests.test_metas_app_routing import PAGINAS_PRINCIPAIS, _entrada


LOGO = Path(__file__).resolve().parents[1] / "assets" / "AdTarget_Intelligence_logo.svg"
LOGO_NEGATIVO = LOGO.with_name("AdTarget_Intelligence_logo_negative.svg")
HASH_LOGO_OFICIAL = "7c5e3f4dcad089928ab97571f30737d4229e21231bc32279cca0f093325bec54"


class _Imagens(HTMLParser):
    def __init__(self):
        super().__init__()
        self.imagens = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.imagens.append(dict(attrs))


@pytest.fixture(autouse=True)
def _cache_independente_por_teste():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def test_asset_preserva_svg_oficial_sem_redesenho_ou_dependencia_externa():
    svg = LOGO.read_bytes()
    assert sha256(svg).hexdigest() == HASH_LOGO_OFICIAL
    raiz = ET.fromstring(svg)
    assert raiz.attrib["viewBox"] == "40 45 700 315"
    assert {elemento.tag.rsplit("}", 1)[-1] for elemento in raiz.iter()} == {
        "svg", "title", "g", "path",
    }
    assert all("href" not in atributo for elemento in raiz.iter() for atributo in elemento.attrib)


@pytest.mark.parametrize("pagina", PAGINAS_PRINCIPAIS + ["🔧 Auditoria (dev)"])
def test_marca_negativa_oficial_aparece_na_sidebar_em_todas_as_paginas(monkeypatch, pagina):
    app, _, _, _, _ = _entrada(monkeypatch, pagina, auditoria=True)
    assert not app.exception
    blocos = [elemento.value for elemento in app.markdown]
    assert any('class="atg-h1"' in html for html in blocos)
    assert not any('class="atg-product-brand"' in html for html in blocos)
    sidebar = "\n".join(elemento.value for elemento in app.sidebar.markdown)
    parser = _Imagens()
    parser.feed(sidebar)
    assert len(parser.imagens) == 1
    imagem = parser.imagens[0]
    assert imagem["alt"] == "AdTarget Intelligence"
    prefixo, conteudo = imagem["src"].split(",", 1)
    assert prefixo == "data:image/svg+xml;base64"
    assert b64decode(conteudo, validate=True) == LOGO_NEGATIVO.read_bytes()
    assert "atg-logo-word" not in sidebar
    assert "atg-logo-sub" not in sidebar


def test_header_nao_remove_controle_nativo_de_reabertura_da_sidebar():
    css = cards.CSS_GLOBAL
    header = re.search(r'header\[data-testid="stHeader"\]\{([^}]+)\}', css).group(1)
    controle = re.search(
        r'header\[data-testid="stHeader"\] \[data-testid="stExpandSidebarButton"\]\{([^}]+)\}',
        css,
    ).group(1)
    assert "display:none" not in header
    assert "visibility:visible" in controle
