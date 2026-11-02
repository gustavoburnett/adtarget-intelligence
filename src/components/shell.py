"""Apresentação do shell compartilhado; sem fontes comerciais ou estado.

Os assets locais são incorporados ao HTML/CSS para dispensar CDN, servidor
de arquivos estáticos e mudanças de configuração no Streamlit Cloud.
"""

from base64 import b64encode
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from src.components.design_tokens import COLOR, TYPOGRAPHY

_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def font_style() -> str:
    font = b64encode((_ROOT / "static/fonts/InterVariable.woff2").read_bytes()).decode("ascii")
    return (
        '<style>@font-face{font-family:"Inter";font-style:normal;'
        'font-weight:100 900;font-display:swap;'
        f'src:url("data:font/woff2;base64,{font}") format("woff2");}}'
        f':root{{--atg-font:{TYPOGRAPHY["family"]};}}</style>'
    )


@lru_cache(maxsize=1)
def sidebar_brand() -> str:
    logo = b64encode((_ROOT / "assets/AdTarget_Intelligence_logo_negative.svg").read_bytes()).decode("ascii")
    return (
        '<div class="atg-sidebar-brand">'
        f'<img src="data:image/svg+xml;base64,{logo}" '
        'alt="AdTarget Intelligence" width="160" height="72"></div>'
    )


def sidebar_footer(sincronizado_em: datetime, minutos: int) -> str:
    return (
        '<div class="atg-sidebar-footer">'
        '<div class="atg-status-line"><span class="atg-status-dot" aria-hidden="true"></span>'
        f'Sincronizado às {sincronizado_em:%H:%M} · há {minutos} min</div>'
        '<div class="atg-sidebar-editorial">'
        '<p class="atg-sidebar-quote">Dados que impulsionam grandes negócios.</p>'
        '<p class="atg-sidebar-identification">AdTarget Intelligence<br>2026</p>'
        '</div></div>'
    )


_NAV_PATHS = {
    "Performance Comercial": '<path d="M5 19V12M12 19V5M19 19V9"/>',
    "Metas e Resultados": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    "Analítico Comercial": '<path d="m4 17 6-6 4 3 6-8M15 6h5v5"/>',
    "Analítico Veículos": '<rect x="3" y="7" width="18" height="14" rx="2"/><path d="m8 3 4 4 4-4"/>',
    "🔧 Auditoria (dev)": '<path d="m9 11 2 2 4-4M8 4H6a2 2 0 0 0-2 2v14h16V6a2 2 0 0 0-2-2h-2"/><rect x="8" y="2" width="8" height="4" rx="1"/>',
}


@lru_cache(maxsize=5)
def navigation_label(pagina: str) -> str:
    """Ícone decorativo em Markdown; o valor do radio continua a página real."""
    paths = _NAV_PATHS.get(pagina)
    if paths is None:
        return pagina
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{COLOR["side-text"]}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{paths}</svg>'
    )
    image = b64encode(svg.encode()).decode("ascii")
    return f'![](data:image/svg+xml;base64,{image}) {pagina.removeprefix("🔧 ")}'
