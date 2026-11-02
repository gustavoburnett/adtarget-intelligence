"""Checkpoint 2B: exploração mensal nativa sobre os contratos já homologados.

O seletor afeta exclusivamente esta seção. Nenhum filtro global, fonte ou
contrato financeiro é alterado. HTML serve somente para a apresentação;
grupo, perspectivas, seleção de mês e gráficos são widgets nativos.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from html import escape

import pandas as pd
import streamlit as st

from src.components import cards, monthly_groups_charts
from src.components.monthly_groups_data import (
    GrupoMensal, MesGrupo, contribuicoes_grupo, grupos_disponiveis, preparar_grupo,
)
from src.components.monthly_groups_styles import CSS
from src.components.partner_logos import partner_logo
from src.data.metas import Referencia

MESES = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")
_ESTADOS = {"encerrado": "Mês encerrado", "em_andamento": "Em andamento", "futuro": "Futuro"}
_PERIODO = "_group_monthly_periodo"
_MES = "_group_monthly_mes"


def _moeda(valor: Decimal) -> str:
    completo = cards.formatar_moeda(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return (f'<span class="num" title="{escape(completo, quote=True)}">'
            f'{escape(cards.formatar_moeda_executiva(valor))}</span>')


def _pct(valor: Decimal) -> str:
    return f'{valor.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP):.1f}'.replace('.', ',') + '%'


def _periodo(meses: list[int], ano: int) -> str:
    if not meses:
        return str(ano)
    if len(meses) == 1:
        return f'{MESES[meses[0] - 1]}/{ano}'
    if meses == list(range(meses[0], meses[-1] + 1)):
        return f'{MESES[meses[0] - 1]} a {MESES[meses[-1] - 1]}/{ano}'
    return ', '.join(MESES[mes - 1] for mes in meses) + f'/{ano}'


def _resumo(modelo: GrupoMensal, ativo: bool, contexto: str | None) -> str:
    resultado = modelo.resultado
    parceiro = modelo.parceiro
    rotulos = {
        "acima_da_meta": ("↑ Acima do ritmo", "positive"),
        "proximo_da_meta": ("≈ No ritmo", "neutral"),
        "abaixo_da_meta": ("↓ Abaixo do ritmo", "negative"),
        "sem_meta_periodo": ("Sem meta no período", "neutral"),
        "aguardando_mes_encerrado": ("Aguardando mês encerrado", "neutral"),
    }
    rotulo, classe = rotulos[parceiro.status] if parceiro else ("Sem meta cadastrada", "neutral")
    if modelo.tem_metas and not ativo:
        rotulo, classe = contexto or "Sem meta ativa no período", "neutral"
    logo = partner_logo(modelo.grupo)
    identidade = (f'<div class="atg-group-identity">{logo}'
                  f'<span class="atg-group-badge {classe}">{escape(rotulo)}</span></div>')
    meses_fechados = [m.mes for m in resultado.meses if m.estado_mes == "encerrado" and m.perimetro]
    pct = parceiro.atingimento_ytd_pct if parceiro else None
    if pct is None:
        titulo = "Sem meta" if not modelo.tem_metas else "Sem base de comparação"
        principal = f'<div class="atg-group-ytd-number neutral">{titulo}</div>'
        apoio = ('Atingimento YTD não se aplica' if not modelo.tem_metas else
                 'Aguardando mês encerrado' if not resultado.meses_encerrados else
                 'Não há meta positiva nos meses encerrados.')
        regua = ""
    else:
        principal = f'<div class="atg-group-ytd-number {classe}">{"▲ " if pct > 100 else ""}{_pct(pct)}</div>'
        apoio = (f'<strong>{_moeda(parceiro.realizado_ytd)}</strong> realizado · '
                 f'<strong>{_moeda(parceiro.meta_ytd)}</strong> meta acumulada '
                 f'{_periodo(meses_fechados, modelo.ano)}')
        largura = min(Decimal(100), max(Decimal(0), pct / Decimal(125) * 100))
        regua = (f'<div class="atg-group-ytd-track" aria-hidden="true"><span style="width:{largura:.2f}%"></span></div>'
                 '<div class="atg-group-ruler">100% da meta YTD'
                 + (' · Acima da escala de 125%' if pct > 125 else '') + '</div>')
    esquerda = (f'<div class="atg-group-ytd">{identidade}<div class="atg-group-label">ATINGIMENTO YTD</div>'
                f'{principal}<div class="atg-group-copy">{apoio}</div>{regua}</div>')
    if not modelo.tem_metas:
        direita = (f'<div><div class="atg-group-label">VENDAS EM {modelo.ano}</div>'
                   f'<div class="atg-group-annual-line"><div class="atg-group-annual-number">{_moeda(modelo.total_vendido_ano)}</div></div>'
                   f'<div class="atg-group-label">META ANUAL · {modelo.ano}</div>'
                   '<p class="atg-group-gap-copy">Meta anual não cadastrada</p>'
                   '<div class="atg-group-copy">Gap comercial e percentual da meta anual não se aplicam. '
                   'As vendas podem ser consultadas no gráfico mensal.</div></div>')
    else:
        anual = modelo.pulso
        cobertura = anual.percentual_meta_ja_vendida
        meses_ativos = [m.mes for m in resultado.meses if m.perimetro]
        vigencia = f' · Vigência {_periodo(meses_ativos, modelo.ano)}' if meses_ativos and len(meses_ativos) < 12 else ''
        gap = modelo.gap_comercial
        texto_gap = ('Meta anual superada em ' + _moeda(abs(gap)) if gap is not None and gap < 0 else
                     'Meta anual atingida' if gap == 0 else
                     'Gap comercial ' + _moeda(gap) if gap is not None else
                     'Sem meta anual positiva para comparar')
        percentagem = (f'<strong>{_pct(cobertura)}</strong> da meta anual de {_moeda(anual.meta_anual)}'
                       if cobertura is not None else 'Meta anual ativa com valor zero · sem base para percentual')
        fechado = max(Decimal(0), modelo.realizado_ytd)
        aberto = max(Decimal(0), modelo.carteira_futura)
        falta = max(Decimal(0), gap or Decimal(0))
        escala = fechado + aberto + falta
        barra = ''.join(f'<span class="atg-group-{nome}" style="width:{valor / escala * 100:.4f}%"></span>'
                        for nome, valor in (("closed", fechado), ("open", aberto), ("gap", falta))) if escala else ''
        meses_abertos_ativos = [m.mes for m in resultado.meses if m.estado_mes != 'encerrado' and m.perimetro]
        periodo_aberto = _periodo(meses_abertos_ativos, modelo.ano)
        legenda = (f'<span class="atg-group-key-item"><i class="atg-group-swatch atg-group-closed" aria-hidden="true"></i>'
                   f'Realizado {_periodo(meses_fechados, modelo.ano)}</span>')
        if meses_abertos_ativos:
            legenda += (f'<span class="atg-group-key-item"><i class="atg-group-swatch atg-group-open" aria-hidden="true"></i>'
                        f'Já vendido {periodo_aberto} <strong>{_moeda(modelo.carteira_futura)}</strong></span>')
        if gap is not None and gap > 0:
            legenda += '<span class="atg-group-key-item"><i class="atg-group-swatch atg-group-gap" aria-hidden="true"></i>Falta vender</span>'
        fora = (f'<div class="atg-group-outside">Fora do perímetro de metas · não somado ao atingimento oficial '
                f'<strong>{_moeda(modelo.fora_perimetro_anual)}</strong></div>'
                if modelo.fora_perimetro_anual != 0 else '')
        direita = (f'<div><div class="atg-group-label">META ANUAL · {modelo.ano}{vigencia}</div>'
                   f'<div class="atg-group-annual-line"><div class="atg-group-annual-number">{_moeda(modelo.total_vendido_ano)} '
                   f'<small>já vendidos</small></div><div class="atg-group-copy">{percentagem}</div></div>'
                   f'<div class="atg-group-annual-track" aria-hidden="true">{barra}</div>'
                   f'<div class="atg-group-gap-copy"><strong>{texto_gap}</strong></div>'
                   f'<div class="atg-group-key">{legenda}</div>{fora}</div>')
    return f'<div class="atg-group-summary" aria-label="Resumo do grupo {escape(modelo.grupo, quote=True)}">{esquerda}{direita}</div>'


def _detalhe(mes: MesGrupo, ano: int) -> str:
    campos: list[tuple[str, str]] = []
    if mes.meta is not None:
        campos.append(("Meta mensal vigente", _moeda(mes.meta)))
    if mes.estado_meta == "inativa":
        mensagem = 'Fora de vigência. As vendas deste mês não são somadas ao atingimento oficial.'
    elif mes.estado_meta == "ausente" and mes.fora_perimetro != 0:
        mensagem = 'Sem meta cadastrada neste mês. As vendas estão fora do perímetro de metas.'
    elif mes.registros == 0:
        mensagem = 'Sem registros elegíveis no perímetro selecionado. Isso não comprova venda zero e não gera atingimento nem desvio.'
    else:
        mensagem = 'Sem meta cadastrada neste mês.' if mes.meta is None else ''
        fechado = mes.estado_mes == 'encerrado'
        campos.append(('Vendas do mês · realizado' if fechado else 'Já vendido · carteira', _moeda(mes.vendido)))
        if mes.atingimento_pct is not None:
            campos.append(('Atingimento' if fechado else 'Cobertura já vendida', _pct(mes.atingimento_pct)))
        if mes.desvio is not None:
            if fechado:
                campos.append(('Diferença para a meta', ('+' if mes.desvio > 0 else '−' if mes.desvio < 0 else '') + _moeda(abs(mes.desvio))))
            else:
                campos.append(('Acima da meta já vendido' if mes.desvio > 0 else 'Falta cobrir (não é déficit)', _moeda(abs(mes.desvio))))
        if mes.meta == 0:
            mensagem = 'Meta ativa com valor zero · sem base para percentual.'
    if mes.fora_perimetro != 0:
        campos.append(('Vendas fora do perímetro', _moeda(mes.fora_perimetro)))
    valores = ''.join(f'<dt>{escape(titulo)}</dt><dd>{valor}</dd>' for titulo, valor in campos)
    return (f'<section class="atg-group-detail" aria-label="Detalhe {MESES[mes.mes - 1]}/{ano}">'
            f'<div class="atg-group-detail-head"><strong>{MESES[mes.mes - 1]}/{ano}</strong>'
            f'<span class="atg-group-copy">{_ESTADOS[mes.estado_mes]}</span></div>'
            + (f'<p class="atg-group-copy">{mensagem}</p>' if mensagem else '')
            + f'<dl>{valores}</dl></section>')


def _veiculos(modelo: GrupoMensal, mes: int | None) -> str:
    veiculos = contribuicoes_grupo(modelo, mes)
    total = modelo.total_vendido_ano if mes is None else modelo.meses[mes - 1].vendido
    positivo = sum((max(Decimal(0), v.valor) for v in veiculos), Decimal(0))
    maior = max((abs(v.valor) for v in veiculos), default=Decimal(0))
    partes, linhas = [], []
    for i, veiculo in enumerate(veiculos):
        cor = f'color-mix(in srgb,var(--atg-brand) {max(25, 100 - i * 15)}%,white)'
        if positivo and veiculo.valor > 0:
            partes.append(f'<span style="width:{veiculo.valor / positivo * 100:.4f}%;background:{cor}"></span>')
        largura = abs(veiculo.valor) / maior * 100 if maior else Decimal(0)
        percentual = _pct(veiculo.percentual) if veiculo.percentual is not None else '—'
        linhas.append(f'<div class="atg-group-vehicle-row" role="listitem">'
                      f'<span class="atg-group-vehicle-name" title="{escape(veiculo.veiculo, quote=True)}">{escape(veiculo.veiculo)}</span>'
                      f'<div class="atg-group-vehicle-bar" aria-hidden="true"><span style="width:{largura:.4f}%;background:{cor}"></span></div>'
                      f'<div class="atg-group-vehicle-value"><strong>{_moeda(veiculo.valor)}</strong> '
                      f'<span class="atg-group-vehicle-pct">{percentual}</span></div></div>')
    contexto = f'no ano de {modelo.ano}' if mes is None else f'no mês de {MESES[mes - 1]}/{modelo.ano}'
    vazio = '<p class="atg-group-copy">Sem registros de vendas no perímetro selecionado.</p>' if not veiculos else ''
    return (f'<div class="atg-group-copy">Participação no já vendido do grupo {contexto} · sem metas individuais</div>'
            f'<div class="atg-group-vehicles"><div class="atg-group-vehicle-stack" aria-hidden="true">{"".join(partes)}</div>'
            f'<div role="list" aria-label="Contribuição dos veículos">{"".join(linhas)}{vazio}</div>'
            f'<div class="atg-group-total"><span>Total do {"ano" if mes is None else "mês"} · grupo {escape(modelo.grupo)}</span>'
            f'<strong>{_moeda(total)}</strong></div></div>')


def _selecionar_mes(chave: str) -> None:
    """Lê somente o mês da seleção nativa, nunca valores financeiros do cliente."""
    selecao = st.session_state.get(chave, {}).get('selection', {})
    pontos = selecao.get('points', [])
    if not pontos:
        return
    custom = pontos[0].get('customdata', [])
    if not isinstance(custom, (list, tuple)) or not custom:
        return
    mes = custom[0]
    if isinstance(mes, bool) or not isinstance(mes, int) or not 1 <= mes <= 12:
        return
    st.session_state[_MES] = mes
    st.session_state[_PERIODO] = 'Mês'


def render(
    df: pd.DataFrame, metas: pd.DataFrame, ano: int, *,
    data_referencia: Referencia = None,
    atividade: Callable[[str], tuple[bool, str | None]],
) -> None:
    grupos = grupos_disponiveis(df, metas, ano, data_referencia=data_referencia)
    st.html(CSS)
    with st.container(key='design_group_monthly'):
        with st.container(key='group_monthly_header', horizontal=True):
            with st.container(key='group_monthly_heading'):
                st.markdown('<h2 class="atg-group-title" id="desempenho-mensal-por-grupo">Desempenho Mensal por Grupo</h2>'
                            '<p class="atg-group-copy">Realizado nos meses encerrados · Já vendido nos meses abertos · no perímetro de metas</p>',
                            unsafe_allow_html=True)
            if not grupos:
                st.info('Sem grupos com vendas ou metas para o ano selecionado.')
                return
            if st.session_state.get('_group_monthly_grupo') not in grupos:
                st.session_state['_group_monthly_grupo'] = 'DISNEY' if 'DISNEY' in grupos else grupos[0]
            with st.container(key='group_monthly_picker'):
                grupo = st.selectbox('Grupo', grupos, key='_group_monthly_grupo', persist_state='session')
        contexto = (ano, grupo)
        if st.session_state.get('_group_monthly_context') != contexto:
            st.session_state['_group_monthly_context'] = contexto
            st.session_state[_MES] = None
            st.session_state[_PERIODO] = 'Ano'
        modelo = preparar_grupo(df, metas, ano, grupo, data_referencia=data_referencia)
        ativo, operacao = atividade(grupo)
        st.markdown(_resumo(modelo, ativo, operacao), unsafe_allow_html=True)
        with st.container(key='group_monthly_body'):
            esquerda, direita = st.columns([2, 1], gap='large')
            with esquerda:
                with st.container(key='group_monthly_chart_controls', horizontal=True):
                    with st.container(key='group_monthly_plot_title'):
                        titulo = {'Vendas × Meta': 'Vendas versus meta mensal', 'Atingimento': 'Atingimento mensal',
                                  'Desvio': 'Desvio mensal em relação à meta'}[st.session_state.get('_group_monthly_perspectiva', 'Vendas × Meta')]
                        st.markdown(f'<h3 class="atg-group-title">{titulo}</h3>', unsafe_allow_html=True)
                    perspectiva = st.segmented_control('Perspectiva mensal', monthly_groups_charts.PERSPECTIVAS,
                        default='Vendas × Meta', required=True, key='_group_monthly_perspectiva',
                        label_visibility='collapsed', persist_state='session')
                mes = st.session_state.get(_MES) if st.session_state.get(_PERIODO) == 'Mês' else None
                identidade = sha256(f'{ano}:{grupo}'.encode()).hexdigest()[:12]
                comparacao_indisponivel = perspectiva != 'Vendas × Meta' and not modelo.tem_metas
                if comparacao_indisponivel:
                    st.info('Sem meta cadastrada para esta comparação. Consulte as vendas em Vendas × Meta.')
                for mobile, tamanho in (() if comparacao_indisponivel else ((False, 'desktop'), (True, 'mobile'))):
                    chave = f'group_monthly_plot_{identidade}_{tamanho}'
                    with st.container(key=f'group_monthly_chart_{tamanho}'):
                        figura = monthly_groups_charts.figura_mensal(modelo, perspectiva, mobile=mobile, mes_selecionado=mes)
                        st.plotly_chart(figura, width='stretch', theme=None, key=chave,
                            on_select=lambda key=chave: _selecionar_mes(key), selection_mode='points',
                            config={'displayModeBar': False, 'responsive': True, 'scrollZoom': False})
                instrucao = ('Use o controle Mês para detalhar.' if comparacao_indisponivel else
                             '* Em andamento · ° Futuro · Selecione um mês no gráfico para detalhar.')
                st.markdown(f'<p class="atg-group-footnote">{instrucao}</p>', unsafe_allow_html=True)
                if mes is not None and st.session_state.get(_PERIODO) == 'Mês':
                    st.markdown(_detalhe(modelo.meses[mes - 1], ano), unsafe_allow_html=True)
            with direita:
                with st.container(key='group_monthly_vehicle'):
                    st.markdown('<h3 class="atg-group-title">Contribuição dos veículos</h3>', unsafe_allow_html=True)
                    periodo = st.segmented_control('Período da contribuição', ('Ano', 'Mês'), required=True,
                        key=_PERIODO, label_visibility='collapsed', persist_state='session',
                        format_func=lambda p: f'Ano · {ano}' if p == 'Ano' else
                        f'Mês · {MESES[st.session_state[_MES] - 1]}/{ano}' if st.session_state.get(_MES) else 'Mês')
                    if periodo == 'Mês':
                        st.selectbox('Mês para detalhar', range(1, 13), index=None, placeholder='Selecione um mês',
                            format_func=lambda m: f'{MESES[m - 1]}/{ano}', key=_MES, persist_state='session',
                            help='Alternativa por teclado ou toque, inclusive para meses sem registros ou fora de vigência.')
                    mes_contribuicao = st.session_state.get(_MES) if periodo == 'Mês' else None
                    if periodo == 'Mês' and mes_contribuicao is None:
                        st.info('Selecione um mês no gráfico ou no campo acima.')
                    else:
                        st.markdown(_veiculos(modelo, mes_contribuicao), unsafe_allow_html=True)
                    if periodo == 'Ano':
                        orientacao = ('Use o controle Mês para ver a contribuição naquele mês.' if comparacao_indisponivel else
                                      'Selecione um mês no gráfico para ver a contribuição naquele mês.')
                        st.markdown(f'<p class="atg-group-copy">{orientacao}</p>', unsafe_allow_html=True)
        st.markdown('<p class="atg-group-footnote">Valor Líquido · Mês de Veiculação · Metas mensais vigentes. '
                    'Meses sem registros não comprovam ausência de vendas.</p>', unsafe_allow_html=True)
