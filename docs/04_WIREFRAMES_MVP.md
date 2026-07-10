# 04. Wireframes do MVP — AdTarget Intelligence

Este documento descreve KPIs, gráficos, filtros, tabelas e lógica de cálculo das 3 páginas aprovadas para a Fase 1. As regras de cálculo detalhadas (definição de Vendas, Faturado, Em Aberto, métrica principal etc.) estão no documento 02, e são a base de todo cálculo descrito aqui. *(Nomenclatura atualizada na v0.3: "Faturamento" → "Vendas"; "Analítico Faturamento" → "Analítico Comercial"; "Pipeline em Aberto" → "Em Aberto". Layout e componentes inalterados.)*

## Página 1: Performance Comercial (visão executiva)

### Cards no topo

| Card | Cálculo | Decisão que ajuda a tomar |
|---|---|---|
| Vendas | Soma do valor líquido dos 6 status de venda, no recorte de filtros selecionado. Etiqueta secundária indicando quanto desse total já está Faturado | Quanto a AdTarget vendeu no período |
| YTD vs Ano Anterior (KPI principal) | Comparativo acumulado no ano (janeiro até o último mês com dado), contra o mesmo intervalo do ano anterior, em percentual, na base Vendas | Se o crescimento do ano é real e sustentado, não apenas um mês bom isolado |
| Ticket Médio | Vendas ÷ quantidade de PIs na base Vendas | Se os negócios fechados estão maiores ou mais pulverizados |
| Quantidade de Campanhas | Combinações distintas de Cliente + Campanha no recorte (base Vendas) | Volume operacional real do período |
| Em Aberto | Soma do valor líquido dos status A VEICULAR + EM VEICULAÇÃO + CHECKING + AGUARD. DOC. VEÍCULO | Quanto já foi vendido e ainda não faturou (Em Aberto = Vendas − Faturado) |

### Gráficos

- **Evolução das Vendas**: linha do ano selecionado, com linha pontilhada do ano anterior no mesmo mês (comparativo mês a mês). Toggle de critério de data: **MÊS (VEICULAÇÃO) como padrão (critério oficial, v0.4)**, MÊS (GANHO) como análise alternativa. Toggle de métrica: Valor Líquido como padrão, Valor Bruto como alternativa.
  Decisão: identificar sazonalidade e comparar o ritmo do ano com o anterior.
- **Evolução mensal do Ticket Médio**: mesmo critério de mês do gráfico anterior.
  Decisão: saber se o ticket está subindo, estável ou caindo mês a mês, independente do volume total.

### Blocos de ranking resumido

Top 5 Veículos (sempre Grupo + Veículo), Top 5 Agências, Top 5 Clientes, em barra horizontal (base Vendas).
Decisão: visão rápida de quem sustenta o negócio, para uso direto em reunião executiva, sem precisar abrir uma tabela.

### Filtros da página

Ano, Grupo. Filtros mais finos (Veículo, Agência, Cliente, Status, Executivo) ficam nas páginas analíticas; essa página é o resumo executivo.

### Tabela

Nenhuma. Esta página é composta apenas por cards e gráficos.

---

## Página 2: Analítico Comercial

### Cards no topo

| Card | Cálculo | Decisão que ajuda a tomar |
|---|---|---|
| Vendas | Mesmo cálculo da página 1, reagindo aos filtros desta página. Etiqueta secundária com o valor Faturado | Consistência com a visão executiva |
| Em Aberto | Mesmo cálculo da página 1 | Idem |
| Cancelado/Bonificado | Contagem de PIs com status CANCELADO e contagem de PIs com status BONIFICADO, exibidas separadamente (não é soma monetária — ver documento 02 para o motivo) | Quantos negócios foram perdidos ou dados como cortesia; taxa de perda da carteira em volume de negócio, não em valor, já que o valor normalmente já vem zerado |
| Alertas de Qualidade | Contagem de linhas FATURADO sem Nota Fiscal, veículos associados a mais de um grupo, status vazio/não reconhecido, e PIs cancelados/bonificados com valor diferente de zero | Quantas linhas precisam de correção manual na fonte antes de fechar o mês |

### Gráfico

Funil ou barra por status (A VEICULAR, EM VEICULAÇÃO, CHECKING, AGUARD. DOC. VEÍCULO, FATURADO, DIRETO, CANCELADO, BONIFICADO), mostrando valor e contagem de cada categoria, na ordem do ciclo de vida comercial.
Decisão: visão completa da saúde da carteira, não apenas o que já é receita fechada.

### Tabela principal

Uma linha por PI, com colunas: Grupo, Veículo, PI, Agência, Cliente, Campanha, Mês (Ganho), Mês (Veiculação), Início, Fim, Valor Bruto, Valor Líquido, Vencimento PI, Status, Nota Fiscal, Executivo. Pesquisável, ordenável, exportável em CSV.
Decisão: auditoria linha a linha; resposta pronta para qualquer questionamento interno sobre um PI específico.

### Filtros da página

Ano, Grupo, Veículo (em cascata dentro do grupo selecionado), Agência, Cliente, Status (múltipla escolha), Executivo. Todos os filtros finos do MVP ficam concentrados aqui.

---

## Página 3: Analítico Veículos

### Cards no topo

| Card | Cálculo | Decisão que ajuda a tomar |
|---|---|---|
| Vendas do recorte | Mesmo cálculo padrão | Consistência entre páginas |
| Ticket Médio por Veículo | Vendas ÷ quantidade de PIs, calculado por Grupo+Veículo (card exibe o ticket do recorte; detalhe por veículo na tabela) | Quais veículos vendem pacotes grandes versus pulverizados |
| Veículos Ativos no Período | Contagem de combinações Grupo+Veículo com pelo menos 1 PI na base Vendas | Quantos veículos do portfólio de fato geram negócio, não apenas os cadastrados |

### Gráficos

- **Vendas por Grupo**: barra horizontal, ordenada do maior para o menor.
  Decisão: onde as vendas se concentram; base para negociação de condições com os grupos maiores.
- **Drill-down: Vendas por Veículo dentro do Grupo**: ao selecionar um grupo (ex: Sistema Verdes Mares), abre o detalhe de vendas por veículo dentro dele.
  Decisão: dentro de um grupo com múltiplos veículos, identificar qual veículo específico realmente performa.
- **Ranking completo de Veículos, Agências e Clientes** (não limitado a Top 5, com paginação).
  Decisão: ranking de uso operacional/comercial, fora do contexto de reunião executiva resumida.

### Tabela

Agregada por Grupo + Veículo, com colunas: Vendas (Bruto), Vendas (Líquido), Ticket Médio, Quantidade de PIs, % do total.
Decisão: visão consolidada por veículo, pronta para uma reunião com o grupo de mídia representado.

### Filtros da página

Ano, Grupo, Agência, Cliente.

---

## Regras transversais a todas as 3 páginas

- Toda agregação por veículo usa sempre Grupo + Veículo, nunca veículo isolado. O filtro de Veículo sempre exibe o rótulo como "Grupo — Veículo".
- Métrica de valor padrão é sempre Valor Líquido, com opção de alternar para Valor Bruto em qualquer bloco monetário.
- Critério de data padrão é sempre **MÊS (VEICULAÇÃO)** (critério oficial do KPI de Vendas — v0.4), com opção de alternar para MÊS (GANHO) em análises específicas. Regra única em todas as páginas. YTD e comparativo mês a mês recalculam sobre o toggle ativo.
- Nenhum total é lido de célula pré-calculada da planilha; tudo é recalculado a partir das linhas brutas tratadas.
- Filtro Ano é de seleção única, com o ano mais recente disponível marcado por padrão; ano anterior é sempre calculado automaticamente (ano selecionado − 1). Demais filtros (Grupo, Veículo, Agência, Cliente, Status, Executivo) são de seleção múltipla, com todos os valores marcados por padrão.
- Recorte de filtro sem nenhuma linha resultante exibe "R$ 0,00" ou "Sem dados no recorte selecionado", nunca erro.
- No gráfico de evolução mensal, meses futuros sem dado aparecem como lacuna (sem linha), nunca como valor zero.
- Comportamento completo de filtros, comparativos e alertas está detalhado no documento 02 (Regras de Negócio e Métricas), que é a referência oficial em caso de dúvida de implementação.
