# 11. Milestone — Fase 2 · Plataforma Comercial Inteligente

## Status

Aberta em 2026-07-13, imediatamente após o congelamento da Release 1.0 (tag `v1.0.0`, baseline oficial do produto). Nenhum item desta fase altera a interface da Release 1.0 — o ciclo de Design System está encerrado (decisão 38).

## Princípio da fase

Evoluir o AdTarget Intelligence de dashboard executivo para plataforma de inteligência comercial: novos módulos, leitura proativa do negócio e fundações de arquitetura que destravam o caminho SaaS.

## Trilhas candidatas (a priorizar com o Product Owner)

**Novos módulos (Fase 1.2 do roadmap original)**
- Página Campanhas (ciclo de vida, concentração por cliente)
- Página Metas (definição e acompanhamento por executivo/grupo)
- Página Executivos (carteira, desempenho, YoY individual)

**Inteligência comercial**
- Prazo médio de faturamento (campos DATA FATURAMENTO / DIAS EM ABERTO, disponíveis desde a aba 2026)
- Segmentação Governo × Privado como dimensão de análise
- Alertas proativos: queda de ritmo, concentração excessiva, pipeline parado
- Mapeamento semântico de cores por status no gráfico de carteira (pendência C5)
- Modelagem oficial do conceito de PI (contagem, impacto no Ticket Médio e no card Campanhas — pendência registrada na Release 1.0)

**IA**
- Resumo executivo narrado por período (fatos, sem interpretação especulativa)
- Perguntas em linguagem natural sobre a carteira ("quanto a Disney vendeu no semestre?")

**Arquitetura de plataforma / escalabilidade**
- Banco de dados gerenciado substituindo a leitura direta da planilha (pré-requisito para multiusuário, histórico e SaaS)
- Autenticação por perfil de usuário e trilha de acesso
- Pipeline de ingestão com versionamento de snapshots da base

## Regras da fase

- A baseline visual `v1.0.0` só muda por decisão explícita de Produto.
- Toda regra de negócio nova nasce documentada (decisão numerada na Memória Oficial) antes do código.
- Disciplina mantida: testes para todo cálculo, smoke com invariância numérica, conflitos de especificação interrompem a implementação.
