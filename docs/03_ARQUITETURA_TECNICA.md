# 03. Arquitetura Técnica — AdTarget Intelligence

*(Cópia sem alteração de conteúdo da versão 0.2 — mantida no repositório para o conjunto documental completo. Alterações da v0.3 estão nos documentos 00, 01, 02, 04 e 06.)*

## Stack

Python + Streamlit. Sem banco de dados na Fase 1. Fonte de dados: Google Sheets, lido diretamente pela aplicação a cada ciclo de cache.

## Bibliotecas necessárias

| Biblioteca | Função |
|---|---|
| `streamlit` | Framework da aplicação |
| `pandas` | Tratamento e agregação dos dados |
| `gspread` | Leitura do Google Sheets |
| `google-auth` | Autenticação da Service Account |
| `plotly` | Gráficos, com suporte a clique para drill-down (grupo → veículo) |

Escolha deliberadamente mínima, evitando dependências desnecessárias. Não entram bibliotecas de leitura de xlsx local, ORM, ou gerenciamento de variável de ambiente externo (o `secrets.toml` nativo do Streamlit já resolve isso).

## Estrutura de pastas e arquivos

```
adtarget-intelligence/
├── app.py                          # entrada única: gate de senha + carrega dados + monta as 3 páginas
├── requirements.txt
├── .gitignore
├── .streamlit/
│   ├── config.toml                 # tema visual
│   └── secrets.toml                # NÃO versionado: senha do app + credenciais da Service Account
├── src/
│   ├── data/
│   │   ├── loader.py               # conexão e leitura bruta do Google Sheets
│   │   ├── cleaning.py             # normalização genérica: trim, case, status, tipos de dado
│   │   ├── quality_checks.py       # alertas de qualidade (não corrigem, apenas detectam)
│   │   └── metrics.py              # indicadores, comparativos e agregações
│   ├── auth/
│   │   └── gate.py                 # tela de senha única
│   └── components/
│       ├── cards.py                # KPI cards reutilizáveis
│       ├── charts.py               # gráficos reutilizáveis
│       └── filters.py              # filtros reutilizáveis
├── pages_content/
│   ├── performance_comercial.py
│   ├── analitico_comercial.py
│   └── analitico_veiculos.py
└── tests/
    ├── test_loader.py
    ├── test_cleaning.py
    └── test_metrics.py
```

### Decisões de organização

- **`st.tabs()` num único `app.py`, em vez do sistema nativo de multipágina do Streamlit.** Com 3 páginas fixas, essa abordagem centraliza a autenticação num único lugar (evitando repetir a checagem de senha em cada arquivo) e evita reprocessar os dados a cada troca de página. Quando a Fase 1.2 trouxer as páginas Campanhas, Metas e Executivos (6 páginas no total), a navegação deve migrar para o sistema nativo em sidebar, mais adequado para esse volume de páginas.
- **`cleaning.py` e `quality_checks.py` são módulos separados de propósito.** Limpeza transforma dado (remove espaço, padroniza texto). Verificação de qualidade observa e avisa, sem alterar nada. Separar evita que correções pontuais de cadastro acabem hardcoded dentro do módulo de normalização genérica.

## Leitura do Google Sheets

- `loader.py` autentica via Service Account, usando as credenciais armazenadas em `st.secrets["gcp_service_account"]` (formato TOML, nunca um arquivo JSON solto no repositório)
- A planilha é aberta pelo **ID do arquivo**, nunca pela URL de compartilhamento
- **Descoberta automática de abas**: o loader identifica automaticamente todas as abas cujo nome seja um ano de 4 dígitos e lê todas elas, sem fixar os anos no código. Isso evita que a aplicação precise ser alterada manualmente quando uma nova aba de ano for criada na planilha (ex: 2027)
- **Detecção automática do cabeçalho**: a primeira linha da aba pode estar vazia (caso real); o loader localiza a primeira linha que contém todas as colunas obrigatórias
- Leitura feita com `value_render_option=UNFORMATTED_VALUE`, garantindo que valores numéricos venham como número puro, não como texto formatado (ex: "R$ 99.879,98")
- O resultado de cada aba é um DataFrame, concatenados ao final com uma coluna `ANO_ABA` indicando a origem

### Como liberar o acesso (passo a passo operacional)

1. Criar/usar um projeto no Google Cloud Console e ativar a Google Sheets API
2. Criar uma Service Account dentro do projeto
3. Gerar uma chave JSON para essa Service Account
4. Copiar o e-mail da Service Account (formato `nome@projeto.iam.gserviceaccount.com`)
5. Na planilha real, usar "Compartilhar" e dar permissão de **Leitor** a esse e-mail
6. As credenciais (conteúdo do JSON) são inseridas no `secrets.toml`, nunca coladas em texto puro no código ou em mensagens

## Limpeza e normalização

Detalhada no documento 02 (Regras de Negócio e Métricas). Tecnicamente implementada em `src/data/cleaning.py`, executada sempre depois da leitura e antes de qualquer cálculo de métrica.

## Verificações de qualidade

Implementadas em `src/data/quality_checks.py`, executadas depois da limpeza. Alimentam o bloco de Alertas de Qualidade da página Analítico Comercial. Nunca alteram o dado, apenas retornam uma lista de ocorrências.

## Autenticação por senha única

- Senha armazenada em `st.secrets["app_password"]`, fora do código e fora do controle de versão
- Estado de sessão `autenticado` inicia como `False`
- Tela de login simples: campo de senha + botão. Senha correta libera a aplicação (`autenticado = True`); senha incorreta mostra erro e não avança
- O gate roda no topo do `app.py`, antes de qualquer leitura de dado ou renderização de página. Se não autenticado, a execução para ali (`st.stop()`)
- Sem perfil de usuário, sem botão de logout no MVP (sessão dura enquanto a aba do navegador estiver aberta)

## Cache

- `st.cache_data(ttl=900)` (15 minutos) na função de leitura do Google Sheets
- Cache compartilhado entre todos os usuários simultâneos do app, não é por sessão individual
- Botão "Atualizar dados agora" na interface, para limpar o cache manualmente quando necessário
- Limpeza e cálculo de métricas não têm cache próprio: com o volume atual de dados (pouco mais de 1.400 linhas), o processamento em pandas é da ordem de milissegundos. Cache só é necessário no ponto em que a rede é o gargalo (a chamada à API do Google)

## Deploy

- **Recomendação para o MVP: Streamlit Community Cloud.** Gratuito, deploy direto a partir de um repositório GitHub (pode ser privado), HTTPS automático
- Passo a passo: repositório no GitHub → conectar em share.streamlit.io → apontar para `app.py` → configurar senha do app e credenciais da Service Account diretamente na interface de secrets do Streamlit Cloud, nunca commitados no repositório
- **Ressalva registrada**: por padrão, a URL do Streamlit Community Cloud é pública na internet, protegida apenas pela senha do app, não por controle de acesso do Google. Essa é uma decisão de negócio já aceita para o MVP
- **Alternativa futura**: se a senha única circular além do time ou for necessário mais controle de acesso, migrar para um VPS pequeno com HTTPS próprio. Isso muda a responsabilidade de manutenção (atualização de sistema, reinício de serviço) para o lado da AdTarget ou via acordo de manutenção continuada

## Riscos e cuidados técnicos

| Risco | Mitigação |
|---|---|
| Leitura da API devolver texto formatado em vez de número puro, quebrando cálculos silenciosamente | Uso de `UNFORMATTED_VALUE` na leitura |
| Limite de requisições da API do Google Sheets | Cache de 15 minutos, compartilhado entre usuários |
| Coluna renomeada ou reordenada na planilha de origem sem aviso | Validação das colunas esperadas na leitura, com erro claro na tela em vez de seguir com dado errado |
| Recorrência de inconsistência de cadastro (veículo associado a mais de um grupo) | Alerta genérico e permanente em `quality_checks.py`, sem correção automática |
| Senha única compartilhada vazar | Risco aceito e registrado como decisão de negócio; qualquer pessoa com o link e a senha acessa o painel |
| Ausência de log de quem editou o quê na planilha de origem | Limitação aceita por não haver banco de dados na Fase 1; alterações na fonte refletem no dashboard em até 15 minutos, sem rastreabilidade de autor |
| Planilha movida, renomeada, ou acesso da Service Account revogado | A aplicação para de funcionar; necessário ter uma pessoa responsável por essa dependência |
| Secrets ausentes ou malformados no ambiente de deploy (senha ou credenciais da Service Account não configuradas corretamente) | A aplicação deve exibir uma mensagem de erro amigável e específica ao iniciar (ex: "Credenciais do Google não configuradas"), nunca um stack trace bruto para o usuário final |
