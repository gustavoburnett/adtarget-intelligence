# Login Google Workspace, implementação e homologação

Base: main `2b95cc933fb45defd8ade25e75bc886077fb9e73`.
Branch local: `feat/google-workspace-login`. Nenhum push, PR ou deploy autorizado nesta etapa.

## Como funciona

Streamlit 1.59.1 é preservado, com o extra oficial `[auth]` (Authlib). O servidor realiza OIDC com discovery Google, assinatura/JWKS, issuer, audience, state e nonce pelo fluxo nativo. Não há parser JWT próprio, identidade por query string nem autenticação por session_state. As credenciais OAuth e o cookie secret ficam exclusivamente em Secrets.

A cada execução, antes dos loaders e caches comerciais, o gate exige identidade nativa autenticada, `iss` Google, `aud` igual ao cliente configurado, `sub` presente, `email_verified` booleano verdadeiro, `hd` exatamente `adtarget.com.br` e `exp` numérico ainda válido. O domínio do texto do email não concede acesso. O parâmetro `hd` da solicitação é apenas uma conveniência de interface; a autorização usa o claim validado. As cinco páginas recebem o mesmo acesso, sem perfis ou administração. Auditoria continua condicionada ao flag de desenvolvimento já existente.

O login reutiliza SVG oficial, fonte local e tokens existentes. Design B, regras financeiras, loaders e planilha não são alterados. `app_password` e o antigo flag `autenticado` não concedem acesso nesta branch.

## Google Cloud, sem mexer na produção

1. Um administrador da AdTarget deve criar ou selecionar um projeto pertencente à organização Google Workspace `adtarget.com.br`. Não usar projeto pessoal externo para uma aplicação Internal.
2. Google Auth Platform: Branding com nome “AdTarget Intelligence”, email de suporte e contato técnico válidos. Configurar Audience como **Internal**. Se Internal não estiver disponível, corrigir a vinculação à organização antes de homologar.
3. Data Access: apenas `openid`, `email` e `profile`. Não solicitar Drive, Sheets, refresh tokens ou delegação de domínio para login. A conta de serviço dos dados permanece independente.
4. Clients: criar cliente OAuth do tipo **Web application**, exclusivo para homologação. Adicionar Authorized redirect URI exatamente `http://localhost:8501/oauth2callback` para o teste local. Para homologação Community Cloud, usar `https://<SUBDOMINIO_EXATO_DE_HOMOLOGACAO>.streamlit.app/oauth2callback`. O subdomínio real ainda não foi definido. Não copiar placeholder para o Console.
5. Se a interface solicitar Authorized JavaScript origins, usar `http://localhost:8501` e/ou a origem HTTPS exata de homologação, sem caminho. O fluxo é servidor a servidor, sem SDK JS.
6. Copiar Client ID e Client secret diretamente para Secrets do ambiente de homologação. Nunca para código, issue, chat, screenshots ou arquivos versionados. Gerar cookie_secret aleatório de pelo menos 32 bytes, por exemplo `python -c 'import secrets; print(secrets.token_urlsafe(48))'`, executado privadamente pelo responsável. Usar segredo diferente entre ambientes.
7. Se Workspace App Access Control restringir aplicativos OAuth, o administrador deve autorizar especificamente esse Client ID para os funcionários. Não alterar políticas globais.

## Secrets e execução local

O modelo completo está em `.streamlit/secrets.toml.example`; contém somente placeholders. Copiar para `.streamlit/secrets.toml`, ignorado pelo Git, e substituir os valores. A seção `[auth.google]` deve usar `server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"`. A seção `[auth]` contém `redirect_uri` e `cookie_secret`. `client_kwargs` pede `openid email profile`, `select_account` e a sugestão de domínio corporativo.

Instalar com Python 3.12: `python -m pip install -r requirements.txt`. Para ambiente reproduzível de teste: `python -m pip install --require-hashes -r requirements-ci.txt`. Executar `streamlit run app.py --server.port 8501`. Não copiar automaticamente Secrets de produção. Para a homologação inicial, preferir uma fonte sintética separada com o mesmo esquema. O login não precisa de acesso OAuth a planilhas.

## Streamlit Community Cloud, etapa futura

Não alterar Settings nem Secrets do app atual. Após autorização específica para publicar, disponibilizar esta branch em um app de homologação separado, com entrada `app.py` e Python 3.12. Registrar sua URL exata no cliente OAuth de homologação. Em App settings → Secrets, colar o TOML preenchido com o redirect HTTPS exato, client_id, client_secret e cookie_secret. Manter os Secrets de dados separados e somente leitura. Não habilitar `dev_auditoria` na produção.

A publicação da branch, criação desse app e configuração externa não foram feitas nesta entrega. Apenas após os testes abaixo, uma nova autorização pode permitir migração da produção. Até lá, o app atual e sua senha continuam intactos. Na migração futura, manter a revisão anterior e seus Secrets disponíveis para rollback controlado. Não incluir fallback de senha nesta nova implementação.

## Sessão e limites nativos

`Sair` limpa session_state, aciona `st.logout()` e interrompe a execução. Streamlit remove o cookie de identidade e cria nova sessão. Logout do app não encerra a conta Google no navegador; `select_account` permite escolher outra conta.

O cookie de identidade nativo pode persistir por até 30 dias segundo a documentação, mas isso não estende a autorização do token: o gate exige `exp` válido em todo rerun, navegação e recarga. Token vencido bloqueia a execução e apresenta “Sair e trocar de conta”. Não há renovação silenciosa implementada. Uma aba sem eventos pode continuar mostrando informação já renderizada; o próximo evento revalida antes de carregar dados. Não é possível apagar informação já vista.

Logout nativo não revoga imediatamente outras sessões já abertas em outras abas. Elas continuam sujeitas ao `exp` em cada execução. Suspensão de funcionário no Workspace também não revoga retroativamente um token já emitido; sua validade limita essa janela. Revogação central imediata e sincronização de logout entre abas não fazem parte desta versão e exigiriam mecanismo adicional. Não alegar que foram testadas ou garantidas.

## Roteiro de homologação real obrigatório

| Caso | Procedimento | Resultado esperado |
| --- | --- | --- |
| Corporativa | Entrar com funcionário do Workspace AdTarget | Cinco páginas acessíveis, mesmos indicadores da revisão anterior |
| Pessoal | Tentar conta Gmail, incluindo janela privada | Google Internal impede ou gate nega; nenhum dado comercial |
| Outro domínio | Tentar outro Workspace | Negado, mesmo com email semelhante |
| Anônima | Abrir URL e deep link em janela privada | Apenas login, sem carga de dados |
| Direto às páginas | Tentar cada uma das cinco páginas com sessão anônima e pessoal | Nenhum loader ou render comercial |
| Logout | Sair após aplicar filtros e recarregar | Login novamente; estado privado limpo |
| Recarga | Recarregar com identidade ainda válida | Acesso preservado pelo cookie nativo, revalidação do gate |
| Expirada | Esperar expirar o ID token e executar navegação/recarga | Bloqueio antes de ler dados; reentrada pelo Google |
| Troca de conta | Sair e selecionar pessoal/corporativa | Pessoal negada; corporativa liberada |
| Protocolo | Callback sem state, state adulterado, nonce inválido ou token para outro client | Rejeição pelo fluxo nativo; nenhum dado |
| Navegadores | Mac e iPhone, teclado e zoom | Marca legível, botão acessível, sem sobreposições |

Os testes locais usam identidades sintéticas em monkeypatch de teste e AppTest; não comprovam emissão real, assinatura do Google, consentimento, redirects ou comportamento dos cookies no navegador. Nenhuma conta real foi usada nesta etapa.

## Fontes primárias

- https://docs.streamlit.io/develop/concepts/connections/authentication
- https://docs.streamlit.io/develop/tutorials/authentication/google
- https://developers.google.com/identity/openid-connect/openid-connect
- https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
