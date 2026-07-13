# 09. Especificação de Implementação — Sprint 2B (v0.5) — AdTarget Intelligence

## 0. Sobre este documento

Este é o documento oficial e autocontido de especificação da Sprint 2B do AdTarget Intelligence. Foi escrito para ser executado sem depender de nenhum histórico de conversa anterior — toda decisão relevante de Design System, Wireframe Executivo e Product Owner está reproduzida aqui na íntegra, não apenas referenciada.

**Status: aprovado para implementação.** A fase de Produto está oficialmente encerrada. A arquitetura visual, o Design System, o Wireframe Executivo e o Mockup de Alta Fidelidade estão todos congelados. Este documento não introduz nenhuma decisão nova de Produto — ele consolida o que já foi aprovado.

**Regra de ouro deste documento**: em qualquer conflito entre estética e regra de negócio, a regra de negócio sempre prevalece. Em qualquer dúvida ou conflito entre este documento e a documentação oficial do produto, a implementação deve ser interrompida e o conflito reportado — nenhuma decisão de arquitetura, regra de negócio ou cálculo deve ser tomada unilateralmente durante a execução.

---

## 1. Contexto e Objetivo da Sprint

A AdTarget Intelligence é uma aplicação Python + Streamlit que substitui um dashboard Power BI para a AdTarget, empresa de representação comercial de veículos de mídia. A Sprint 2A (já publicada em produção) implementou a base funcional da aplicação. A Sprint 2B **não adiciona nenhuma funcionalidade de negócio nova** — seu único objetivo é transformar a camada visual da página Performance Comercial para o padrão definido no Design System v0.5 e no Wireframe Executivo aprovados, preservando integralmente toda a camada de negócio, cálculo e regra já construída até a Sprint 2A.

Ao final da Sprint, a percepção do usuário deve ser a de um software executivo premium — o objetivo declarado é que a aplicação deixe de parecer um dashboard técnico em Streamlit e passe a parecer um produto desenhado especificamente para CEOs, Diretores Comerciais e Executivos de Growth.

**Esta deve ser a maior evolução visual do projeto desde seu início.**

---

## 2. Fontes Oficiais e Ordem de Precedência

Em caso de qualquer dúvida, prevalece sempre o documento mais recente na lista abaixo:

1. `00_MEMORIA_OFICIAL.md`
2. `04_WIREFRAMES_MVP.md`
3. `07_DESIGN_SYSTEM.md`
4. `08_WIREFRAME_EXECUTIVO_SPRINT_2B.md`
5. Mockup de Alta Fidelidade aprovado (`mockup_performance_comercial.html`)
6. Este documento (`09_ESPECIFICACAO_SPRINT_2B.md`)
7. Código atual da Sprint 2A

Nenhuma decisão documentada deve ser reinterpretada. As seções 5 e 6 abaixo reproduzem o conteúdo integral dos documentos 07 e 08 para que este documento seja lido de forma autossuficiente.

---

## 3. Escopo Aprovado da Sprint 2B

Implementar integralmente, na página Performance Comercial:

- Design Tokens (cores, tipografia, escala tipográfica, grid, espaçamentos, radius, sombras, fundo da aplicação)
- Masthead
- Sidebar e Navegação
- Sistema de filtros
- Cards de KPI, incluindo o Card Hero de YTD
- Faixa de Insights automáticos
- Gráfico Hero (com as duas abas Receita / Ticket Médio)
- Tratamento visual dos meses futuros no gráfico
- Rankings Top 5 (Veículos, Agências, Clientes), incluindo o indicador de tendência aprovado
- Navegação cruzada para as páginas analíticas
- Microinterações previstas no Wireframe e no Mockup
- Polimento visual completo, incluindo os ajustes de polimento listados na seção 8.6

### 3.1 Fora de Escopo (Explicitamente Não Implementar)

- Dark Mode (arquitetura pode prever o espaço do controle no Masthead, mas o efeito visual não é implementado nesta Sprint)
- Qualquer funcionalidade nova
- Qualquer KPI novo
- Qualquer filtro novo
- Qualquer cálculo novo
- Qualquer regra de negócio nova
- Qualquer consulta nova à camada de dados
- Qualquer melhoria não prevista nesta documentação, mesmo que pareça pequena ou óbvia
- Qualquer alteração de arquitetura de dados ou de estrutura de pastas definida em `03_ARQUITETURA_TECNICA.md`
- Terceira aba de Pipeline no Gráfico Hero (explicitamente adiada — ver seção 8.4)

---

## 4. Restrições Não-Negociáveis

Estas restrições têm prioridade sobre qualquer outra instrução deste documento, incluindo as instruções de fidelidade visual ao Mockup:

- **Nenhuma regra de negócio poderá ser alterada.**
- **Nenhum cálculo poderá ser alterado.**
- **Nenhum resultado numérico poderá mudar.** Os números exibidos pela aplicação após a Sprint 2B devem ser idênticos aos exibidos antes dela, para o mesmo recorte de filtros.
- Nenhuma consulta da camada de dados poderá ser alterada.
- Nenhum comportamento funcional existente poderá mudar.
- Nenhuma lógica de filtro poderá mudar.
- Nenhuma regra da página de Auditoria poderá mudar.
- Nenhum teste existente poderá deixar de passar.
- Nenhum documento oficial poderá ser desrespeitado.
- **Em qualquer conflito entre estética e fidelidade às regras de negócio, a fidelidade às regras de negócio sempre prevalece.**
- **Em caso de dúvida ou conflito entre esta especificação e a documentação oficial do produto (itens 1 a 5 da seção 2), a implementação deve ser interrompida e o conflito reportado antes de prosseguir.** Nenhuma decisão de arquitetura, regra de negócio ou cálculo deve ser tomada unilateralmente durante a execução.

---

## 5. Design System v0.5 — Conteúdo Integral (Congelado)

*Reprodução integral de `07_DESIGN_SYSTEM.md`, incluindo as decisões de separação de cor confirmadas como regra permanente pelo Product Owner.*

### 5.1 Propósito

Referência oficial de linguagem visual do AdTarget Intelligence. Nenhuma Sprint cria componente novo, cor nova, ou padrão de espaçamento novo sem antes verificar aqui. Este documento não define regra de negócio, cálculo, ou KPI — define apenas como a informação aparece na tela.

### 5.2 Princípios de Design

1. Hierarquia antes de estética.
2. Cor tem significado, nunca decoração. Verde é alta. Vermelho é queda ou risco. Se uma cor não carrega informação, ela é neutra.
3. Silêncio visual é uma escolha ativa.
4. Consistência entre páginas é inegociável — o mesmo componente, quando repetido, é sempre idêntico.
5. Executivo não escava — nada essencial deve depender de hover, clique ou scroll para ser entendido.

### 5.3 Tipografia

Família tipográfica: sans-serif de uso corporativo/produto (ex: Inter ou equivalente), com suporte a números tabulares (largura fixa por dígito) — obrigatório para qualquer número monetário.

| Nível | Tamanho | Peso | Uso |
|---|---|---|---|
| Display / Hero Number | 40–44px | Bold | Número do card YTD (KPI principal) |
| KPI Number | 26–28px | Semibold | Números dos demais cards de KPI |
| Título de Página | 22–24px | Semibold | Título no Masthead |
| Título de Seção/Card | 15–16px | Semibold | "Evolução da Receita", "Top 5 Veículos" |
| Corpo / Label | 13–14px | Regular/Medium | Rótulos de filtro, texto de tabela, texto de insight |
| Caption / Apoio | 12px | Regular | "vs ano anterior", legendas de gráfico, timestamps |

Regra fixa: números nunca usam peso Regular quando são o dado principal do bloco — sempre Semibold ou Bold.

### 5.4 Cor

**Paleta semântica [REGRA PERMANENTE]:**

| Papel | Uso | Observação |
|---|---|---|
| **Positivo (verde)** | Exclusivamente desempenho: alta vs período anterior, Faturamento Realizado, status FATURADO/DIRETO | Mesmo verde em toda a aplicação. Nunca usado para identidade visual, navegação ou seleção — esse papel pertence só à Cor de Marca |
| **Negativo (vermelho)** | Queda vs período anterior, alertas de qualidade críticos, CANCELADO | Reservado para o que exige atenção real — nunca usado em elemento decorativo |
| **Atenção (âmbar)** | Pipeline em Aberto, alertas informativos (não críticos), SEM_STATUS | Pipeline não é bom nem ruim, é "ainda não decidido" |
| **Neutro/Inativo** | BONIFICADO, elementos desabilitados, texto de apoio | Cinza médio, baixo contraste intencional |
| **Marca (verde AdTarget)** | Logo, identidade visual, navegação ativa, foco, seleção, componentes institucionais | Nunca é usada para indicar desempenho, alta ou faturamento realizado. É uma cor de identidade, não de dado. Tom deliberadamente distinto do Verde Positivo (marca mais fria/saturada, positivo mais quente), para que as duas nunca sejam confundidas na mesma tela |

**Aplicação por status de negócio [DECIDIDO]** — mapeamento único e fixo, usado em qualquer gráfico ou indicador que mostre status:

| Status | Cor |
|---|---|
| FATURADO | Verde |
| DIRETO | Verde (tom/padrão levemente distinto — soma dentro de Faturamento Realizado mas é identificado separado) |
| CHECKING / AGUARD. DOC. VEÍCULO (Pipeline) | Âmbar |
| CANCELADO | Vermelho |
| BONIFICADO | Cinza neutro |
| SEM_STATUS | Vermelho ou âmbar mais intenso — é alerta de qualidade, precisa destoar |

### 5.5 Espaçamento e Grid

Unidade base: 4px. Escala oficial: `4 · 8 · 12 · 16 · 24 · 32 · 48 · 64`.

| Contexto | Valor |
|---|---|
| Padding interno de card | 24 |
| Gap entre cards (mesma linha) | 16–24 |
| Gap entre seções | 32 |
| Padding interno de tabela (célula) | 12 |
| Gap entre ícone e texto | 8 |

Grid: 12 colunas, largura máxima de conteúdo definida, sidebar com largura fixa, conteúdo principal fluido dentro do grid.

### 5.6 Bordas, Radius, Sombra

| Elemento | Radius |
|---|---|
| Card (KPI, gráfico, ranking) | 12px |
| Botão, input, segmented control | 8px |
| Chip / Pill | 999px (totalmente arredondado) |

Sombra usada com extrema moderação: Nível 1 (quase imperceptível) para todo card em repouso; Nível 2 (mais perceptível) reservado para hover ou elemento temporariamente elevado. Borda 1px cor neutra clara como alternativa à sombra em tabelas e divisores.

### 5.7 Iconografia

Estilo outline, traço consistente, biblioteca única em toda a aplicação. Tamanhos: 16px (inline com texto), 20px (padrão em botão/nav), 24px (destaque em card). Ícone sempre funcional, nunca decorativo.

### 5.8 Componentes

**Masthead [DECIDIDO]** — presente no topo de todas as páginas, mesma estrutura sempre:
- Título da página + subtítulo de uma linha à esquerda
- À direita: caption "atualizado há X min", botão Exportar (dropdown único agrupando PDF / Excel / Copiar imagem — um botão, um menu, não três botões separados), botão "Atualizar dados agora" (vive exclusivamente aqui, não existe mais na sidebar), ícone de toggle de tema (espaço reservado no layout; efeito visual do Dark Mode não é implementado nesta Sprint)

**Sidebar [DECIDIDO]:**
- Logo no topo
- Navegação com exatamente 3 itens, nesta ordem: Performance Comercial, Analítico Faturamento, Analítico Veículos. Nenhum item adicional, nenhum item desabilitado ou "em breve"
- Estado ativo: fundo de destaque sutil + Cor de Marca no texto/ícone. Estado hover: fundo levemente diferente do repouso
- Abaixo da navegação, separador, depois bloco de status somente leitura: "● Dados atualizados", "há X minutos", "Última sincronização: HH:MM"
- **Sem botão na sidebar.** Toda ação vive no Masthead

**Cards de KPI** — dois tamanhos fixos:
- **Card Hero** (1 por página — ex: YTD na página executiva): maior, número em Display, seta/símbolo de direção, cor semântica aplicada ao número e à seta. **[REGRA PERMANENTE]** A ênfase do Card Hero é sempre estrutural — tamanho, peso tipográfico, padding e posição — nunca por preenchimento na Cor de Marca. Isso evita o conflito de quando o número for negativo: um card com fundo na Cor de Marca (identidade) exibindo uma seta vermelha (semântica de queda) misturaria os dois sistemas de cor que a seção 5.4 mantém propositalmente separados.
- **Card Secundário** (demais KPIs da mesma linha): mesma altura entre si, número em tamanho KPI Number, rótulo acima, texto de apoio pequeno abaixo quando aplicável

**Botões:**

| Tipo | Uso |
|---|---|
| Primário | Uma única ação de destaque por tela no máximo (ex: "Atualizar dados agora") |
| Secundário / Outline | Ações de apoio (ex: "Limpar filtros") |
| Ghost / Texto | Ações de baixa hierarquia dentro de card |
| Ícone isolado | Ações reconhecíveis por símbolo universal, sempre com tooltip |

**Filtros:**
- **Ano**: segmented control (não dropdown) — seleção única entre poucas opções
- **Grupo, Veículo, Agência, Cliente, Status, Executivo**: multi-select com chips removíveis individualmente + contador quando exceder o espaço ("+8"). Botão "Limpar filtros" sempre visível ao lado, nunca escondido em menu
- Barra de filtro nunca duplicada entre topo de página e sidebar

**Chips / Pills**: radius total (999px), altura fixa, cor de fundo clara com texto na cor semântica correspondente quando aplicável a status.

**Inputs**: radius 8px, borda 1px neutra em repouso, borda na Cor de Marca em foco, mensagem de erro abaixo do campo em vermelho (nunca só a borda vermelha sem texto).

**Tabelas (páginas analíticas)**: cabeçalho fixo ao rolar, linha zebrada sutil, números alinhados à direita com fonte tabular, texto alinhado à esquerda, status como chip colorido, indicador claro de ordenação ativa.

**Gráficos:**
- Linha (evolução mensal): ano corrente em traço sólido e cor de marca/positivo, ano anterior em traço tracejado e cor neutra — nunca a mesma cor para os dois
- Meses futuros sem dado: área esmaecida/hachurada com rótulo pequeno "sem dado disponível" — nunca linha reta em zero, nunca vazio sem explicação
- Barra (rankings): sempre horizontal, valor e percentual sempre visíveis inline, nunca dependente de hover para o dado essencial
- Cores de série seguem o mapeamento semântico da seção 5.4 quando o gráfico representa status ou comparação positiva/negativa

**Estados de interface [DECIDIDO]:**

| Estado | Comportamento |
|---|---|
| Carregando | Skeleton no formato exato do componente final — nunca spinner genérico central, nunca tela em branco |
| Vazio (filtro sem resultado) | Mensagem clara no espaço do próprio card/gráfico ("Sem dados no recorte selecionado") |
| Erro | Mensagem amigável e específica, nunca stack trace |
| Sucesso / Confirmação | Toast discreto no canto da tela, some sozinho após poucos segundos |

### 5.9 Insights Automáticos

Cápsula curta (ícone + 1 linha de texto), nunca repetindo número que já aparece em card ao lado — sempre entrega leitura adicional (concentração, variação, destaque) que o card ou gráfico não entrega sozinho. Máximo de 4 por página.

### 5.10 Dark Mode [EM ESTUDO — não implementar nesta Sprint]

Registrado como direção, não como especificação: contexto de uso provavelmente é apresentação/projeção, não uso noturno individual; fundo não deve ser preto puro; cores semânticas precisam de revisão própria em fundo escuro; texto nunca branco puro. Nenhuma decisão de implementação até isso virar especificação numa versão futura deste documento.

---

## 6. Wireframe Executivo — Arquitetura Aprovada (Congelado)

*Reprodução integral de `08_WIREFRAME_EXECUTIVO_SPRINT_2B.md`, incluindo as decisões finais de Product Owner e a revisão crítica final já incorporada.*

### 6.1 Teste de Aceite do Wireframe

Um executivo abre a página e, sem clicar em nada, em até 30 segundos, consegue responder:

1. Estou melhor ou pior que o ano passado, e por quanto?
2. Isso é sustentado ao longo do ano ou foi um mês isolado?
3. Quem sustenta esse resultado (grupo, agência, cliente)?
4. Quanto ainda está represado (pipeline) e isso é relevante?

A ordem vertical da página segue exatamente essa sequência de perguntas.

### 6.2 Wireframe Completo — Performance Comercial

```
┌───────────┬──────────────────────────────────────────────────────────────────────────┐
│           │  Performance Comercial                                                    │
│  AdTarget │  Visão geral de vendas, campanhas e faturamento                           │
│Intelligence│                                                atualizado há 3 min       │
│           │                                     [Exportar ▾]  [↻ Atualizar]   [☾]     │
│  ───────  ├──────────────────────────────────────────────────────────────────────────┤
│ ▸ Performance │  Ano  (2024 │ 2025 │●2026)      Grupo [DISNEY ×][TEADS ×][+8 ▾] [Limpar filtros]│
│   Comercial   ├──────────────────────────────────────────────────────────────────────┤
│   (ativo)     │ ┌────────────────────┐┌───────────┐┌───────────┐┌─────────┐┌────────┐│
│ ▸ Analítico   │ │                    ││Faturamento││ Pipeline  ││ Ticket  ││Campanh.││
│   Faturamento │ │   ▲ 55,8%          ││ Realizado ││ em Aberto ││ Médio   ││        ││
│ ▸ Analítico   │ │   HERO · YTD       ││           ││           ││         ││        ││
│   Veículos    │ │   vs Ano Anterior  ││R$13,28 Mi ││ R$8,38 Mi ││R$87,97K ││   64   ││
│               │ │                    ││dos quais  ││37,2% da   ││         ││Cliente ││
│  ───────      │ │ R$12,5Mi este ano  ││R$X DIRETO ││receita    ││         ││+Campanh││
│ ○ Dados       │ │ vs R$8,0Mi ano ant.││           ││líquida    ││         ││        ││
│  atualizados  │ └────────────────────┘└───────────┘└───────────┘└─────────┘└────────┘│
│ há 3 min      ├──────────────────────────────────────────────────────────────────────┤
│ Última        │ 💡 Disney concentra 41% do faturamento no recorte selecionado         │
│ sincronização:│ 💡 Junho concentrou o maior volume de faturamento do ano, com R$4,87Mi│
│ 15:27         │ 💡 Julho teve a maior queda mês a mês do período (-85% vs Jun)         │
│               ├──────────────────────────────────────────────────────────────────────┤
│               │ Evolução      [●Receita] [ Ticket Médio ]    [●Líquido|Bruto] [●Ganho|Veic.]│
│               │ ┌────────────────────────────────────────────────────────────────────┐│
│               │ │5M                                                                   ││
│               │ │4M         4,87M                                                     ││
│               │ │3M     ___/\                                                         ││
│               │ │2M ___/     \___             ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ ││
│               │ │1M/              \_____      ▒▒ sem dado disponível ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ ││
│               │ │0                       \___  ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ ││
│               │ │  Jan Fev Mar Abr Mai Jun Jul  Ago  Set  Out  Nov  Dez                ││
│               │ │  ┄┄┄ 2025 (ano anterior)      ── 2026 (ano selecionado)              ││
│               │ └────────────────────────────────────────────────────────────────────┘│
│               ├──────────────────────────────────────────────────────────────────────┤
│               │ Top 5 Veículos           Top 5 Agências          Top 5 Clientes        │
│               │ TEADS—TEADS   R$4,0M 41% ▲12%  NACIONAL  R$6,2M 30% ▲8%  CAIXA R$6,9M 34% ▲15%│
│               │ DISNEY—DISNEY+R$2,1M 22% ▲6%   PROPEG    R$4,2M 20% ▲3%  SECOM R$4,8M 24% ▲4% │
│               │ BRASIL 247    R$1,3M 14% ▼4%   CALIA     R$2,1M 10% ▼5%  MIN.SAÚDE R$2,8M 14% ▼3%│
│               │ DISNEY—ESPN   R$0,9M  9% ▲2%   DEBITO    R$1,8M  9% ▲1%  MDS   R$0,9M  5% ▲1% │
│               │ MELODIA       R$0,6M  6% ▼9%   BINDER    R$1,6M  8% ▼2%  SEBRAE R$0,8M  4% ▼6%│
│               │ [ver tudo →]              [ver tudo →]              [ver tudo →]       │
│               ├──────────────────────────────────────────────────────────────────────┤
│               │ *Receita Líquida: Faturamento - Impostos - Devoluções - Cancelamentos  │
└───────────────┴──────────────────────────────────────────────────────────────────────┘
```

### 6.3 Leitura por Zona

| Zona | Responde a pergunta | Componente (Design System) |
|---|---|---|
| Masthead | "Isso é atual?" | Masthead §5.8 |
| Filtros | "Que recorte estou vendo?" | Segmented Control + Chips §5.8 |
| Card Hero | "Melhor ou pior que ano passado, quanto?" | Card Hero §5.8 |
| Cards Secundários | "Faturei quanto, quanto tá represado, ticket, volume" | Card Secundário §5.8 |
| Insights | "O que eu não veria olhando só os números?" | Insight Capsule §5.9 |
| Gráfico Hero | "Isso é sustentado ou foi um mês isolado?" | Gráfico de linha §5.8 |
| Rankings | "Quem sustenta o resultado?" | Gráfico de barra horizontal §5.8 |

Nenhuma zona exige clique para entregar sua resposta.

### 6.4 Decisões Finais de Product Owner (já congeladas)

- **Pipeline no Gráfico Hero**: adiado oficialmente para uma evolução futura, sem data definida. Gráfico Hero permanece com 2 abas (Receita / Ticket Médio) nesta versão. Card de Pipeline em Aberto continua sendo a única representação de Pipeline na página. Só deve entrar quando agregar leitura real, não por completude de interface.
- **Tendência nos Rankings**: aprovada a Variante 1 — badge de seta + percentual (ex: `▲12%`), reaproveitando exatamente a mesma linguagem visual do Card Hero. Sparkline e barra colorida foram descartadas.
- **Padronização dos links de rodapé dos rankings**: texto único "ver tudo →" nos três blocos (Veículos, Agências, Clientes), substituindo variações anteriores ("ver ranking completo", "ver todas", "ver todos").
- **Hierarquia visual do cabeçalho do Gráfico Hero**: as abas Receita/Ticket Médio devem ter peso visual maior (controle primário, mais destacado) que os toggles de Líquido/Bruto e Mês (Ganho)/Mês (Veiculação) (controles secundários, mais discretos) — para que o olho identifique primeiro "o que estou vendo" antes de "como estou vendo".
- **Orçamento vertical da página**: aceito conscientemente pelo Product Owner. Os rankings completos (Top 5 × 3 colunas, agora com o badge de tendência) podem ficar parcialmente abaixo da dobra em notebooks comuns. Isso não invalida o teste dos 30 segundos, porque a leitura principal (Card Hero + Insights) acontece antes de qualquer rolagem. **Não reduzir de Top 5 para Top 3** para tentar caber tudo acima da dobra — isso tiraria justamente a resposta à pergunta "quem sustenta o resultado".

### 6.5 Sprint 2B — Entregas (Escopo Congelado)

| # | Entrega | Depende de |
|---|---|---|
| 2B.1 | Fundação visual: tipografia, cores, espaçamento, radius, sombra (Design System aplicado) | — |
| 2B.2 | Masthead completo (título, período, export dropdown, refresh, toggle de tema sem função) | 2B.1 |
| 2B.3 | Sidebar com 3 itens fixos + bloco de status sem botão | 2B.1 |
| 2B.4 | Filtros (Ano segmented + Grupo chips) | 2B.1 |
| 2B.5 | Cards de KPI com hierarquia (Hero + 4 Secundários) | 2B.1 |
| 2B.6 | Insights automáticos (até 4 cápsulas) | 2B.5 |
| 2B.7 | Gráfico Hero com 2 abas (Receita / Ticket Médio) + tratamento de mês futuro | 2B.1 |
| 2B.8 | Rankings Top 5 com valor + % + badge de tendência (Variante 1) | 2B.1 |
| 2B.9 | Estados de interface (loading, vazio, erro, toast) | 2B.1–2B.8 |
| 2B.10 | Microinterações finas (hover em card revela cálculo, clique em barra aplica filtro) | 2B.1–2B.9 |

Nenhum item além destes dez entra nesta Sprint.

### 6.6 Ajustes de Polimento (resolver durante a implementação, sem necessidade de nova revisão de Produto)

- Padronizar os três links de rodapé dos rankings para "ver tudo →"
- Diferenciar peso visual entre as abas do Gráfico Hero (primário) e os toggles Líquido/Bruto e Ganho/Veiculação (secundário)

---

## 7. Mockup de Alta Fidelidade

O arquivo `mockup_performance_comercial.html` é a referência de fidelidade pixel-a-pixel aprovada pelo Product Owner. Ele é um arquivo estático (HTML/CSS puro, sem lógica, sem dado real, sem interatividade funcional) que materializa visualmente o Wireframe Executivo (seção 6) usando os tokens do Design System (seção 5).

A implementação da Sprint 2B deve reproduzir este Mockup com a maior fidelidade possível dentro das limitações do Streamlit — proporções, ritmo visual, espaçamentos, hierarquia, densidade e equilíbrio geral da página. Onde houver mais de uma forma de implementar um componente dentro das limitações do Streamlit, escolher sempre a alternativa que gere a melhor percepção de software executivo premium, priorizando clareza, hierarquia, consistência, simplicidade e elegância — e evitando excesso de bordas, cores, sombras ou elementos decorativos.

Este arquivo deve acompanhar o envio ao Cowork como anexo (ver seção 12).

---

## 8. Critérios de Aceite da Sprint 2B

- Nenhuma regra de negócio alterada
- Nenhum cálculo alterado
- Nenhum resultado numérico alterado
- Todos os testes existentes continuam passando
- Página de Auditoria funcionando exatamente como antes
- Interface consistente nas três páginas do MVP (Performance Comercial, Analítico Faturamento, Analítico Veículos)
- Aderência máxima ao Mockup de Alta Fidelidade aprovado
- Produto com aparência de software executivo premium
- Todos os itens da seção 6.5 (2B.1 a 2B.10) implementados
- Nenhum item da seção 3.1 (fora de escopo) implementado

---

## 9. Fluxo de Execução Obrigatório

1. Implementar integralmente os itens 2B.1 a 2B.10 (seção 6.5)
2. Executar toda a suíte de testes existente
3. Executar Ruff
4. Executar Smoke Test completo, cobrindo as 4 áreas:
   - Performance Comercial
   - Analítico Faturamento
   - Analítico Veículos
   - Auditoria
5. Fazer uma revisão crítica completa comparando a implementação com:
   - Mockup de Alta Fidelidade
   - Design System (seção 5)
   - Wireframe Executivo (seção 6)
6. Corrigir todas as divergências encontradas na revisão
7. Repetir os testes (passos 2 a 4) após as correções
8. Gerar um único commit local, com mensagem descritiva do escopo da Sprint 2B
9. **Não realizar push.** O commit permanece local até revisão e autorização explícita do Product Owner.

**Protocolo de dúvida ou conflito**: se, em qualquer etapa deste fluxo, surgir uma divergência entre este documento e o código atual da Sprint 2A, ou uma ambiguidade que exija decisão de arquitetura, regra de negócio ou cálculo não coberta explicitamente aqui, a implementação deve ser **interrompida** e o conflito **reportado** antes de qualquer decisão unilateral. Nenhuma suposição substitui uma decisão de Product Owner já registrada, e nenhuma nova suposição deve ser criada para preencher uma lacuna — a lacuna deve ser reportada como está.

---

## 10. Relatório Final Obrigatório

Ao concluir a Sprint, entregar um relatório contendo obrigatoriamente:

1. Resumo executivo da Sprint
2. Estratégia utilizada
3. Arquivos alterados
4. Decisões técnicas relevantes
5. Testes executados
6. Resultado da suíte de testes
7. Resultado do Ruff
8. Resultado do Smoke Test
9. Riscos conhecidos
10. Diferenças remanescentes entre a implementação e o Mockup (caso existam)
11. Autoavaliação de aderência ao Mockup, no seguinte formato:
    - Masthead: XX%
    - Sidebar: XX%
    - Filtros: XX%
    - Cards KPI: XX%
    - Hero YTD: XX%
    - Insights: XX%
    - Gráfico Hero: XX%
    - Rankings: XX%
    - Navegação: XX%
    - Consistência visual geral: XX%
12. Hash do commit local gerado

---

## 11. O que este documento não cobre

- Qualquer regra de cálculo, definição de métrica ou KPI — ver `01_DICIONARIO_DE_DADOS.md` e `02_REGRAS_DE_NEGOCIO_E_METRICAS.md`
- Estrutura de pastas, bibliotecas ou stack técnica além do já definido em `03_ARQUITETURA_TECNICA.md`
- Layout de Analítico Faturamento ou Analítico Veículos — fora de escopo desta Sprint
- Fase 1.2 (Campanhas, Metas, Executivos) — fora de escopo
- Efeito visual do Dark Mode — registrado como estudo, não implementar
- Terceira aba de Pipeline no Gráfico Hero — explicitamente adiada

---

## 12. ADENDO — Resolução oficial de conflitos (2026-07-10, decisões de Product Owner)

Registrado após a revisão de conflitos entre esta especificação/mockup e a documentação oficial v0.3+/v0.4. As resoluções abaixo PREVALECEM sobre o corpo deste documento e sobre o mockup onde houver divergência:

- **C1 (aprovado)**: cards usam a nomenclatura oficial v0.3 — **Vendas** (com decomposição "sendo X já faturado") e **Em Aberto** — nunca "Faturamento Realizado"/"Pipeline em Aberto". A decomposição DIRETO (v0.2) não é exibida.
- **C2 (aprovado)**: rodapé "Receita Líquida: Faturamento − Impostos − Devoluções − Cancelamentos" SUPRIMIDO (fórmula inexistente no modelo oficial); caption do Em Aberto permanece a oficial.
- **C3 (aprovado)**: abas do Gráfico Hero = **"Vendas" / "Ticket Médio"** (nunca "Receita").
- **C4 (decisão PO)**: **a sidebar passa a ser a navegação oficial do produto**, com 4 itens: Performance Comercial, Analítico Comercial, Analítico Veículos e 🔧 Auditoria (temporário — removido junto com a ferramenta). Supersede a navegação em st.tabs do documento 03.
- **C5 (registrado)**: o mapa de status da seção 5.4 está defasado (v0.2); correção para a Sprint do Analítico: A VEICULAR / EM VEICULAÇÃO / CHECKING / AGUARD. DOC. VEÍCULO = âmbar (Em Aberto); SEM_STATUS não existe mais como categoria (apenas guarda-corpo do alerta 4).
- **C6 (decisão PO)**: botão **Exportar removido completamente** desta Sprint — sem placeholder e sem espaço reservado.
- **C7 (decisão PO)**: Insights Automáticos mantidos, implementados EXCLUSIVAMENTE como agregações derivadas das métricas oficiais existentes (resumem, comparam ou destacam dados já calculados; nenhuma regra de negócio nova). Badge de tendência dos rankings = variação da entidade vs o mesmo intervalo comparável do YTD (regra v0.4), no toggle ativo — informação nova de apresentação; nenhum número existente muda.
- **C8 (decisão PO)**: microinteração "clique em barra aplica filtro" ADIADA — fora da Sprint 2B.
- **C9 (aprovado)**: formatação monetária segue a regra oficial v0.5-S1 em todos os elementos (Mi/mil, 2 casas, sem "K"/"M").
- **C10 (aprovado)**: linha do ano corrente na **cor de marca** (#0B7A66); ano anterior cinza tracejado.
