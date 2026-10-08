"""Integridade dos assets oficiais e identificação acessível, sem dados comerciais."""

import base64
import hashlib
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

import pytest

from src.components import partner_logos


EXPECTED_ASSETS = {
    "TEADS": "teads.webp", "DISNEY": "disney.png", "MELODIA": "melodia.png",
    "INFOMONEY": "infomoney.png", "CARREGA+": "carrega.png",
    "CLIMATEMPO": "climatempo.webp", "WEBEDIA": "webedia.png",
    "FORBES": "forbes.jpg", "BRASIL 247": "brasil-247.png", "HYPR": "hypr.jpg",
}


@pytest.fixture(autouse=True)
def _clear_logo_cache():
    partner_logos._data_uri.cache_clear()
    yield
    partner_logos._data_uri.cache_clear()


def _image_dimensions(data, mime_type):
    """Lê só cabeçalhos dos formatos recebidos, sem biblioteca nova ou edição."""
    if mime_type == "image/png":
        assert data.startswith(b"\x89PNG\r\n\x1a\n")
        return struct.unpack(">II", data[16:24])
    if mime_type == "image/webp":
        assert data[:4] == b"RIFF" and data[8:12] == b"WEBP"
        assert data[12:16] == b"VP8X"
        return (
            1 + int.from_bytes(data[24:27], "little"),
            1 + int.from_bytes(data[27:30], "little"),
        )
    assert mime_type == "image/jpeg" and data[:2] == b"\xff\xd8"
    index = 2
    while index < len(data):
        assert data[index] == 255
        while data[index] == 255:
            index += 1
        marker = data[index]
        index += 1
        length = int.from_bytes(data[index:index + 2], "big")
        if marker in (192, 193, 194):
            height, width = struct.unpack(">HH", data[index + 3:index + 7])
            return width, height
        index += length
    raise AssertionError("JPEG sem dimensões")


@pytest.mark.parametrize("grupo,file_name", EXPECTED_ASSETS.items())
def test_each_commercial_identifier_uses_exact_supplied_asset(grupo, file_name):
    logo = partner_logos.PARTNER_LOGOS[grupo]
    assert logo.file_name == file_name
    content = logo.path.read_bytes()
    # Os hashes correspondem aos arquivos fornecidos, antes da cópia local.
    assert hashlib.sha256(content).hexdigest() == logo.sha256
    html = ET.fromstring(partner_logos.partner_logo(grupo))
    image = html.find("img")
    assert image is not None
    header, encoded = image.get("src").split(",", 1)
    assert header == f"data:{logo.mime_type};base64"
    assert base64.b64decode(encoded) == content


@pytest.mark.parametrize("grupo", EXPECTED_ASSETS)
def test_original_proportions_and_optical_fit_keep_logo_content_visible(grupo):
    logo = partner_logos.PARTNER_LOGOS[grupo]
    assert _image_dimensions(logo.path.read_bytes(), logo.mime_type) == (
        logo.width, logo.height,
    )
    image = ET.fromstring(partner_logos.partner_logo(grupo)).find("img")
    assert int(image.get("width")) == logo.width
    assert int(image.get("height")) == logo.height
    styles = dict(item.split(":") for item in image.get("style").split(";"))
    assert "height" not in styles
    scale = float(styles["width"][:-2]) / logo.width
    x, y = (float(styles[key][:-2]) for key in ("left", "top"))
    left, top, right, bottom = logo.content_bounds
    assert x + left * scale >= 2.99
    assert x + right * scale <= partner_logos.LOGO_AREA[0] - 2.99
    assert y + top * scale >= 3.99
    assert y + bottom * scale <= partner_logos.LOGO_AREA[1] - 3.99
    assert "height:auto!important" in partner_logos.CSS_PARTNER_LOGOS
    assert "filter:" not in partner_logos.CSS_PARTNER_LOGOS
    assert "transform:" not in partner_logos.CSS_PARTNER_LOGOS


@pytest.mark.parametrize("grupo", EXPECTED_ASSETS)
def test_logo_has_accessible_source_name_without_repeated_visual_text(grupo):
    root = ET.fromstring(partner_logos.partner_logo(grupo))
    image = root.find("img")
    assert image.get("alt") == grupo
    assert image.get("aria-hidden") is None
    assert image.get("title") is None
    assert "".join(root.itertext()) == ""


@pytest.mark.parametrize("grupo", [
    "SISTEMA VERDES MARES", "PARCEIRO FUTURO", "RADIO MELODIA", "CARREGA++",
    '<Novo & Parceiro "Oficial">',
])
def test_unknown_identifier_uses_accessible_text_without_engine_rule(grupo):
    root = ET.fromstring(partner_logos.partner_logo(grupo))
    assert root.tag == "span"
    assert root.get("class") == "atg-partner-logo-fallback"
    assert root.text == grupo
    assert len(root) == 0


def test_missing_local_asset_falls_back_instead_of_loading_external_image(monkeypatch, tmp_path):
    monkeypatch.setattr(partner_logos, "ASSET_DIRECTORY", tmp_path)
    root = ET.fromstring(partner_logos.partner_logo("TEADS"))
    assert root.text == "TEADS"
    assert root.find("img") is None


def test_assets_are_local_and_mapping_does_not_import_engine_or_external_services():
    source = Path(partner_logos.__file__).read_text()
    assert "http://" not in source and "https://" not in source
    assert "src.data" not in source
    assert "requests" not in source and "urlopen" not in source
    assert set(path.name for path in partner_logos.ASSET_DIRECTORY.iterdir()) == set(
        EXPECTED_ASSETS.values()
    )
    assert partner_logos.PARTNER_LOGOS["DISNEY"].source_name == "images.png"
    assert "disney-plus-logo.png" not in source and "marvel-logo-4.png" not in source
    for line in partner_logos.CSS_PARTNER_LOGOS.splitlines():
        if "{" in line:
            assert line.startswith(".st-key-design_metas_content .atg-partner-logo")
