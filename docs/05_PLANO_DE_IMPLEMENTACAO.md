# 05. Plano de Implementação — AdTarget Intelligence

*(Cópia da versão 0.2 com uma única nota da v0.3 nos critérios de aceite: as magnitudes de referência validam o indicador **Faturado** — antigo "Faturamento Realizado". Alterações de regra estão nos documentos 00, 02 e 06.)*

## Ordem de desenvolvimento

O desenvolvimento segue a dependência real entre módulos: primeiro a base de dados, depois a camada visual, nunca o contrário.

1. **Módulo de dados** (`src/data/`)
   1.1. `loader.py`: conexão com a Service Account e leitura bruta das abas por ano
   1.2. `cleaning.py`: normalização genérica (trim, case, status, tipos de dado)
   1.3. `quality_checks.py`: alertas de qualidade (Nota Fiscal ausente, veículo com grupo inconsistente, status não reconhecido)
   1.4. `metrics.py`: indicadores comerciais, Ticket Médio, YTD, comparativo mês a mês
2. **Testes do módulo de dados** (`tests/`), garantindo que os cálculos batem com os números já validados manualmente durante a análise
3. **Autenticação** (`src/auth/gate.py`)
4. **Componentes reutilizáveis** (`src/components/`: cards, gráficos, filtros)
5. **Página Performance Comercial**
6. **Página Analítico Comercial**
7. **Página Analítico Veículos**
8. **Integração final em `app.py`** (gate → carga de dados → montagem das 3 abas)
9. **Deploy em Streamlit Community Cloud**

## Critérios de aceite do MVP

O MVP é considerado validado quando:

- O indicador **Faturado** calculado pela aplicação bate com os números de referência do documento 01 (aproximadamente R$ 16,50 milhões líquidos em 2024, R$ 20,00 milhões em 2025, e R$ 4,71 milhões em 2026 parcial na época da análise, todos em FATURADO + DIRETO) *(nota v0.3: o card principal exibe Vendas, que inclui também os status em aberto e será sempre ≥ Faturado)*
- As 3 páginas carregam corretamente com dado real da planilha
- Os toggles de Valor Líquido/Bruto e MÊS (GANHO)/MÊS (VEICULAÇÃO) funcionam em todos os blocos aplicáveis
- O KPI de YTD reflete corretamente o intervalo comparável entre os dois anos (nunca ano parcial contra ano completo)
- O bloco de Alertas de Qualidade exibe corretamente as ocorrências reais da base (Nota Fiscal ausente, veículo com grupo inconsistente, status não reconhecido, e cancelado/bonificado com valor diferente de zero, se houver)
- O bloco de Cancelado/Bonificado exibe contagem de PIs, não soma monetária (ver documento 02)
- A tela de senha bloqueia o acesso sem autenticação
- O botão de atualização manual de dados funciona
- A aplicação está publicada e acessível pelo link do Streamlit Community Cloud

## Checklist para rodar localmente

1. Python 3.11 ou mais recente instalado
2. Clonar o repositório
3. Criar e ativar um ambiente virtual
4. Instalar dependências: `pip install -r requirements.txt`
5. Criar a Service Account no Google Cloud, ativar a Google Sheets API, gerar a chave de acesso
6. Compartilhar a planilha real com o e-mail da Service Account, permissão de Leitor
7. Criar `.streamlit/secrets.toml` local (nunca versionado) com a senha do app e as credenciais da Service Account
8. Rodar `streamlit run app.py`
9. Abrir `localhost:8501`, informar a senha, confirmar que as 3 páginas carregam com dado real
10. Conferir se o indicador Faturado exibido bate com os números de referência do documento 01 (critério de aceite acima)

## Checklist para deploy em produção

1. Repositório publicado no GitHub (pode ser privado)
2. Conta criada em share.streamlit.io, conectada ao repositório
3. Apontar o deploy para `app.py`
4. Configurar, na interface de secrets do Streamlit Cloud (nunca no repositório): senha do app e credenciais completas da Service Account
5. Validar o link de produção com os mesmos critérios de aceite do ambiente local
6. Compartilhar o link e a senha apenas com quem de fato deve acessar o painel

## Riscos e cuidados a monitorar durante a implementação

Detalhados no documento 03 (Arquitetura Técnica). Resumo dos pontos que exigem atenção redobrada durante o desenvolvimento:

- Garantir leitura de valor numérico puro da API (`UNFORMATTED_VALUE`), não texto formatado
- Validar a existência das colunas esperadas antes de processar qualquer dado, com erro visível em caso de divergência
- Não reintroduzir, em nenhum módulo, correções hardcoded para casos específicos de cadastro (isso é papel do alerta genérico de qualidade, não do código de normalização)

## Próximos passos após a validação do MVP

Registrados aqui apenas como direção futura, fora do escopo de implementação atual:

- Fase 1.2: páginas Campanhas, Metas e Executivos, com migração da navegação de `st.tabs()` para o sistema nativo de multipágina do Streamlit
- Avaliação de métrica de prazo médio de faturamento, usando os campos DATA FATURAMENTO e DIAS EM ABERTO, disponíveis apenas a partir da aba 2026
- Avaliação de segmentação Governo x Privado como dimensão adicional de análise
- Avaliação de migração de hospedagem para VPS próprio, caso o controle de acesso por senha única deixe de ser suficiente
