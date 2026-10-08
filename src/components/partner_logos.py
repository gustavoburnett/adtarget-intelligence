"""Marcas oficiais do Design 1F, sem acoplamento aos cálculos de metas.

Os arquivos são cópias integrais dos assets fornecidos. O posicionamento CSS
compensa suas margens vazias sem modificar pixels, cores ou proporções. O
mapeamento identifica somente a marca; elegibilidade e ordem vêm da engine.
"""

import base64
from dataclasses import dataclass
from functools import lru_cache
from html import escape
from pathlib import Path
from types import MappingProxyType


ASSET_DIRECTORY = Path(__file__).resolve().parents[2] / "assets" / "partners"
LOGO_AREA = (116, 44)


@dataclass(frozen=True)
class PartnerLogo:
    """Dimensões originais e área visual usadas somente para ajuste óptico."""

    official_name: str
    file_name: str
    source_name: str
    mime_type: str
    width: int
    height: int
    content_bounds: tuple[int, int, int, int]
    sha256: str

    @property
    def path(self) -> Path:
        return ASSET_DIRECTORY / self.file_name


PARTNER_LOGOS = MappingProxyType({
    "TEADS": PartnerLogo(
        "Teads", "teads.webp", "lg-69f92e0213ca3-Teads.webp", "image/webp",
        550, 550, (21, 213, 530, 337),
        "d4b4c642345d36724ae23b260ef058811c0a543b15998ad6fe63bb46fd28add1",
    ),
    "DISNEY": PartnerLogo(
        "Disney", "disney.png", "images.png", "image/png",
        # Asset oficial com fundo branco; a marca é preservada integralmente.
        738, 312, (0, 0, 738, 312),
        "991f936f0a6813ac88694594ab657f91ba58b7ee002dae6057683e7ce636ba9a",
    ),
    "MELODIA": PartnerLogo(
        "Melodia", "melodia.png", "650226e6ce32f.png", "image/png",
        500, 238, (18, 32, 480, 197),
        "7b3296a41e6692214f7b769b1885a7a1f8e4e72ac53741b29ceaf5d326063546",
    ),
    "INFOMONEY": PartnerLogo(
        "InfoMoney", "infomoney.png", "images - cópia.png", "image/png",
        738, 147, (0, 0, 738, 147),
        "94d145a725f8b4fcd2b9da14935d96807a281ffe6df4bbe25ce9871de8be63ba",
    ),
    "CARREGA+": PartnerLogo(
        "Carrega+", "carrega.png", "carrega.png", "image/png",
        600, 300, (86, 101, 514, 199),
        "53bc097d9fca222df243514bf92ac7aa2f7797c9d8bee0a30507df73ddad3b78",
    ),
    "CLIMATEMPO": PartnerLogo(
        "Climatempo", "climatempo.webp", "climatempo.png.webp", "image/webp",
        600, 360, (26, 142, 578, 219),
        "d7ef7a1933fa26a01623781642b142a8d0d2d8293b8ccff83eb46cdc5c70ee66",
    ),
    "WEBEDIA": PartnerLogo(
        "Webedia", "webedia.png", "Webedia_-_Main_Logo_Blue.png", "image/png",
        1920, 324, (0, 0, 1920, 324),
        "b4d72bcd3fce75fff378befdfae11d92ff5affae088dc8d74f55b3c0aab97c02",
    ),
    "FORBES": PartnerLogo(
        "Forbes", "forbes.jpg", "Forbes-Logo-1999-presente.jpg", "image/jpeg",
        1920, 1080, (88, 313, 1832, 768),
        "5b67f9a30b07913c6bcf8252226090b22078dff2f8be5661df39a9293dec5a65",
    ),
    "BRASIL 247": PartnerLogo(
        "Brasil 247", "brasil-247.png", "Logo_Brasil_247_2024.png", "image/png",
        923, 264, (0, 0, 923, 252),
        "f70b68058c9cff1ec4f76e9e55a46f983e4d7b2e924915480190b1bc7e133734",
    ),
    "HYPR": PartnerLogo(
        "HYPR", "hypr.jpg", "oie_NmGISpHyvZgm.jpg", "image/jpeg",
        800, 500, (286, 230, 514, 272),
        "10030025d4f540174d11e1e4aaebd479b55e0efe15a40e74d2e7cf22bc58fac9",
    ),
})


CSS_PARTNER_LOGOS = """
.st-key-design_metas_content .atg-partner-logo {
  position:relative;display:block;flex:none;width:116px;height:44px;
  overflow:hidden;background:transparent;border:0;box-shadow:none;}
.st-key-design_metas_content .atg-partner-logo-image {
  position:absolute;display:block;max-width:none!important;
  max-height:none!important;height:auto!important;
  border:0;border-radius:0;box-shadow:none;}
.st-key-design_metas_content .atg-partner-logo-fallback {
  display:flex;align-items:center;min-height:44px;width:116px;max-width:100%;
  color:var(--atg-ink);font-family:var(--atg-font);font-weight:700;
  font-size:13px;line-height:1.25;overflow-wrap:anywhere;}
"""


def _optical_style(logo: PartnerLogo) -> str:
    """Fit de conteúdo com espaço de segurança; só margens vazias são cortadas."""
    left, top, right, bottom = logo.content_bounds
    scale = min(110 / (right - left), 36 / (bottom - top))
    x = (LOGO_AREA[0] - (right - left) * scale) / 2 - left * scale
    y = (LOGO_AREA[1] - (bottom - top) * scale) / 2 - top * scale
    return f"width:{logo.width * scale:.4f}px;left:{x:.4f}px;top:{y:.4f}px"


@lru_cache(maxsize=32)
def _data_uri(path: Path, mime_type: str) -> str:
    content = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{content}"


def partner_logo(grupo: str) -> str:
    """HTML acessível da marca oficial ou texto para qualquer parceiro novo.

    O identificador da fonte não é corrigido ou convertido neste componente.
    Asset ausente usa o mesmo fallback, sem buscar uma imagem na rede.
    """
    name = str(grupo)
    logo = PARTNER_LOGOS.get(name)
    if logo is not None:
        try:
            uri = _data_uri(logo.path, logo.mime_type)
        except OSError:
            pass
        else:
            return (
                '<span class="atg-partner-logo">'
                f'<img class="atg-partner-logo-image" src="{uri}" '
                f'alt="{escape(name, quote=True)}" width="{logo.width}" '
                f'height="{logo.height}" style="{_optical_style(logo)}" />'
                '</span>'
            )
    return (
        '<span class="atg-partner-logo-fallback">'
        f'{escape(name) if name else "Parceiro sem identificação"}</span>'
    )
