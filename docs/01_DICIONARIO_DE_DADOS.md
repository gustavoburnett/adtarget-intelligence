# 01. Dicionário de Dados — AdTarget Intelligence

## Fonte

Google Sheets, título "Planilha de Vendas AdTarget". Uma aba por ano: **2024**, **2025**, **2026**. Mesma estrutura de colunas em todas as abas, com uma diferença: a aba **2026** tem 2 colunas adicionais (ver seção de colunas).

Não existem tabelas separadas de cadastro (Grupo, Veículo, Agência, Cliente). Toda a informação está numa única tabela transacional por aba: **uma linha = um PI (Pedido de Inserção)**.

## Volume de dados (no momento da análise)

| Aba | Linhas de dados (excluindo cabeçalho) |
|---|---|
| 2024 | 654 |
| 2025 | 647 |
| 2026 | 156 (parcial, ano em andamento) |

Volume cresce ano a ano. Faturamento bruto total (soma de todas as linhas, todos os status, apenas para dimensionar o tamanho da base — não confundir com os indicadores oficiais, definidos no documento 02): 2024 ≈ R$ 20,4 milhões, 2025 ≈ R$ 25,2 milhões, 2026 (parcial) ≈ R$ 16,6 milhões.

### Magnitudes de referência (indicador **Faturado**, valor líquido)

Estes são os números que a aplicação deve reproduzir no indicador **Faturado** (FATURADO + DIRETO; até a v0.2 denominado "Faturamento Realizado"), servindo de critério de aceite:

| Ano | Faturado (líquido) | Faturado (bruto) |
|---|---|---|
| 2024 | R$ 16.498.970 | R$ 20.340.880 |
| 2025 | R$ 19.996.930 | R$ 24.919.240 |
| 2026 (parcial) | R$ 4.714.419 | R$ 5.893.024 |
| **Total 3 anos** | **R$ 41.210.319** | **R$ 51.153.146** |

Na época da análise, a soma de CHECKING + AGUARD. DOC. VEÍCULO (então denominada "Pipeline em Aberto"; a partir da v0.3, parte do indicador **Em Aberto**, que também inclui A VEICULAR e EM VEICULAÇÃO) totalizava R$ 9.972.236 bruto / R$ 7.977.788 líquido em todos os anos. O indicador **Vendas** (v0.3) será sempre ≥ Faturado, pois inclui os status em aberto.

*(Nota histórica — situação resolvida na v0.3: na análise original existiam 7 linhas sem STATUS somando R$ 1.101.270 bruto / R$ 881.016 líquido. A equipe padronizou a planilha, o campo STATUS passou a ser obrigatório e essas linhas foram classificadas. Não existe mais valor fora dos indicadores por ausência de status.)*

## Colunas identificadas

| Coluna | Tipo esperado | Descrição | Observação de qualidade |
|---|---|---|---|
| PRAÇA | Texto | Cidade/praça da operação | Hoje só existe o valor "BRASÍLIA" (1 linha nula). Dimensão sem variação, não vale como filtro no MVP. |
| EXECUTIVO | Texto | Nome do executivo comercial responsável pelo PI | 9 executivos distintos. Concentração alta: o executivo com maior volume responde por aproximadamente 34% do Faturado (líquido) do período analisado. |
| GRUPO | Texto | Grupo de mídia | 21 grupos distintos. 14 são "grupo = veículo único", 7 têm múltiplos veículos reais (ex: Sistema Verdes Mares, Disney, Canal Rural). |
| VEICULO | Texto | Veículo de mídia dentro do grupo | 54 veículos distintos. **Sempre usar em conjunto com GRUPO ao agrupar/agregar**, nunca isolado, por risco de ambiguidade (ver seção de qualidade). |
| PI | Numérico (na maioria) | Número do Pedido de Inserção | Tipo de dado misto: a maioria é numérica, mas existem valores em texto (ex: "01/2024") e alguns que o próprio Google Sheets converteu para data por engano. Tratar sempre como texto na aplicação, nunca como identificador único garantido. |
| AGENCIA | Texto | Agência de publicidade intermediária | 39 agências distintas. Valor "DIRETO" indica venda sem agência intermediária. |
| CLIENTE | Texto | Anunciante final | 90 clientes distintos. Mistura de órgãos públicos (SECOM, ministérios, municípios) e empresas privadas. |
| CAMPANHA | Texto livre | Nome da campanha publicitária | 537 valores distintos de texto puro; alguns nomes se repetem entre clientes diferentes (ex: "ALWAYS ON"), por isso contagem de campanha é feita por Cliente+Campanha, não só pelo nome. |
| MÊS (GANHO) | Texto ("MÊS/ANO") | Mês em que o negócio foi fechado/vendido | Converter para data (primeiro dia do mês) na limpeza. |
| MÊS (VEICULAÇÃO) | Texto ("MÊS/ANO") | Mês em que o anúncio efetivamente rodou | Difere de MÊS (GANHO) em ~38% das linhas. Isso é normal do negócio (venda fechada num mês, anúncio rodando no mês seguinte), não é erro. |
| INÍCIO | Data | Data de início da veiculação | — |
| FIM | Data | Data de fim da veiculação | Alguns intervalos aparentam inconsistência (fim muito distante do início); não tratado automaticamente no MVP, aparece só se algum indicador futuro precisar. |
| VALOR PI BRUTO | Numérico (moeda) | Valor bruto negociado | Ler com `UNFORMATTED_VALUE` na API para evitar receber string formatada em R$. |
| VALOR PI LIQUIDO | Numérico (moeda) | Valor líquido após comissão | Métrica principal do projeto. Na maioria dos casos, líquido = bruto × 0,80 (comissão de 20%). Em vendas com status DIRETO, a relação se aproxima de 1:1 (sem comissão), com pequenas variações. |
| VENCIMENTO PI | Data ou texto | Data de vencimento do pagamento | Campo misto: em ~55% das linhas o valor é o texto "CONTRA APRESENT." (sem data fixa, pagamento contra apresentação da nota fiscal), no restante é uma data real. Tratar como dois campos derivados: data (quando existir) + flag booleana de "contra apresentação". |
| STATUS | Texto (categórico, **obrigatório**) | Situação do PI | **Vocabulário oficial (v0.3), 8 valores**: A VEICULAR, EM VEICULAÇÃO, CHECKING, AGUARD. DOC. VEÍCULO, FATURADO, DIRETO, CANCELADO, BONIFICADO. Ver regras de negócio no documento 02. Duplicidades por espaço em branco no fim do texto (ex: "FATURADO" e "FATURADO ") são tratadas na normalização. Valor vazio ou fora do vocabulário gera alerta de qualidade e fica fora de todos os indicadores. |
| NOTA FISCAL | Texto/Numérico | Número da nota fiscal emitida | Ausência de NF ocorre de duas formas: célula em branco, ou o texto literal "SEM NF"/"SEM NOTA" preenchido no campo. A verificação de qualidade considera as duas formas como "NF ausente". Todas as vendas com status DIRETO (56 de 56) não possuem NF registrada nesta planilha por desenho (faturamento direto emitido fora deste controle), isso não é uma inconsistência. O alerta de qualidade do documento 02 é focado especificamente em linhas **FATURADO** sem NF, que são as que de fato precisam de correção. |
| DATA DE CRIAÇÃO | Data | Data de criação do registro na planilha | — |
| OBSERVAÇÃO | Texto livre | Anotações diversas | Preenchido em menos de 20% das linhas. Sem estrutura, não entra em nenhum cálculo. |
| DATA FATURAMENTO | Data | Data em que o faturamento efetivamente ocorreu | **Existe apenas na aba 2026.** Sinal de que a operação começou a rastrear prazo de faturamento este ano. Não há dado retroativo para 2024/2025. |
| DIAS EM ABERTO | Numérico | Quantidade de dias que o PI ficou aberto até faturar (ou até hoje, se ainda aberto) | **Existe apenas na aba 2026.** Base para uma futura métrica de prazo médio de faturamento (não faz parte do MVP atual, fica registrado para Fase 1.2). |

## Dimensões e escala

| Dimensão | Quantidade de valores distintos |
|---|---|
| Grupos | 21 |
| Veículos | 54 |
| Agências | 39 |
| Clientes | 90 |
| Executivos | 9 |

## Hierarquia real Grupo → Veículo

14 dos 21 grupos são "grupo = veículo único" (estrutura simples, uma entidade só). 7 grupos têm hierarquia real de múltiplos veículos:

| Grupo | Quantidade de veículos | Exemplos |
|---|---|---|
| Sistema Verdes Mares | 10 | Diário do Nordeste, Verdinha, Recife FM, TV Diário, 93 FM |
| Disney | 11 | ESPN 1/2/3/4, ESPN Digital, Star Channel, FX, Disney+ |
| Carrega+ | 6 | Variações regionais (SP, GO, RJ, DF/RJ, MG) |
| Liga OOH | 4 | Variações regionais (PE, SE, RN, PB) |
| Canal Rural | 3 | Canal Rural, Canal do Criador, Portal Canal Rural |
| Webedia | 3 | Adoro Cinema, Minha Vida, Webedia |
| Melodia | 2 | 93 FM, Melodia |

## Qualidade de dados conhecida

- **Duplicidade de categoria por espaço em branco no fim do texto**: ocorre em STATUS (ex: "FATURADO"/"FATURADO "), em VEICULO (3 casos, ex: "93 FM"/"93 FM "), em AGENCIA (1 caso) e em CLIENTE (5 casos, ex: "SEBRAE"/"SEBRAE "). Resolvido por normalização automática genérica (trim + padronização de caixa).
- **Campo PI com tipo de dado misto**: número, texto e datas geradas por engano pelo Google Sheets. Tratado sempre como texto na aplicação.
- **Campo VENCIMENTO PI misto**: data real ou texto "CONTRA APRESENT.". Tratamento descrito na tabela de colunas.
- **Totais pré-calculados na própria planilha não são confiáveis**: identificado durante a análise que o critério de soma variava entre abas (uma aba somava só o faturado, outra somava tudo, inclusive pipeline) e que um dos totais estava desatualizado. Por isso, a aplicação nunca lê célula de total pré-calculada, sempre recalcula a partir das linhas brutas.
- **Cabeçalho pode não estar na primeira linha da aba**: identificado na conexão com a planilha real que a primeira linha pode estar vazia, com o cabeçalho verdadeiro na linha seguinte. O loader detecta automaticamente a primeira linha que contém todas as colunas obrigatórias.
- **Inconsistência de cadastro Grupo x Veículo**: identificado durante a análise que 1 linha de "93 FM" estava sob o grupo errado (Melodia em vez de Sistema Verdes Mares) e 1 linha de "IG" estava sob o grupo errado (ESPN em vez de IG). **Ambos os casos já foram corrigidos manualmente na planilha de origem.** A aplicação mantém um alerta genérico e permanente que detecta automaticamente se algum veículo passar a ter mais de um grupo associado, sem corrigir nada por conta própria.
- **Notas fiscais ausentes em linhas marcadas como FATURADO**: aproximadamente 69 linhas no total. Fica registrado como alerta de qualidade, não como erro bloqueante.
- **Linhas sem STATUS preenchido** *(histórico — resolvido na v0.3)*: existiam 7 linhas no período analisado. A planilha foi padronizada pela equipe, o campo STATUS passou a ser obrigatório e a categoria interna SEM_STATUS foi extinta. Um eventual branco que escape da regra de preenchimento é capturado pelo alerta de status não reconhecido, fora de todos os indicadores.
- **PIs cancelados ou bonificados normalmente vêm com valor zerado na origem**: 42 das 43 linhas CANCELADO e as 26 linhas BONIFICADO têm VALOR PI BRUTO e VALOR PI LIQUIDO iguais a zero, o que é o comportamento esperado (negócio não faturado, sem valor a contabilizar). Existe **1 exceção identificada**: uma linha CANCELADO em 2024 com valor de R$ 17.172,00 bruto que não foi zerado na planilha. Essa exceção é a razão pela qual a métrica de "Cancelado/Bonificado" no dashboard usa contagem de PIs como indicador principal, não soma monetária (ver documento 02). A aplicação mantém um alerta permanente para qualquer PI cancelado ou bonificado com valor diferente de zero, para sinalizar novos casos como esse.
