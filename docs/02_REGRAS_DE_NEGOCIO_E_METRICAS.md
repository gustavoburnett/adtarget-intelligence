# 02. Regras de Negócio e Métricas — AdTarget Intelligence

## Classificação de Status (regra vigente — v0.3, 2026-07-09)

O campo STATUS é **obrigatório** na planilha de origem e possui **8 valores oficiais**. Todo PI é classificado com base no campo STATUS normalizado:

| Bucket | Status incluídos | Entra em soma de valor? |
|---|---|---|
| **Vendas** (indicador principal) | A VEICULAR, EM VEICULAÇÃO, CHECKING, AGUARD. DOC. VEÍCULO, FATURADO, DIRETO | Sim |
| **Faturado** (subconjunto de Vendas) | FATURADO, DIRETO | Sim |
| **Em Aberto** (subconjunto de Vendas) | A VEICULAR, EM VEICULAÇÃO, CHECKING, AGUARD. DOC. VEÍCULO | Sim |
| **Fora do cálculo** | CANCELADO, BONIFICADO | Não (apenas contagem, em bloco separado) |

Regras explícitas:

- **Vendas = soma de VALOR PI LIQUIDO** (ou VALOR PI BRUTO, via toggle) dos 6 status de venda.
- **Faturado = FATURADO + DIRETO.** Corresponde ao antigo "Faturamento Realizado" (nomenclatura usada até a v0.2) e continua sendo o indicador validado pelas magnitudes de referência do documento 01. Dentro dele, o valor de DIRETO tem natureza comercial diferente (sem comissão de agência).
- **Em Aberto = Vendas − Faturado** (identidade estrutural). Representa campanhas vendidas e ainda não faturadas.
- **CANCELADO e BONIFICADO ficam fora de todas as somas**, sem exceção.
- **Status vazio ou não reconhecido pelo vocabulário** gera alerta de qualidade e fica **fora de todos os indicadores** — nunca entra silenciosamente em nenhuma soma. Não existe categoria interna para status em branco (a antiga SEM_STATUS foi extinta na v0.3).

## Métrica de valor

- **Métrica principal: VALOR PI LIQUIDO.** Todo card, gráfico e tabela usa valor líquido por padrão.
- **Métrica alternável: VALOR PI BRUTO.** Disponível via botão/toggle em qualquer bloco que envolva valor monetário, para quem precisa ver o volume de negócio intermediado, não só a receita líquida da AdTarget.
- Comissão observada nos dados: aproximadamente 20% flat (líquido = bruto × 0,80) na maioria dos PIs. Em vendas DIRETO, a relação se aproxima de 1:1 (sem comissão).

## Mês de referência

- **Padrão: MÊS (GANHO).** Representa quando o negócio foi comercialmente fechado. É o critério padrão em todos os gráficos e KPIs de evolução temporal.
- **Alternável: MÊS (VEICULAÇÃO).** Representa quando o anúncio efetivamente rodou. Disponível via toggle, principalmente relevante para leitura de entrega/faturamento.
- Os dois critérios divergem em cerca de 38% das linhas. Por isso a escolha do critério muda o resultado do gráfico de evolução mensal, e ambos precisam estar disponíveis, nunca só um.

## Comparativos temporais (base Vendas)

| Comparativo | Onde aparece | Lógica de cálculo |
|---|---|---|
| **YTD (acumulado no ano)** | KPI principal da página Performance Comercial | Soma de Vendas de janeiro até o último mês com dado no ano selecionado, comparado ao mesmo intervalo (janeiro até o mês equivalente) do ano anterior. Nunca compara ano parcial atual com ano completo anterior. |
| **Mês a mês** | Gráfico de evolução mensal | Cada mês do ano selecionado comparado isoladamente ao mesmo mês do ano anterior (Jan vs Jan, Fev vs Fev...), sem acumular. |

## Comportamento dos filtros (regra transversal, válida nas 3 páginas)

- **Ano**: seleção única (um ano por vez, nunca múltiplos). Ao carregar qualquer página, vem selecionado por padrão o ano mais recente disponível na base. O "ano anterior", usado em todo comparativo, é sempre calculado automaticamente como (ano selecionado − 1), nunca é um filtro separado que o usuário escolhe.
- **Se não existir dado para o ano anterior ao selecionado** (ex: usuário seleciona o primeiro ano disponível na base), qualquer bloco de comparativo (YTD ou mês a mês) exibe "sem comparativo disponível" em vez de erro, percentual inválido, ou divisão por zero.
- **Grupo, Veículo, Agência, Cliente, Status, Executivo**: todos são filtros de seleção múltipla. Por padrão, ao carregar a página, vêm com **todos os valores marcados** (mostrando o universo completo do ano selecionado), nunca vazios.
- **Veículo**: sempre listado e exibido como o par "Grupo — Veículo" (nunca o nome do veículo isolado), pelo mesmo motivo do agrupamento descrito acima. Se nenhum Grupo estiver selecionado, o filtro de Veículo lista todos os pares Grupo—Veículo existentes no ano selecionado.
- **Recorte de filtro sem nenhuma linha resultante**: qualquer card mostra "R$ 0,00" ou "Sem dados no recorte selecionado", nunca erro ou tela em branco.
- **Meses futuros sem dado no gráfico de evolução mensal**: aparecem como lacuna (sem ponto/linha), nunca como valor zero. Isso evita que um mês futuro sem dado seja lido visualmente como uma queda de vendas.
- **YTD e comparativo mês a mês respeitam os toggles ativos no momento da visualização**: se o usuário estiver com Valor Bruto e MÊS (VEICULAÇÃO) selecionados, os comparativos são recalculados sobre essa base, não ficam fixos em Valor Líquido/MÊS (GANHO). O padrão inicial de todo carregamento é Valor Líquido + MÊS (GANHO), conforme definido acima.

## Ticket Médio

Ticket Médio = Vendas (no toggle de valor ativo) ÷ quantidade de PIs classificados na base Vendas, no recorte de filtros selecionado.

## Quantidade de Campanhas

Contada por **combinação distinta de Cliente + Campanha**, não pelo nome da campanha isoladamente. Motivo: existem nomes de campanha genéricos (ex: "ALWAYS ON", "CAMPANHA INSTITUCIONAL 2024") que se repetem em clientes diferentes; contar só pelo nome subestimaria a quantidade real de campanhas distintas.

**Recorte de status (v0.3)**: a contagem considera as linhas da base **Vendas** (os 6 status de venda), no mesmo recorte de filtros do card de Vendas ao lado do qual ela aparece. Campanhas canceladas ou bonificadas não entram. *(Até a v0.2, a contagem considerava apenas FATURADO + DIRETO; os números de referência da análise original — 240 campanhas em 2024, 257 em 2025 e 45 em 2026 parcial — foram calculados nessa base antiga e devem ser relidos após a primeira carga com a regra nova.)*

## Agrupamento de Veículo

Toda agregação por veículo (ranking, gráfico de vendas por veículo, tabela analítica) usa sempre a combinação **Grupo + Veículo**, nunca o nome do veículo isolado. Motivo: existem veículos com o mesmo nome comercial pertencentes a grupos diferentes (identificado na análise da base real), o que geraria mistura incorreta de entidades distintas se agregado só pelo nome do veículo.

## Métrica de Cancelado/Bonificado

Ao contrário do que uma primeira leitura sugeriria, **essa métrica não é calculada como soma monetária**. Na base real, 42 das 43 linhas CANCELADO e todas as 26 linhas BONIFICADO já vêm com VALOR PI BRUTO e VALOR PI LIQUIDO zerados na origem (é o comportamento esperado: negócio não faturado, sem valor a contabilizar). Somar valor monetário desses status resultaria, quase sempre, em um número próximo de zero, sem nenhum poder de leitura sobre o tamanho real da perda de carteira.

**Definição oficial**: o indicador de Cancelado/Bonificado é uma **contagem de PIs**, exibida como duas contagens separadas dentro do mesmo bloco ("X PIs Cancelados", "Y PIs Bonificados"), no recorte de filtros selecionado. Caso exista valor monetário diferente de zero nessas linhas (situação hoje excepcional, ver alerta de qualidade abaixo), esse valor aparece como informação secundária, nunca como o número principal do bloco.

## Totais e recomputação

Nenhum total, soma ou KPI é lido de célula pré-calculada da planilha de origem. Todo valor exibido no dashboard é recalculado a partir das linhas brutas, a cada carregamento de dado (respeitando o cache). Isso evita herdar inconsistências de fórmulas antigas ou desatualizadas que possam existir na planilha.

## Normalização de dados (regras genéricas, aplicadas a toda a base)

- Remoção de espaço em branco no início/fim de campos de texto (GRUPO, VEICULO, AGENCIA, CLIENTE, EXECUTIVO, STATUS, CAMPANHA)
- Padronização de maiúscula/minúscula para fins de agrupamento e comparação (mantendo formatação de exibição)
- Unificação de valores de STATUS equivalentes que hoje aparecem duplicados por diferença de formatação (ex: espaço extra)
- Conversão de campos de mês em texto ("JANEIRO/2024") para data real (primeiro dia do mês)
- Tratamento do campo PI sempre como texto, nunca como número ou data
- Tratamento do campo VENCIMENTO PI como dois campos derivados: data (quando existir) e flag de "contra apresentação" (quando o valor original for texto)

Importante: a normalização trata **apenas problemas genéricos de qualidade de dados**. Nenhuma correção específica de um cadastro individual (como os casos pontuais de veículo com grupo trocado, já corrigidos direto na planilha de origem) fica implementada como regra fixa no código.

## Alertas de qualidade (não corrigem, apenas avisam)

Exibidos num bloco próprio na página Analítico Comercial. A numeração original é preservada para rastreabilidade; o alerta 2 foi removido na v0.3:

1. **Linhas com status FATURADO sem Nota Fiscal preenchida.** Considera célula em branco e também o texto literal "SEM NF"/"SEM NOTA", quando presente nesse status.
2. *(removido na v0.3)* ~~Linhas sem STATUS preenchido.~~ O campo STATUS passou a ser obrigatório na planilha; um eventual branco que escape da regra de preenchimento é capturado pelo alerta 4, exibido como "(VAZIO)".
3. **Veículo associado a mais de um Grupo** na base carregada. Verificação genérica e permanente, criada depois de identificar esse tipo de inconsistência na análise inicial da planilha. Não corrige nada automaticamente, apenas sinaliza para correção manual na fonte.
4. **Status vazio ou não reconhecido pelo vocabulário controlado** (8 status oficiais). Linhas sinalizadas aqui ficam fora de todos os indicadores — nunca entram silenciosamente em nenhuma soma.
5. **PI com status CANCELADO ou BONIFICADO e valor (bruto ou líquido) diferente de zero.** Comportamento esperado é valor zerado nesses status; qualquer exceção é sinalizada individualmente para verificação manual.
