"""Adaptador de consulta da Carteira; usa exclusivamente os contratos oficiais.

Sem I/O, rateio, deduplicação ou alteração das fontes. Valores em Decimal
até serialização. A classificação é mensal, obtida de MesMetas.perimetro.
"""
from decimal import Decimal
import pandas as pd
from src.data import metas as engine, metrics
from src.data.cleaning import COL_GRUPO, COL_VEICULO, COL_PI, COL_CLIENTE, COL_AGENCIA, COL_CAMPANHA, COL_STATUS, COL_VALOR_LIQUIDO
from src.data.metas_schema import normalizar_entidade
from src.components.monthly_groups_data import _mascara_perimetro, grupos_disponiveis

ZERO = Decimal(0)

def dinheiro(df):
    return Decimal(str(metrics.vendas(df, 'liquido')))

def preparar(vendas, metas, *, data_referencia=None, anos=None, pis_conferidos=()):
    referencia = engine.data_local(data_referencia)
    df = vendas.copy(deep=True).reset_index(drop=True)
    for col in (COL_GRUPO, COL_VEICULO):
        df[col] = df[col].map(normalizar_entidade)
    # Não perder linhas elegíveis sem grupo; o seletor recebe um nome explícito.
    df[COL_GRUPO] = df[COL_GRUPO].replace('', 'SEM PARCEIRO INFORMADO')
    vigente = engine.vigencia(metas, data_referencia=referencia)
    temporal = metrics.coluna_mes('veiculacao')
    anos = sorted(set(anos or [*df[temporal].dropna().dt.year.tolist(), *vigente.ANO.tolist(), referencia.year, referencia.year+1]))
    anos = sorted(set(anos) | {min(anos)-1})
    eligible = df.loc[metrics.mascara_vendas(df) & df[temporal].notna()].copy()
    eligible['__inside'] = False
    groups_by_year, monthly = {}, {}
    for year in anos:
        groups = grupos_disponiveis(df, vigente, year, data_referencia=referencia)
        groups_by_year[str(year)] = list(groups)
        for group in groups:
            plano = vigente.loc[vigente.GRUPO == group]
            base = engine.avaliar_metas(df, plano, year, data_referencia=referencia)
            pulso = engine.avaliar_pulso(df, plano, year, data_referencia=referencia)
            for month, pulse in zip(base.meses, pulso.meses, strict=True):
                rows = eligible.loc[(eligible[temporal].dt.year == year) & (eligible[temporal].dt.month == month.mes) & (eligible[COL_GRUPO] == group)]
                mask = _mascara_perimetro(rows, month)
                eligible.loc[rows.index, '__inside'] = mask
                total = dinheiro(rows)
                monthly[(year, group, month.mes)] = dict(total=total, inside=pulse.vendido, out=total-pulse.vendido, target=month.meta if month.estado_meta in ('ativa','zero_ativa') else None, status=month.estado_meta, phase=month.estado_mes)
    rows = []
    for index, row in eligible.iterrows():
        def text(col):
            value = row.get(col, '')
            return '' if pd.isna(value) else str(value)
        rows.append(dict(id=int(index), year=int(row[temporal].year), month=int(row[temporal].month), group=text(COL_GRUPO), pi=text(COL_PI), client=text(COL_CLIENTE), agency=text(COL_AGENCIA), vehicle=text(COL_VEICULO), campaign=text(COL_CAMPANHA), status=text(COL_STATUS), value=float(Decimal(str(row[COL_VALOR_LIQUIDO]))*100), inside=bool(row['__inside']), flag=text(COL_PI) in pis_conferidos))
    slices = {}
    for year in anos:
        for group in ['', *groups_by_year[str(year)]]:
            gs = [group] if group else groups_by_year[str(year)]
            for grain in (1,3,6,12):
                for first in range(1,13,grain):
                    ms = range(first,first+grain)
                    cells = [monthly[(year,g,m)] for g in gs for m in ms]
                    target_cells = [c['target'] for c in cells if c['target'] is not None]
                    total = sum((c['total'] for c in cells), ZERO)
                    inside = sum((c['inside'] for c in cells), ZERO)
                    target = sum(target_cells,ZERO) if target_cells else None
                    old_rows = eligible.loc[(eligible[temporal].dt.year == year-1) & eligible[temporal].dt.month.isin(ms)]
                    if group: old_rows = old_rows.loc[old_rows[COL_GRUPO] == group]
                    missing = [f'{g} · {m:02d}/{year}: {monthly[(year,g,m)]["status"]}' for g in gs for m in ms if monthly[(year,g,m)]['status'] not in ('ativa','zero_ativa')]
                    inactive = bool(cells) and all(c['status']=='inativa' for c in cells)
                    key = f'{year}|{group}|{first}|{grain}'
                    def cents(v): return None if v is None else float(v*100)
                    slices[key] = dict(total=cents(total),inside=cents(inside),out=cents(total-inside),target=cents(target),gap=cents(-engine.diferenca_monetaria(inside,target)) if target is not None and target>0 else None,coverage=float(inside/target*100) if target is not None and target>0 else None,old=cents(dinheiro(old_rows)),hasOld=bool(len(old_rows)),partial=bool(target_cells and missing),missing=missing,inactive=inactive)
    return dict(reference=referencia.isoformat(),years=anos,groupsByYear=groups_by_year,rows=rows,slices=slices,unassignedMonth=int((metrics.mascara_vendas(df)&df[temporal].isna()).sum()))
