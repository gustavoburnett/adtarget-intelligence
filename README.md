# AdTarget Intelligence

Aplicação interna de inteligência comercial da AdTarget. Substitui o dashboard Power BI, lendo a "Planilha de Vendas AdTarget" (Google Sheets) diretamente e recalculando todas as métricas a partir das linhas brutas.

**Status: v0.4 — em produção no Streamlit Community Cloud.** MVP completo (camada de dados + interface), conciliado com a planilha real via ferramenta de auditoria. Regras vigentes: indicadores Vendas/Faturado/Em Aberto (v0.3) e critério temporal oficial MÊS (VEICULAÇÃO) com YTD verdadeiro (v0.4). A aba "🔧 Auditoria de Vendas 2026" é temporária e deve ser removida ao fim da conciliação.

## Arquitetura

Stack: Python + Streamlit + pandas + gspread + google-auth + plotly. Sem banco de dados na Fase 1.

O fluxo de dados segue quatro camadas com responsabilidades estritamente separadas:

```
Google Sheets ──> loader.py ──> cleaning.py ──> quality_checks.py
                  (leitura       (normalização    (alertas: detectam,
                   bruta)         genérica)        nunca corrigem)
                                      │
                                      └──> metrics.py (KPIs e comparativos)
```

1. **`src/data/loader.py`** — autentica via Service Account, descobre automaticamente as abas cujo nome é um ano de 4 dígitos (2024, 2025, 2026, futuras), lê com `UNFORMATTED_VALUE` (número puro, nunca "R$" formatado), valida as colunas esperadas com erro amigável (`ErroDeCarga`) e concatena tudo num DataFrame com a coluna `ANO_ABA`.

2. **`src/data/cleaning.py`** — normalização genérica apenas: trim e caixa alta em campos de texto, unificação de status duplicados por formatação, conversão de "MÊS/ANO" em data (dia 1 do mês), PI sempre como texto, VENCIMENTO PI desdobrado em data + flag de "contra apresentação", valores monetários como float. Nenhuma correção de cadastro específico é feita aqui (decisão 17).

3. **`src/data/quality_checks.py`** — os 4 alertas vigentes (o antigo alerta 2, "linhas sem status", foi removido quando o campo STATUS passou a ser obrigatório; os códigos 1/3/4/5 foram preservados para rastreabilidade). Cada função retorna um `AlertaQualidade` (código, título, contagem, detalhes e linhas afetadas) e nunca altera o dado.

4. **`src/data/metrics.py`** — indicadores comerciais recalculados das linhas brutas tratadas, conforme a regra vigente (2026-07-09): **Vendas** (A VEICULAR + EM VEICULAÇÃO + CHECKING + AGUARD. DOC. VEÍCULO + FATURADO + DIRETO), **Faturado** (FATURADO + DIRETO) e **Em Aberto** (= Vendas − Faturado). CANCELADO e BONIFICADO ficam fora de qualquer soma (apenas contagem de PIs). As métricas derivadas — Ticket Médio, Quantidade de Campanhas (Cliente + Campanha distintos), evolução mensal com lacunas, comparativo mês a mês, YTD em intervalo comparável, rankings e agregação sempre por Grupo + Veículo — usam a base Vendas. Todas as funções aceitam os dois toggles oficiais: `valor` ("liquido" padrão / "bruto") e `criterio_mes` — cujo padrão é a **regra oficial v0.4: MÊS (VEICULAÇÃO)**, centralizada na constante `CRITERIO_MES_OFICIAL` de `metrics.py` (fonte única de verdade; o toggle da interface inicializa a partir dela, e MÊS (GANHO) segue disponível como análise alternativa). Os comparativos recalculam sobre o toggle ativo. O vocabulário de STATUS tem 8 valores oficiais e o campo é obrigatório na planilha (não existe mais a categoria SEM_STATUS; um branco é sinalizado pelo alerta de status desconhecido).

Os módulos de dados não dependem de Streamlit, o que os mantém 100% testáveis. O cache (`st.cache_data(ttl=900)`) será aplicado sobre `loader.load_all_sheets` na integração do `app.py`.

## Estrutura do projeto

```
adtarget-intelligence/
├── app.py                          # gate de senha + cache + 3 abas
├── requirements.txt
├── .gitignore
├── .streamlit/
│   ├── config.toml                 # tema visual
│   └── secrets.toml.example       # modelo (o real NUNCA é versionado)
├── src/
│   ├── data/
│   │   ├── loader.py               # leitura bruta do Google Sheets
│   │   ├── cleaning.py             # normalização genérica
│   │   ├── quality_checks.py       # 4 alertas de qualidade
│   │   └── metrics.py              # KPIs, toggles e comparativos
│   ├── auth/gate.py                # senha única via st.secrets
│   └── components/                 # cards, charts, filters
├── pages_content/                  # 3 páginas do MVP
└── tests/
    ├── test_loader.py              # loader com mocks de gspread, sem rede
    ├── test_cleaning.py
    └── test_metrics.py
```

## Como executar localmente

Pré-requisito: Python 3.11+ (a suíte também roda em 3.10).

```bash
git clone <repositorio>
cd adtarget-intelligence
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Configuração de acesso (necessária apenas para ler a planilha real):

1. Criar projeto no Google Cloud Console e ativar a Google Sheets API
2. Criar uma Service Account e gerar chave JSON
3. Compartilhar a planilha com o e-mail da Service Account (permissão Leitor)
4. Copiar `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` e preencher `app_password`, `spreadsheet_id` e o bloco `[gcp_service_account]`

Rodar a aplicação: `streamlit run app.py` e abrir `localhost:8501`.

## Como rodar os testes

```bash
python -m pytest tests/ -v
```

Os testes não dependem de rede nem de credenciais: o loader é testado com mocks do contrato do gspread, e as métricas usam uma base sintética que reproduz os casos extremos reais da planilha (status com espaço no fim, cancelado com valor não zerado, veículo homônimo em grupos diferentes, campanha homônima em clientes diferentes, PI de tipo misto, vencimento "CONTRA APRESENT.").

## Critérios de aceite com dado real

Ao conectar na planilha real, o indicador **Faturado** (líquido) deve bater com as magnitudes de referência do documento 01: R$ 16.498.970 (2024), R$ 19.996.930 (2025), R$ 4.714.419 (2026 parcial — valor da análise original; a planilha segue recebendo lançamentos). O indicador Vendas será maior, pois inclui os status em aberto.

## Documentação oficial

Este código implementa os documentos 00 a 06 do projeto (versão 0.2), com uma atualização de regra comercial definida pelo responsável em 2026-07-09 (indicadores Vendas/Faturado/Em Aberto, vocabulário de 8 status, campo STATUS obrigatório), pendente de registro formal como versão 0.3 da documentação. Em caso de dúvida, a regra de 2026-07-09 prevalece sobre o documento 02.
