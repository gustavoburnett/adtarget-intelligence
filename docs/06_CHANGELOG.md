# 06. Changelog — AdTarget Intelligence

## Versão 0.1

- Criação do projeto AdTarget Intelligence
- Definição do escopo do MVP
- Análise completa da base de dados
- Definição das regras de negócio
- Definição das métricas
- Definição da arquitetura técnica
- Aprovação dos wireframes
- Aprovação do plano de implementação

## Versão 0.2

Revisão cruzada completa da documentação oficial, feita comparando Dicionário de Dados, Regras de Negócio e Métricas, Wireframes, Arquitetura Técnica e Plano de Implementação entre si e contra a base de dados real, antes do início da implementação.

- Corrigida a figura de concentração de faturamento por executivo no Dicionário de Dados (de ~42% para ~34%), recalculada com base correta em Faturamento Realizado líquido, e não na soma de todos os status.
- Adicionadas magnitudes de referência precisas por ano (Faturamento Realizado líquido/bruto, Pipeline em Aberto, valor em linhas sem status), para servirem de critério de aceite objetivo na implementação.
- Redefinida a métrica de Cancelado/Bonificado: de soma monetária para contagem de PIs, porque a base real mostra que praticamente todo negócio cancelado ou bonificado já vem com valor zerado na origem (42 de 43 linhas CANCELADO e as 26 linhas BONIFICADO).
- Criado novo alerta de qualidade permanente para PIs cancelados ou bonificados com valor diferente de zero, cobrindo a única exceção identificada na base atual.
- Ampliado o alerta de "linhas sem status" para exibir também o valor financeiro somado envolvido, não apenas a contagem de linhas, porque o valor identificado (R$ 881 mil líquidos) é material e não deveria ficar escondido atrás de um número de contagem pequeno.
- Esclarecido no Dicionário de Dados que a ausência de Nota Fiscal pode aparecer como célula em branco ou como texto literal "SEM NF"/"SEM NOTA", e documentado que vendas DIRETO nunca têm Nota Fiscal por desenho, não por inconsistência.
- Formalizado, no documento de Regras de Negócio e Métricas, o comportamento padrão de todos os filtros das 3 páginas (seleção única para Ano com ano mais recente marcado por padrão, seleção múltipla com tudo marcado por padrão para as demais dimensões, comportamento em caso de recorte sem dado, e ano anterior sempre calculado automaticamente).
- Formalizado que os comparativos YTD e mês a mês recalculam sobre os toggles de métrica (líquido/bruto) e critério de mês (ganho/veiculação) ativos no momento, em vez de ficarem fixos numa única combinação.
- Fechado o escopo de status considerado na contagem de "Quantidade de Campanhas" (apenas Faturamento Realizado, não Pipeline), com os números de referência por ano.
- Adicionada regra explícita de que meses futuros sem dado aparecem como lacuna no gráfico de evolução mensal, nunca como valor zero, evitando leitura equivocada de queda de faturamento.
- Adicionado risco técnico de secrets ausentes ou malformados no ambiente de deploy, com a mitigação esperada (mensagem de erro amigável, não stack trace).
- Atualizados os critérios de aceite do Plano de Implementação com valores numéricos precisos por ano, substituindo a faixa aproximada usada na versão 0.1.
- Nenhuma informação previamente aprovada foi removida. Todas as numerações de decisões e de documentos existentes na versão 0.1 foram preservadas; os ajustes desta versão foram adicionados como itens novos.

## Versão 0.3 (2026-07-09)

Redefinição da regra comercial de indicadores e alinhamento de nomenclatura, decidida pelo responsável do projeto (Gustavo Burnett) após a padronização da planilha de origem pela equipe. Supersede as decisões 8, 9 e 10 da versão 0.1/0.2 no que conflitarem.

- **Novo indicador principal: Vendas** = soma de VALOR PI LIQUIDO dos status A VEICULAR, EM VEICULAÇÃO, CHECKING, AGUARD. DOC. VEÍCULO, FATURADO e DIRETO (toggle para VALOR PI BRUTO disponível, como em todo bloco monetário).
- **Faturado** = soma apenas de FATURADO + DIRETO. Corresponde ao antigo "Faturamento Realizado" e continua sendo o indicador validado pelas magnitudes de referência do Dicionário de Dados.
- **Em Aberto** = soma apenas de A VEICULAR + EM VEICULAÇÃO + CHECKING + AGUARD. DOC. VEÍCULO (campanhas vendidas e ainda não faturadas). Identidade estrutural: **Em Aberto = Vendas − Faturado**.
- **CANCELADO e BONIFICADO ficam fora de todas as somas.** Permanecem apenas como contagem de PIs (bloco Cancelado/Bonificado) e no alerta de valor diferente de zero.
- **O campo STATUS passou a ser obrigatório na planilha** e o vocabulário controlado foi fechado em **8 valores oficiais**: A VEICULAR, EM VEICULAÇÃO, CHECKING, AGUARD. DOC. VEÍCULO, FATURADO, DIRETO, CANCELADO, BONIFICADO.
- **Extinta a categoria SEM_STATUS** e removido o alerta de qualidade nº 2 ("linhas sem status"). Status vazio ou não reconhecido pelo vocabulário gera o alerta de qualidade de status não reconhecido (nº 4) e fica fora de todos os indicadores — nunca entra silenciosamente em nenhuma soma. Os códigos dos demais alertas (1, 3, 4, 5) foram preservados para rastreabilidade.
- **Métricas derivadas passam à base Vendas**: YTD, comparativo mês a mês, Ticket Médio, Quantidade de Campanhas, rankings (Top 5 e completos), Veículos Ativos e agregações por Grupo+Veículo e por dimensão.
- **Nomenclatura comercial corrigida nas telas**: "Faturamento" substituído por "Vendas" nas páginas comerciais; página "Analítico Faturamento" renomeada para **"Analítico Comercial"**; títulos de gráficos atualizados (Evolução das Vendas; Vendas por Grupo; Vendas por Veículo; Vendas por Agência; Vendas por Cliente). Sem alteração de layout, identidade visual, filtros ou navegação.
- Convenção da versão 0.2 mantida: nenhuma informação previamente aprovada foi removida dos documentos; regras superadas foram marcadas como históricas, com referência a esta versão.

## Versão 0.4 (2026-07-10)

Definição do critério temporal oficial do KPI de Vendas, estabelecida após a auditoria de dados, a validação da base e a confirmação da área de negócio. Supersede a decisão 12 (v0.1).

- **REGRA OFICIAL: o indicador de Vendas utiliza MÊS (VEICULAÇÃO) como critério temporal.** Sempre que alguém perguntar "quanto vendemos em <ano>", a resposta oficial usa Veiculação. **Este é o KPI oficial da AdTarget.**
- **MÊS (GANHO) permanece disponível apenas para análises alternativas**, através do toggle existente — a funcionalidade não foi removida.
- **Regra única em todo o produto**: o padrão vale para todas as páginas (Performance Comercial, Analítico Comercial, Analítico Veículos e qualquer outra que exiba o indicador oficial), sem variação de comportamento entre telas.
- **Fonte única de verdade**: a definição está centralizada na constante de negócio `CRITERIO_MES_OFICIAL` (`src/data/metrics.py`). Todas as funções de métrica usam essa constante como padrão e o toggle da interface inicializa a partir dela; a ferramenta temporária de auditoria segue o mesmo critério. Nenhum valor fixo espalhado pelo código.
- Todos os indicadores que dependem do critério temporal (Vendas, Evolução das Vendas, YTD, Ticket Médio e sua evolução, Quantidade de Campanhas, Faturado, Em Aberto, rankings) permanecem calculados pelo mesmo pipeline e matematicamente consistentes entre si, verificado por testes automatizados e smoke test.
- **Refinamento do YTD (mesma data)**: no ano corrente, o acumulado vai de janeiro até o MÊS ATUAL, comparado ao mesmo intervalo do ano anterior (meses futuros — ex: veiculações agendadas — ficam fora); em anos encerrados, a comparação é ano completo contra ano completo. O texto auxiliar do card passa a exibir o período comparado (ex: "Jan–Jul/2026 vs Jan–Jul/2025"). Até então, o limite era o último mês com dado, o que, no critério Veiculação, podia puxar meses futuros para dentro do acumulado.

## Versão 0.5 — Sprint 1 (2026-07-10)

Melhorias exclusivamente de experiência de leitura executiva. Nenhuma regra de negócio, cálculo, pipeline ou estrutura de dados da v0.4 foi alterada.

- **Card YTD de destaque (apenas fatos)**: frase de período dinâmica ("Acumulado Jan–Jul/2026 vs Jan–Jul/2025", usando o mês limite da regra oficial v0.4), percentual como indicador principal com seta de direção (verde = crescimento, vermelho = queda) e valores absolutos comparativos como linha de suporte. Removida qualquer frase interpretativa. Estados garantidos: sem comparativo ("Sem comparativo disponível para este ano."), recorte vazio ("Sem dados no recorte selecionado.") e queda (mesma estrutura, só cor e seta mudam) — nunca percentual quebrado ou divisão por zero.
- **Hierarquia dos KPIs**: YTD passa a ser o KPI visualmente mais importante, mantendo a grade de 5 cards (mesma largura, altura e alinhamento) — destaque por tipografia ~25% maior no percentual e borda lateral fina na cor do sentimento. Cards reordenados por afinidade: YTD, financeiros (Vendas, Em Aberto), operacionais (Ticket Médio, Campanhas).
- **Formatação executiva dos valores monetários** em todos os cards das 3 páginas: ≥ R$ 1 milhão -> "R$ X,XX Mi"; ≥ R$ 1 mil -> "R$ X,XX mil"; abaixo, valor completo. Sem "K". Arredondamento pelo valor mais próximo (nunca truncado), com promoção de faixa no limite. Tooltips, tabelas analíticas e a auditoria continuam exibindo o valor completo. Contagens seguem inteiras; percentuais com uma casa decimal.

## Versão 0.5 — Sprint 2A (2026-07-10)

Filtros Premium, Sidebar e Componentes, conforme especificação oficial de UX (`docs/UX/SPRINT_2A_SPEC.md`). Nenhuma regra de negócio, cálculo, pipeline ou resultado numérico alterado — mudanças exclusivamente de apresentação.

- **Semântica de cores do tema**: cor de destaque (accent) da interface substituída por azul petróleo neutro provisório (`primaryColor` no config.toml), eliminando o vermelho padrão do Streamlit em chips, seleção ativa e foco. Regra de sistema documentada: vermelho exclusivo para sentimento negativo, verde exclusivo para positivo, interface sempre neutra.
- **Radios → Segmented Control**: os toggles de Métrica de Valor e Critério de Mês passam a segmented control (opções unidas, ativa preenchida na cor neutra), com os mesmos rótulos, mesmas keys e mesmos padrões oficiais (Valor Líquido / Mês Veiculação). Desmarcar a opção ativa retorna ao padrão — o toggle nunca fica sem valor.
- **Filtro de Grupo recolhido por padrão** (Performance Comercial): componente compacto com resumo ("Grupo: Todos" / nomes até 3 / "A, B +N" / "Grupo: Nenhum selecionado"), abrindo painel com checkboxes e atalhos Selecionar todos/Limpar. Semântica idêntica ao filtro anterior (todos marcados por padrão; recorte vazio segue a regra existente).
- **Barra de filtros em linha única** (Performance Comercial): Ano, Grupo recolhido e segmented controls numa única faixa horizontal com alinhamento vertical consistente, substituindo as linhas empilhadas.
- **Sidebar reestruturada**: nome do produto -> bloco de status dos dados (indicador + "Dados atualizados" + "há X min · sincronizado às HH:MM") -> botão "Atualizar dados agora" -> nota de rodapé sobre o ciclo automático de 15 minutos.

## Versão 0.5 — Sprint 2B (2026-07-10)

Transformação visual da página Performance Comercial para o padrão executivo premium (Design System v0.5 + Wireframe Executivo + Mockup aprovado — `docs/09_ESPECIFICACAO_SPRINT_2B.md`, com o adendo de resolução de conflitos C1-C10 e decisões 34-37 da Memória Oficial). Nenhuma regra de negócio, cálculo, consulta ou resultado numérico alterado.

- **Fundação visual (2B.1)**: design tokens aplicados — cor de MARCA verde AdTarget (#0B7A66) para identidade/navegação/seleção, deliberadamente distinta do Verde Positivo de desempenho (#1E9E52); fundo de página #F5F6F8; superfícies brancas; radius 12/8/999; sombra sutil; números tabulares.
- **Masthead (2B.2)**: título + subtítulo à esquerda; "atualizado há X min", botão "↻ Atualizar" (movido da sidebar) e toggle de tema desabilitado (dark mode em estudo) à direita. Botão Exportar removido da Sprint por decisão de PO (C6).
- **Sidebar = navegação oficial (2B.3, decisão 34)**: logo, navegação (Performance Comercial, Analítico Comercial, Analítico Veículos, 🔧 Auditoria temporário) com estado ativo na cor de marca, e bloco de status somente leitura. Sem botão na sidebar.
- **Filtros (2B.4)**: Ano como segmented control; Grupo mantém o componente recolhido com resumo (Sprint 2A) + botão "Limpar filtros" sempre visível (retorna ao padrão: todos marcados).
- **KPIs (2B.5)**: linha única com Card Hero de YTD (Display 42px, seta e cor semântica, ênfase estrutural — nunca fundo em cor de marca) + 4 secundários (Vendas em verde positivo, Em Aberto em âmbar, Ticket Médio, Campanhas), mesma altura, tooltips com valor completo.
- **Insights automáticos (2B.6, decisão 36)**: até 4 cápsulas factuais derivadas exclusivamente de métricas oficiais (concentração do grupo líder, maior mês, maior queda mês a mês).
- **Gráfico Hero (2B.7)**: abas Vendas / Ticket Médio (controle primário) com toggles Líquido/Bruto e Ganho/Veiculação como controles secundários no cabeçalho — estado único da página, todos os blocos reagem juntos, comportamento inalterado. Ano corrente em cor de marca sólida, anterior tracejado cinza (C10), grid sutil, meses futuros como zona esmaecida "sem dado disponível", rótulos no pico e no último mês.
- **Rankings Top 5 (2B.8)**: valor + % + badge de tendência (Variante 1: ▲/▼ + %, variação vs mesmo intervalo comparável do YTD, no toggle ativo; "—" sem base anterior); links "ver tudo →" com navegação cruzada para as páginas analíticas.
- **Estados (2B.9)**: toast de confirmação na atualização manual; vazio e erro mantidos. **Microinterações (2B.10)**: tooltips revelam valor completo; "clique em barra aplica filtro" adiado (C8).
- Novas agregações de apresentação em metrics.py (tendencia_por_dimensao, tendencia_grupo_veiculo, destaques_do_recorte), derivadas apenas dos buckets oficiais, com 7 testes — incluindo prova de que não alteram nenhum indicador existente.
