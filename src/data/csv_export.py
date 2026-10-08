"""CSV de auditoria: neutralização textual somente na cópia exportada."""

from __future__ import annotations

import pandas as pd


def _neutralizar_formula(valor: object) -> object:
    if not isinstance(valor, str):
        return valor
    # Defesa adicional para prefixos ocultos por whitespace Unicode, aspas,
    # BOM ou controles. Esses caracteres são preservados no arquivo; apenas
    # examinamos o primeiro caractere significativo antes de prefixá-lo.
    for caractere in valor:
        if (caractere.isspace() or caractere in '"\ufeff'
                or ord(caractere) < 32 or ord(caractere) == 127):
            continue
        if caractere in "=+-@":
            return "'" + valor
        break
    return valor


def gerar_csv_seguro(tabela: pd.DataFrame) -> bytes:
    """Preserva números e o original; prefixa textos de risco com apóstrofo.

    O apóstrofo é acrescentado antes do conteúdo original, inclusive seus
    espaços, aspas e quebras de linha. Somente o arquivo para download recebe
    essa proteção; valores numéricos negativos legítimos não são convertidos.
    """
    exportacao = tabela.copy(deep=True)
    for coluna in exportacao.columns:
        serie = exportacao[coluna]
        if serie.map(lambda valor: isinstance(valor, str)).any():
            exportacao[coluna] = serie.map(_neutralizar_formula, na_action="ignore")
    return exportacao.to_csv(index=False).encode("utf-8-sig")
