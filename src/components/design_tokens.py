"""Tokens semânticos do Design System v1.0.1, sem regras de negócio.

A identidade institucional e a paleta da interface são distintas. Os
componentes legados mantêm suas cores até seus checkpoints de apresentação.
"""

COLOR = {
    "surface-page": "#F2F4F1",
    "surface-card": "#FFFFFF",
    "surface-muted": "#EEF1EE",
    "line-card": "#E6E9E5",
    "line-control": "#DCE1DD",
    "line-control-hover": "#BFC8C2",
    "line-divider": "#DCE2DD",
    "ink": "#13201B",
    "text-secondary": "#4D5A55",
    "text-muted": "#5F6B66",
    "text-meta": "#6B7772",
    "brand": "#0D5C4B",
    "brand-tint": "#E2F0EA",
    "brand-accent": "#2FA06B",
    "identity-green": "#66B82E",
    "identity-ink": "#111514",
    "identity-ivory": "#F7F4EE",
    "identity-white": "#FFFFFF",
    "focus-ring": "#0D5C4B",
    "focus-ring-dark": "#2FA06B",
    "positive": "#17794B",
    "positive-bg": "#E1F3E8",
    "positive-surface": "#EBF6EF",
    "positive-border": "#CDE6D7",
    "positive-label": "#115C39",
    "negative": "#B83232",
    "negative-bg": "#FBE6E3",
    "negative-surface": "#FCEFED",
    "negative-border": "#F2D2CE",
    "negative-label": "#8F2A2A",
    "warning": "#A8660A",
    "warning-bg": "#FBEFD9",
    "neutral-tile-bg": "#E8EDF2",
    "neutral-tile-fg": "#3E5568",
    "side-bg": "#0C1F1A",
    "side-text": "#C4D1CC",
    "side-text-strong": "#FFFFFF",
    "side-text-muted": "#8FA39B",
    "side-eyebrow": "#9DB0A8",
    "side-hover": "rgba(255,255,255,.06)",
    "side-active": "rgba(47,160,107,.16)",
    "side-divider": "rgba(255,255,255,.10)",
    "chart-previous": "#77837C",
    "chart-grid": "#DCE2DD",
    "chart-base": "#CBD3CD",
    "chart-hatch": "#D3DAD5",
    "chart-area-start": "rgba(13,92,75,.20)",
    "chart-area-end": "rgba(13,92,75,0)",
    "chart-highlight": "rgba(13,92,75,.05)",
    "chart-shadow": "rgba(12,31,26,.16)",
}

SPACE = {str(px): f"{px}px" for px in (4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 56)}
RADIUS = {
    "card": "16px", "insight": "14px", "tile": "12px",
    "control": "10px", "option": "8px", "pill": "99px",
}
SHADOW = {
    "card": "0 1px 2px rgba(12,31,26,.05)",
    "chart-label": "0 2px 6px rgba(12,31,26,.16)",
}
TYPOGRAPHY = {"family": '"Inter", Arial, Helvetica, sans-serif', "weights": (400, 500, 600, 700, 800)}
TYPE = {
    "page-size": "34px", "hero-size": "56px", "kpi-size": "26px",
    "radar-size": "24px", "section-size": "20px", "ranking-size": "18px",
    "support-size": "14px", "context-size": "13px", "control-size": "13px",
    "label-size": "11.5px", "badge-size": "12px", "metadata-size": "12px",
    "navigation-size": "14px", "navigation-weight": "600",
    "sidebar-quote-size": "21px", "sidebar-quote-weight": "600",
    "sidebar-identification-size": "12px",
}
SIDEBAR_WIDTH = 248


def css_variables() -> str:
    """Uma única paleta alimenta CSS; não cria tema ou seleção de tema."""
    declarations = [f"--atg-{key}:{value};" for key, value in COLOR.items()]
    for prefix, tokens in (("space", SPACE), ("radius", RADIUS), ("shadow", SHADOW), ("type", TYPE)):
        declarations.extend(f"--atg-{prefix}-{key}:{value};" for key, value in tokens.items())
    declarations.append(f'--atg-font:{TYPOGRAPHY["family"]};')
    return ":root{" + "".join(declarations) + "}"
