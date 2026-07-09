# AdTarget Intelligence

Aplicação interna de inteligência comercial da AdTarget. Substitui o dashboard Power BI, lendo a "Planilha de Vendas AdTarget" (Google Sheets) diretamente e recalculando todas as métricas a partir das linhas brutas.

**Status: Fase 1 — camada de dados implementada e testada.** Interface (Streamlit), autenticação e páginas serão integradas nas próximas etapas, conforme o plano de implementação (documento 05).

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

2. **`src/data/cleaning.py`** — normalização genérica apenas: trim e caixa alta em campos de texto, unificação de status duplicados por formatação, `SEM_STATUS` para linhas sem status, conversão de "MÊS/ANO" em data (dia 1 do mês), PI sempre como texto, VENCIMENTO PI desdobrado em data + flag de "contra apresentação", valores monetários como float. Nenhuma correção de cadastro específico é feita aqui (decisão 17).

3. **`src/data/quality_checks.py`** — os 5 alertas oficiais do documento 02. Cada função retorna um `AlertaQualidade` (código, título, contagem, detalhes e linhas afetadas) e nunca altera o dado.

4. **`src/data/metrics.py`** — métricas oficiais recalculadas das linhas brutas tratadas: Faturamento Realizado (FATURADO + DIRETO, com etiqueta de DIRETO), Pipeline em Aberto, Ticket Médio, Quantidade de Campanhas (Cliente + Campanha distintos, só Realizado), Cancelado/Bonificado (contagem de PIs), evolução mensal com lacunas (nunca zero em mês sem dado), comparativo mês a mês, YTD em intervalo comparável e agregação sempre por Grupo + Veículo. Todas as funções aceitam os dois toggles oficiais: `valor` ("liquido" padrão / "bruto") e `criterio_mes` ("ganho" padrão / "veiculacao") — os comparativos recalculam sobre o toggle ativo.

Os módulos de dados não dependem de Streamlit, o que os mantém 100% testáveis. O cache (`st.cache_data(ttl=900)`) será aplicado sobre `loader.load_all_sheets` na integração do `app.py`.

## Estrutura do projeto

```
adtarget-intelligence/
├── app.py                          # entrada (stub — integração na etapa final)
├── requirements.txt
├── .gitignore
├── .streamlit/
│   ├── config.toml                 # tema visual
│   └── secrets.toml.example       # modelo (o real NUNCA é versionado)
├── src/
│   ├── data/
│   │   ├── loader.py               # leitura bruta do Google Sheets
│   │   ├── cleaning.py             # normalização genérica
│   │   ├── quality_checks.py       # 5 alertas de qualidade
│   │   └── metrics.py              # KPIs, toggles e comparativos
│   ├── auth/gate.py                # senha única (próxima etapa)
│   └── components/                 # cards, charts, filters (próxima etapa)
├── pages_content/                  # 3 páginas do MVP (próxima etapa)
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

Rodar a aplicação (após a integração da interface): `streamlit run app.py` e abrir `localhost:8501`.

## Como rodar os testes

```bash
python -m pytest tests/ -v
```

Os testes não dependem de rede nem de credenciais: o loader é testado com mocks do contrato do gspread, e as métricas usam uma base sintética que reproduz os casos extremos reais da planilha (status com espaço no fim, cancelado com valor não zerado, linha sem status com valor material, veículo homônimo em grupos diferentes, campanha homônima em clientes diferentes, PI de tipo misto, vencimento "CONTRA APRESENT.").

## Critérios de aceite com dado real

Ao conectar na planilha real, o Faturamento Realizado (líquido) deve bater com as magnitudes de referência do documento 01: R$ 16.498.970 (2024), R$ 19.996.930 (2025), R$ 4.714.419 (2026 parcial).

## Documentação oficial

Este código implementa estritamente os documentos 00 a 06 do projeto (Memória Oficial, Dicionário de Dados, Regras de Negócio e Métricas, Arquitetura Técnica, Wireframes, Plano de Implementação e Changelog, versão 0.2). Em caso de dúvida de implementação, o documento 02 é a referência.
