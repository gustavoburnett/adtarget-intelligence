# Homologação isolada — 02/11/2026


A autorização atual permite commit/push desta branch e um aplicativo Streamlit
separado. Não permite merge nem implantação na aplicação de produção.
Os documentos anteriores registram a etapa local original.


## Aplicativo separado


- Repositório: `gustavoburnett/adtarget-intelligence`.
- Branch: `feat/google-workspace-login`.
- Entrada: **`app_homologacao.py`**, Python 3.12.
- Aplicativo criado: https://adtarget-intelligence-homologacao.streamlit.app/.
- Secrets: usar somente `.streamlit/secrets.homologacao.toml.example`, preenchido privadamente.
- Não copiar Secrets de produção. Não fornecer chave de conta de serviço.
- O entrypoint substitui exclusivamente as fontes por vendas geradas localmente,
  metas vazias e cadastro sintético. O cliente Sheets real é bloqueado.
- Gate nativo, renderização das cinco páginas e cálculos usam a implementação existente.
- Os testes de navegação sintética não reconciliam indicadores reais de produção.


## Evidência desta etapa


A suíte integral executada nesta etapa aprovou **1.611 testes Python** (144,80 s).
Após os ajustes das datas e links sintéticos, **nove testes direcionados** passaram.
As evidências anteriores de 26 casos JavaScript permanecem históricas; Node não
estava disponível no PATH desta sessão para repeti-los.


Google Cloud corporativo acessível após reautenticação. Projeto
`adtarget-intelligence`; plataforma OAuth criada com nome “AdTarget Intelligence —
Homologação”, público Interno e contato corporativo. Cliente Web exclusivo criado
com callback exato `https://adtarget-intelligence-homologacao.streamlit.app/oauth2callback`.
Fluxo real observado solicitando somente `openid email profile`.
Secrets exclusivos armazenados diretamente no Streamlit, sem chave de conta de
serviço ou ID real de planilha. Nenhum segredo está neste documento ou no Git.


Streamlit Cloud: app separado criado, Python 3.12 (runtime 3.12.16), Streamlit 1.59.1.
O app existente na main com `app.py`, seus Secrets e a planilha oficial não foram alterados.
Branch publicada; PR Draft tentado pelo conector GitHub, negado com 403
`Resource not accessible by integration`. PR não é necessário para executar este app.


| Caso real | Evidência observada |
| --- | --- |
| Corporativa | Login Google de funcionário @adtarget.com.br concluiu callback e liberou o app |
| Cinco páginas | Todas selecionadas e renderizadas na sessão corporativa com fonte sintética |
| Recarga autenticada | Manteve acesso e renderizou novamente |
| Logout | Retornou à tela de login |
| Recarga após logout | Permaneceu na tela de login |
| Gmail pessoal | Google bloqueou com **403 org_internal**, antes do callback autorizado |
| Anônimo | Navegador independente exibiu somente login |
| Link direto anônimo | `?carteira=1` exibiu somente login, sem navegação comercial |
| Outro Workspace | Pendente: a tentativa feita pelo usuário mostrou novamente o mesmo Gmail; não há evidência de outro domínio |
| Expiração real | Pendente: não foi aguardado o vencimento natural do token; coberto apenas por testes sintéticos |
| iPhone | Pendente de teste real no dispositivo |


A primeira renderização usava datas sintéticas em formato não aceito pelo normalizador,
resultando em valores zerados. O entrypoint foi corrigido para o formato da fonte;
teste adicional confirma 48 datas válidas e soma positiva. Também foi isolado o
> O registro de 02/11 abaixo descreve a etapa sintética inicial. O estado vigente da homologação está nesta atualização.

## Atualização de 16/11/2026 — dados comerciais em leitura real

A configuração atual usa a planilha comercial, com acesso somente leitura.

- O Secret homologation_data_mode está definido como real_readonly.
- O Secret spreadsheet_id aponta para a Planilha de Vendas AdTarget. O ID fica somente nos Secrets do app.
- A conta de serviço adtarget-intelligence-homologacao-reader (adtarget-homologacao-reader@adtarget-intelligence.iam.gserviceaccount.com) tem permissão Leitor na planilha comercial.
- O acesso dessa conta à planilha financeira foi removido. A verificação de compartilhamentos retornou somente a planilha comercial.
- Nenhum papel IAM de projeto foi concedido durante esta configuração.
- O código mantém synthetic como padrão. A fonte real é ativada explicitamente; o loader limita a leitura às abas 2024, 2025 e 2026 e usa o escopo spreadsheets.readonly.
- A chave da conta de serviço e as credenciais OAuth ficam somente nos Secrets do Streamlit. Nenhuma credencial ou ID de planilha foi incluído no repositório ou neste documento.

Durante a configuração, o primeiro ID informado apontava para a planilha financeira. O compartilhamento foi removido e o Secret foi corrigido para a planilha comercial antes da validação final.

Após salvar os Secrets e reiniciar somente a homologação, o app abriu o Radar Executivo com as cinco páginas. A tela deixou de exibir os valores sintéticos do aceite inicial e não mostrou erro de permissão ou leitura. A reconciliação detalhada de cada indicador com a planilha continua pendente.
