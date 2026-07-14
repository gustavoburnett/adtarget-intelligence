# AdTarget Intelligence

## Release 1.0

### Resumo executivo

O AdTarget Intelligence substitui o dashboard Power BI por um produto próprio de inteligência comercial, lendo a Planilha de Vendas diretamente e recalculando todos os indicadores a partir das linhas brutas. A Release 1.0 encerra o ciclo de fundação (dados, regras de negócio, interface e design system): um executivo abre o produto e responde, em menos de 30 segundos, se a AdTarget está melhor ou pior que o ano anterior, quanto está vendido e ainda não faturado, e quem sustenta o resultado. O design atual fica congelado como baseline oficial; os próximos ciclos focam em novos módulos e inteligência comercial.

### Principais melhorias

Regras de negócio consolidadas e auditadas: indicadores oficiais Vendas / Faturado / Em Aberto (Em Aberto = Vendas − Faturado) sobre 8 status controlados; critério temporal oficial MÊS (VEICULAÇÃO) com fonte única de verdade no código; YTD verdadeiro (ano corrente corta no mês atual; anos encerrados comparam inteiros). Experiência executiva: página Performance com Card Hero de YTD factual, KPI band, insights automáticos derivados das métricas oficiais, Gráfico Hero com abas Vendas/Ticket Médio e rankings Top 5 com badge de tendência. Sistema de filtros compacto padrão Notion/Linear: campo com resumo, busca com realce, seleção em duas camadas (nada recalcula antes do Aplicar). Formatação executiva (Mi/mil) com valores completos em tooltips, tabelas e auditoria.

### Arquitetura

Python + Streamlit sobre Google Sheets (Service Account, cache de 15 min), sem banco na Fase 1. Camadas estritas: loader (leitura bruta, cabeçalho autodetectado) → cleaning (normalização genérica) → quality_checks (alertas que nunca corrigem) → metrics (única fonte de cálculo — a interface não faz nenhuma conta). Navegação em sidebar; ferramenta de Auditoria preservada atrás da flag `dev_auditoria` para validação futura de indicadores. Documentação oficial versionada no repositório (docs 00–10), com decisões numeradas e supersedências rastreáveis.

### Design System

Baseline v0.6 congelada: semântica de cor permanente (verde = desempenho positivo; vermelho = queda/alerta; âmbar = em aberto; verde-marca AdTarget = identidade/navegação, nunca desempenho), tipografia consolidada com números tabulares, grid de 8pt, superfícies com bordas hairline e sombra apenas no hover, chrome do Streamlit oculto. Fidelidade validada contra o mockup de alta fidelidade aprovado, com screenshots em cada sprint.

### Performance

Base atual (~1,5 mil linhas) processada em milissegundos; o único gargalo é a API do Google, coberto pelo cache compartilhado de 15 minutos com atualização manual no masthead. Interações de filtro rodam em fragmento isolado — a página não recalcula durante a seleção, apenas no Aplicar.

### Confiabilidade

158 testes automatizados (dados, regras, formatação, componentes), smoke test de ponta a ponta das páginas com prova de invariância numérica a cada mudança visual, property tests de consistência card × gráfico (milhares de comparações, zero falha), alertas de qualidade permanentes (NF ausente, veículo em dois grupos, status desconhecido, cancelado com valor) e conciliação da base real fechada em R$ 0,00 pela ferramenta de Auditoria. Erros de configuração geram mensagens amigáveis, nunca stack trace.

### Testes executados

Suíte completa (158/158), Ruff sem apontamentos, smoke das páginas em produção e com flag de desenvolvimento, verificação de indicadores idênticos pré/pós release, filtros validados (estado aplicado filtra; rascunho não vaza) e captura visual de regressão.

### Riscos conhecidos

Dependência única da planilha Google (acesso revogado ou aba renomeada param o produto — mitigado por validação com erro claro); URL pública do Streamlit Cloud protegida apenas por senha única (decisão aceita; revisitar quando o produto circular além da diretoria); CSS ancorado em `data-testid` do Streamlit (upgrades de versão podem pedir ajuste visual — congelar a versão no requirements é recomendado); busca dos filtros aplica no Enter (limitação do widget nativo); modelagem do conceito de PI adiada por decisão de produto (impacta card Campanhas e denominador do Ticket Médio quando for tratada).

### Próximos passos recomendados

Fase 1.2 do roadmap original: módulos Campanhas, Metas e Executivos. Inteligência comercial: prazo médio de faturamento (campos DATA FATURAMENTO/DIAS EM ABERTO da aba 2026), segmentação Governo × Privado, alertas proativos de queda e concentração. IA: resumo executivo narrado por período e perguntas em linguagem natural sobre a carteira. Plataforma: banco de dados gerenciado substituindo a leitura direta da planilha (pré-requisito para multiusuário e SaaS), autenticação por perfil e trilha de auditoria de acesso.
