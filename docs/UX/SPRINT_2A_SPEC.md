# Sprint 2A — Especificação de UX (v0.5) — AdTarget Intelligence

## Sobre este documento

Especificação oficial e aprovada da Sprint 2A da v0.5 do AdTarget Intelligence, pronta para implementação no Cowork. Documento de UX/UI puro: nenhuma regra de negócio, cálculo, métrica ou arquitetura de dados é alterada por qualquer item aqui descrito. As regras de negócio permanecem as consolidadas na v0.4 e registradas em `docs/00_MEMORIA_OFICIAL.md` e `docs/02_REGRAS_DE_NEGOCIO_E_METRICAS.md`.

## Contexto

A v0.4 consolidou definitivamente as regras de negócio e cálculos do produto. A v0.5 desloca o foco para experiência do usuário, com o objetivo declarado de que um diretor (CEO, diretor de marketing ou diretor comercial) entenda a situação da empresa em menos de 30 segundos ao abrir o dashboard.

A v0.5 Sprint 1, já publicada, entregou: nova comunicação do card de YTD (percentual como indicador principal, período comparável explícito, valores absolutos de apoio, sem frases interpretativas), hierarquia visual integrada entre os 5 KPIs do topo (destaque de 20 a 30% no card de YTD via tipografia e borda, sem hero band e sem quebrar a leitura horizontal) e formatação executiva de valores monetários em todos os cards (Mi / mil / valor completo, sem uso de "K", com valor integral preservado em tooltips e tabelas).

A partir da Auditoria de UX da v0.4 (`docs/07_AUDITORIA_UX_V0.4.md`) e da revisão de produto que cobriu Filtros Premium, Dark Mode, Gráficos, Sidebar e Componentes, foi montado o backlog da Sprint 2, dividido em duas entregas menores para reduzir risco: Sprint 2A (Filtros Premium, Sidebar e Componentes) e Sprint 2B (Gráficos). Este documento cobre exclusivamente a Sprint 2A.

## Escopo da Sprint 2A

1. Radios → Segmented Control
2. Correção da semântica de cores do tema
3. Filtro de Grupo recolhido por padrão
4. Consolidação da barra de filtros em uma única linha
5. Reorganização estrutural da sidebar

Fora do escopo desta sprint, por decisão de Product Owner: aproveitamento do espaço ocioso da sidebar com contexto de escala da base (não resolve uma dor real do usuário neste momento) e todo o tema Gráficos (fica para a Sprint 2B).

---

## 1. Radios → Segmented Control

**Escopo:** os dois toggles hoje em radio nativo (Métrica de Valor: Líquido/Bruto; Critério de Mês: Ganho/Veiculação).

**Comportamento visual alvo:** as duas opções de cada grupo aparecem unidas num único componente, sem bolinha de rádio, sem espaçamento solto entre rótulo e opção. Opção ativa com fundo preenchido na cor neutra definida no item 2, opção inativa com fundo transparente e texto em tom secundário. Troca de estado no primeiro clique, sem confirmação adicional.

**Rótulo do grupo** ("Métrica de valor", "Critério de mês") continua acima do controle, com papel de legenda, não de instrução.

**Estados:** hover na opção inativa com leve destaque de fundo; foco por teclado com contorno visível.

**Posicionamento:** lado a lado como hoje, a menos que a consolidação da barra (item 4) exija reposicionar, caso em que este item se adapta ao novo layout, não o contrário.

**Fora de escopo:** nenhuma mudança nos textos das opções, nos valores padrão (Valor Líquido / Mês Veiculação continuam oficiais) ou em quais blocos os toggles recalculam. Isso é regra de negócio já fechada, aqui é só a pele do componente.

## 2. Correção da semântica de cores do tema

**Problema de origem:** a cor de destaque padrão do tema (hoje usada no "x" dos chips do multiselect de Grupo) é a mesma cor usada para sentimento de queda no card de YTD.

**Ação:** substituir a cor de destaque (accent) do tema por uma cor neutra de interface, sem carga de sentimento. Como a paleta de marca ainda não existe formalmente, usar um neutro provisório (grafite ou azul petróleo), evitando qualquer tom que leia como positivo ou negativo.

**Regra de sistema de cor a partir desta sprint** (documentada aqui para não se perder):
- Vermelho: exclusivo para sentimento negativo (queda, alerta, erro).
- Verde: exclusivo para sentimento positivo (crescimento).
- Qualquer outro elemento de interface (chips, seleção ativa, borda de foco): nunca vermelho nem verde.

**Onde muda:** chips do multiselect de Grupo, seleção ativa de qualquer multiselect futuro nas páginas analíticas, estado ativo do segmented control do item 1.

**Onde não muda:** cor de sentimento do card de YTD e de eventuais alertas de qualidade.

**Validação antes de publicar:** conferir as 3 páginas mais a aba de Auditoria, garantindo que nenhum componente ainda herde o vermelho antigo por engano.

## 3. Filtro de Grupo recolhido por padrão

**Estado padrão ao carregar:** o filtro aparece como um componente único e compacto, mostrando resumo, nunca a lista expandida de chips.

**Regras de resumo por quantidade selecionada:**
- Todos selecionados (padrão da página, 21 de 21 hoje): "Grupo: Todos"
- Seleção parcial pequena (até 3): mostra os nomes, "Grupo: Disney, Teads, Brasil 247"
- Seleção parcial maior que o espaço disponível: nomes que couberem + contador, "Grupo: Disney, Teads +5"
- Nenhum selecionado: cards e gráficos seguem a regra de negócio já existente para recorte vazio; o resumo do filtro mostra "Grupo: Nenhum selecionado", deixando claro que o vazio é intencional, não erro.

**Regra de espaço (decisão de Product Owner):** o resumo do filtro nunca poderá ocupar mais de uma linha. Caso o espaço horizontal seja insuficiente, o componente deverá resumir automaticamente a seleção mantendo a barra de filtros em uma única linha.

**Interação:** clique no componente recolhido abre um painel com a lista completa em checkboxes, mantendo os atalhos de limpar tudo/selecionar tudo já existentes. Fechar o painel (clique fora ou Esc) aplica a seleção e volta ao estado recolhido, resumo atualizado.

**Fora de escopo:** lista de grupos disponíveis, regra de seleção múltipla com tudo marcado por padrão, qualquer filtro em cascata novo. Só a apresentação do filtro que já existe muda.

## 4. Consolidação da barra de filtros em uma única linha

**Layout alvo:** uma faixa horizontal única, da esquerda para a direita: Ano, Grupo recolhido (item 3), segmented controls (item 1) alinhados à direita da mesma faixa. Substitui as 4 linhas verticais de hoje.

**Regra de consistência visual (decisão de Product Owner):** todos os controles da barra de filtros deverão possuir a mesma altura visual, alinhamento vertical e espaçamento horizontal consistente.

**Responsividade:**
- Desktop largo: tudo numa linha só.
- Notebook 13-14": se não couber, os dois segmented controls podem quebrar para uma segunda linha, mas Ano + Grupo permanecem sempre juntos na primeira (são filtro de recorte de dado; os toggles são de exibição, a diferenciação é proposital).
- Tela menor: empilha verticalmente na ordem Ano, Grupo, Métrica de Valor, Critério de Mês, sem sobreposição.

**Dependência:** este item só fecha depois dos itens 1 e 3 estarem prontos, é o resultado de juntar as duas peças já reformadas numa faixa só. Ordem sugerida: 3 e 1 podem vir em qualquer ordem entre si, o item 4 sempre por último.

**Fora de escopo:** nenhuma mudança na lógica de filtro, só na disposição espacial.

## 5. Reorganização estrutural da sidebar

**Escopo desta sprint:** só estrutura e hierarquia. Acabamento de cor de marca fica para quando a paleta existir, como segunda camada esperada, não retrabalho.

**Estrutura alvo, de cima para baixo:**
1. Nome do produto, mantém como está.
2. Bloco de status dos dados, isolado visualmente do botão: indicador de estado (ponto ou ícone) + "Dados atualizados" + linha secundária menor com "há X minutos" e horário da última sincronização.
3. Botão "Atualizar dados agora", com espaçamento claro acima separando-o do bloco de status.
4. Texto explicativo sobre o ciclo automático de 15 minutos, reposicionado abaixo do botão como nota de rodapé, não como abertura da sidebar.

**Fora de escopo:** navegação (continua em abas no topo), atalho de filtro, contexto de escala da base (cortado da sprint por decisão do Product Owner), cor de marca.

---

## Aviso permanente válido para as 5 especificações

Nenhuma altera cálculo, regra de negócio, dado exibido, ou comportamento de filtro além da apresentação. Onde havia dúvida de texto novo, foi usado apenas o estritamente necessário para os estados descritos aqui (caso do "Grupo: Nenhum selecionado"), sem inventar rótulo além disso.

## Ordem de implementação recomendada

**2 → 1 → 3 → 4 → 5.**

Item 2 primeiro por ser isolado. Item 1 em seguida, também isolado. Itens 3 e 4 emparelhados por dependência direta. Item 5 por último, é o mais independente dos quatro, pode rodar em paralelo se o Cowork tiver capacidade, mantendo a mesma disciplina de implementar, validar e publicar um de cada vez.

---

## Critério de Aceite da Sprint

- Nenhuma regra de negócio poderá ser alterada.
- Nenhum cálculo poderá ser alterado.
- Nenhum resultado numérico poderá mudar.
- Todos os testes existentes deverão continuar passando.
- As três páginas do dashboard deverão manter consistência visual.
- A aba de Auditoria deverá continuar funcionando exatamente como na v0.5 Sprint 1.
- Nenhum componente poderá utilizar vermelho como cor neutra de interface.

---

## Próximo passo

Após validação desta especificação, seguir para a Sprint 2B (Gráficos): rótulo de valor nas barras de ranking, espessura de linha diferenciada entre 2025 e 2026, grid mais sutil no gráfico de evolução, e destaque na barra líder de cada ranking.
