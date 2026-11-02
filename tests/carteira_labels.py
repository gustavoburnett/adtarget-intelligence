"""Normalização limitada aos textos visíveis aprovados para comparar checkpoints.

Não muda séries, números, filtros, engine ou contratos internos dos testes.
"""
REPLACEMENTS = {'Superávit YTD': 'Acima da meta acumulada', 'Déficit YTD': 'Abaixo da meta acumulada', 'Saldo YTD': 'Diferença para a meta acumulada', 'Realizado YTD no perímetro de metas': 'Vendas acumuladas no ano · no perímetro de metas', 'Meta YTD': 'Meta acumulada no ano', 'da meta YTD realizada': 'Atingimento da meta acumulada', '100% da meta YTD': '100% da meta acumulada no ano', 'Atingimento YTD não se aplica': 'Atingimento da meta acumulada não se aplica', 'ATINGIMENTO YTD': 'Atingimento da meta acumulada', 'KPI Principal · YTD vs Ano Anterior': 'Comparação com o mesmo período do ano anterior', 'YoY no perímetro de metas': 'Comparação com o mesmo período do ano anterior · no perímetro de metas', " YoY'": " em relação ao ano anterior'", "} YTD'": "} · acumulado no ano'", 'YoY:': 'Comparação com o ano anterior:'}

def visible_source(source):
    for old,new in REPLACEMENTS.items():
        source=source.replace(old,new)
    return source
