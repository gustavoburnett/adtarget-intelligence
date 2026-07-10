# 00. Memória Oficial do Projeto — AdTarget Intelligence

## Sobre a AdTarget

A AdTarget é uma empresa de representação comercial de veículos de mídia. Representa grupos de mídia perante agências de publicidade e anunciantes, com forte presença em contas do governo federal (SECOM e ministérios) e clientes privados.

O negócio da AdTarget gira em torno de:

- Veículos
- Grupos (um veículo pode pertencer a um grupo com múltiplos veículos, ou ser um grupo de veículo único)
- Agências
- Clientes
- Campanhas
- Executivos Comerciais
- Faturamento
- Comissões
- Metas

## Situação atual

A operação comercial é acompanhada hoje por um dashboard em Power BI, alimentado por uma planilha Google Sheets. Esse dashboard será substituído por uma aplicação própria.

## Objetivo do projeto AdTarget Intelligence

Substituir o dashboard Power BI por uma aplicação própria, sem reinventar o produto na primeira fase. A prioridade da Fase 1 é reproduzir as funcionalidades essenciais do dashboard atual com simplicidade, estabilidade e baixa manutenção.

## Papel do Claude no projeto

Atuando como CTO, Arquiteto de Software, Product Owner e Desenvolvedor Principal. Responsável por entender o negócio, mapear os dados reais, propor arquitetura de informação, validar decisões com o responsável do projeto (Gustavo Burnett) antes de qualquer linha de código, e depois implementar.

## Fonte de dados

Uma única planilha Google Sheets, intitulada "Planilha de Vendas AdTarget", com uma aba por ano (2024, 2025, 2026). Não há banco de dados na Fase 1. A aplicação lê a planilha diretamente, trata os dados em memória e monta o dashboard.

## Escopo da Fase 1 (MVP)

**Dentro do escopo:**
- Página Performance Comercial
- Página Analítico Comercial (até a versão 0.2, denominada Analítico Faturamento)
- Página Analítico Veículos
- Leitura via Google Sheets API com Service Account
- Autenticação por senha única (sem perfil de usuário)
- Cache de dados, sem atualização em tempo real
- Hospedagem em Streamlit Community Cloud

**Fora do escopo (Fase 1.2):**
- Página Campanhas
- Página Metas
- Página Executivos
- Login por perfil de usuário
- Qualquer indicador exclusivo das páginas acima
- Segmentação Governo x Privado (ideia registrada, não aprovada para o MVP)
- Exportação em PDF/Excel (só entra se confirmado como necessidade real)

## Linha de decisões já validadas

1. Fonte de dados é a planilha Google Sheets real, sem banco de dados na Fase 1.
2. Painel único para uso interno da diretoria, sem login por perfil.
3. Acesso prioritariamente via desktop/notebook.
4. Atualização periódica (cache), não em tempo real.
5. Tecnologia: Python + Streamlit.
6. Planilha real foi lida e analisada diretamente (via integração de Google Drive), não apenas por prints do Power BI.
7. Estrutura real identificada: uma tabela transacional por ano, sem tabelas normalizadas separadas de Grupo/Veículo/Agência/Cliente.
8. *(histórico — superada pela decisão 28)* Faturamento Realizado definido como soma de status FATURADO + DIRETO.
9. *(histórico — superada pela decisão 28)* Pipeline em Aberto definido como soma de status CHECKING + AGUARD. DOC. VEÍCULO, exibido separado do faturamento.
10. *(histórico — parcialmente superada pelas decisões 28 e 30)* CANCELADO e BONIFICADO não entram em nenhum cálculo de receita, aparecem apenas como status de controle/qualidade. *(A exclusão de CANCELADO/BONIFICADO permanece válida; a categoria SEM_STATUS deixou de existir.)*
11. Valor Líquido é a métrica principal de valor; Valor Bruto fica disponível como alternativa.
12. *(histórico — superada pela decisão 33)* MÊS (GANHO) é o critério padrão de data; MÊS (VEICULAÇÃO) fica disponível como alternativa.
13. Comparativo com ano anterior: mês a mês no gráfico da evolução mensal, e YTD (acumulado no ano) como KPI principal da página executiva.
14. Quantidade de Campanhas contada por combinação distinta de Cliente + Campanha.
15. Agrupamento de veículo sempre pela dupla Grupo + Veículo, nunca veículo isolado.
16. Totais pré-calculados que já existem na planilha são ignorados; todo cálculo é refeito a partir das linhas brutas.
17. Normalização automática cobre apenas problemas genéricos de qualidade (espaço, maiúscula/minúscula, status duplicado por formatação). Nenhuma correção específica de cadastro fica hardcoded no código.
18. Um caso real de inconsistência de cadastro (veículo "93 FM" e veículo "IG" aparecendo sob grupo errado em 1 linha cada) foi identificado na análise e corrigido manualmente direto na planilha de origem pelo responsável do projeto. A aplicação passa a ter um alerta genérico de qualidade que detecta esse tipo de inconsistência (veículo mapeado para mais de um grupo), sem corrigir automaticamente.
19. Wireframe das 3 páginas do MVP aprovado, com KPIs, gráficos, filtros, tabelas e lógica de cálculo detalhados por página.
20. Plano técnico de implementação aprovado, cobrindo estrutura de pastas, bibliotecas, leitura de dados, autenticação, cache e deploy.
21. Revisão cruzada de toda a documentação oficial realizada antes do início da implementação, comparando Dicionário de Dados, Regras de Negócio, Wireframes, Arquitetura e Plano de Implementação entre si e contra a base real.
22. Métrica de Cancelado/Bonificado redefinida de soma monetária para contagem de PIs, porque a base real mostra que praticamente todo negócio cancelado ou bonificado já vem com valor zerado na origem.
23. *(histórico — superada pela decisão 30)* Alerta de qualidade "linhas sem status" passa a exibir também o valor financeiro somado (bruto e líquido), não apenas a contagem, porque o valor identificado é material.
24. Novo alerta de qualidade permanente: PI com status CANCELADO ou BONIFICADO e valor diferente de zero (situação hoje excepcional, 1 caso identificado).
25. Comportamento padrão de filtros formalizado: Ano em seleção única com o ano mais recente marcado por padrão e ano anterior sempre calculado automaticamente; demais filtros em seleção múltipla com tudo marcado por padrão; ausência de dado no recorte exibe zero/mensagem, nunca erro; meses futuros aparecem como lacuna no gráfico mensal, nunca como zero.
26. Confirmado que os comparativos YTD e mês a mês recalculam sobre os toggles de métrica (líquido/bruto) e critério de mês (ganho/veiculação) ativos no momento, não ficam fixos numa combinação só.
27. *(histórico — base de cálculo alterada pela decisão 32)* Escopo da contagem de "Quantidade de Campanhas" fechado: considera apenas linhas de Faturamento Realizado (FATURADO + DIRETO), não Pipeline.
28. **(v0.3, 2026-07-09)** Regra comercial de indicadores redefinida, supersedendo as decisões 8 e 9: **Vendas** = soma de VALOR PI LIQUIDO dos status A VEICULAR + EM VEICULAÇÃO + CHECKING + AGUARD. DOC. VEÍCULO + FATURADO + DIRETO; **Faturado** = FATURADO + DIRETO (corresponde ao antigo Faturamento Realizado); **Em Aberto** = A VEICULAR + EM VEICULAÇÃO + CHECKING + AGUARD. DOC. VEÍCULO. Identidade estrutural: **Em Aberto = Vendas − Faturado**. CANCELADO e BONIFICADO ficam fora de todas as somas.
29. **(v0.3)** Vocabulário do campo STATUS fechado em **8 valores oficiais** (entram A VEICULAR e EM VEICULAÇÃO). O campo passou a ser obrigatório na planilha de origem, padronizada pela equipe.
30. **(v0.3)** Categoria SEM_STATUS extinta e alerta de "linhas sem status" removido. Status vazio ou não reconhecido pelo vocabulário gera o alerta de qualidade de status não reconhecido e fica fora de todos os indicadores — nunca entra silenciosamente em nenhuma soma.
31. **(v0.3)** Nomenclatura comercial corrigida nas telas: "Faturamento" substituído por "Vendas"; página "Analítico Faturamento" renomeada para "Analítico Comercial"; títulos de gráficos atualizados. Sem mudança de layout, identidade visual, filtros ou navegação.
32. **(v0.3)** Métricas derivadas (YTD, comparativo mês a mês, Ticket Médio, Quantidade de Campanhas, rankings, Veículos Ativos e agregações) calculadas sobre a base **Vendas**, coerentes com o indicador principal.
33. **(v0.4, 2026-07-10)** Regra oficial de critério temporal, supersedendo a decisão 12, validada pela auditoria de dados e confirmada pela área de negócio: o KPI oficial de Vendas da AdTarget usa **MÊS (VEICULAÇÃO)** como critério temporal padrão, em **todas as páginas do produto** (regra única, sem variação entre telas). MÊS (GANHO) permanece disponível apenas como análise alternativa, via toggle. A definição é centralizada numa única constante de negócio (`CRITERIO_MES_OFICIAL` em `src/data/metrics.py`) — fonte única de verdade: funções de métrica e toggle da interface derivam dela.

## Status atual

Documentação oficial consolidada na versão 0.3 (ver 06_CHANGELOG.md). MVP implementado: camada de dados (loader, cleaning, quality_checks, metrics) e interface (gate de senha, componentes e as 3 páginas), com 99 testes automatizados passando e smoke test de ponta a ponta. Próximos passos: validação dos números com a planilha real (critério de aceite: indicador Faturado contra as magnitudes de referência do documento 01) e deploy no Streamlit Community Cloud.
