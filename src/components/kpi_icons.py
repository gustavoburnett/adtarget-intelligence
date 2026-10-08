"""Ícones vetoriais de apresentação dos indicadores da Performance Comercial."""


def _icone(conteudo: str) -> str:
    return (
        '<svg width="22" height="22" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="1.9" '
        'stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true" focusable="false">'
        f"{conteudo}</svg>"
    )


ICONES_KPI = {
    "vendas": _icone(
        '<path d="M12 3v18M16 7.5c-.8-1-2.2-1.5-4-1.5-2.2 0-4 1.1-4 3'
        's1.8 2.6 4 3 4 1.1 4 3-1.8 3-4 3c-1.8 0-3.2-.5-4-1.5"/>'
    ),
    "em-aberto": _icone(
        '<rect x="5" y="3" width="14" height="18" rx="2"/>'
        '<path d="M9 7h6M9 11h6M9 15h4"/>'
    ),
    "ticket": _icone(
        '<path d="M20.5 13.5 13.5 20.5a2 2 0 0 1-2.8 0L3 12.8V3h9.8'
        'l7.7 7.7a2 2 0 0 1 0 2.8Z"/>'
        '<circle cx="7.5" cy="7.5" r="1"/>'
    ),
    "campanhas": _icone(
        '<path d="m8 9 11-4v14L8 15H4a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1h4Z'
        'M8 9v6m-2 0 1.5 6h3L9 15M22 9v6"/>'
    ),
    "cancelado": _icone(
        '<circle cx="12" cy="12" r="8"/>'
        '<path d="m6.4 6.4 11.2 11.2"/>'
    ),
    "alertas": _icone(
        '<path d="m12 3 9 17H3Z"/>'
        '<path d="M12 9v4M12 16h.01"/>'
    ),
}


TRIANGULOS_HERO = {
    "▲": '<path d="M12 3 22 21H2Z"/>',
    "▼": '<path d="M2 3h20L12 21Z"/>',
}
