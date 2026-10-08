"""Ícones lineares decorativos do Radar Executivo, sem dependência externa."""


def _icone(conteudo: str) -> str:
    return (
        '<svg width="24" height="24" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true" focusable="false">'
        f"{conteudo}</svg>"
    )


ICONES_RADAR = {
    "queda": _icone('<path d="M12 5v14m-6-6 6 6 6-6"/>'),
    "crescimento": _icone('<path d="M12 19V5m-6 6 6-6 6 6"/>'),
    # Destaque mensal: estrela somente em contorno, com a paleta neutra do DS.
    "destaque": _icone(
        '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3'
        'l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9Z"/>'
    ),
}
