# Parecer de prontidão para homologação

Data: 02/11/2026. Branch local `feat/google-workspace-login`.
Base preservada: `2b95cc933fb45defd8ade25e75bc886077fb9e73` (main, PR #13).

## Escopo entregue

Login Google OIDC nativo, autorização por Workspace (`hd`), identidade e expiração verificadas antes da carga comercial, acesso igual às cinco páginas, logout e limpeza do estado da sessão. Marca, fonte local e tokens existentes reutilizados. Dependência Streamlit mantida em 1.59.1, com extra oficial auth e lock de CI regenerado.

Alterações nos testes antigos substituem a injeção do flag de senha por identidade nativa sintética. A preservação histórica do gate de senha foi substituída por verificações do contrato Google explicitamente solicitado; as verificações financeiras históricas permanecem. O fixture de cache passou a reter a referência original para limpar o cache mesmo quando o teste substitui `st.cache_data` por um observador. Nenhum teste financeiro foi removido.

## Evidências

- Main isolada: 1.583 testes Python passaram, Python 3.12.12 / Streamlit 1.59.1 / pandas 3.0.3, com rede bloqueada pelo plugin `ci.offline`.
- Nova branch: 1.604 testes Python passaram na suíte integral offline, inclusive no ambiente criado com o lock OAuth atualizado (60 pacotes; 120,56 segundos).
- Testes direcionados de login, acesso direto, navegação, metas e preservação: 155 passaram.
- Regressão de Performance Comercial: 29 passaram.
- JavaScript Carteira: 19 casos de links e 7 casos de caracteres especiais passaram, Node 24.20.0 local. CI continua com seu Node 22.14.0 original.
- Consistência das dependências: `uv pip check` aprovou os 60 pacotes do ambiente OAuth atualizado.
- Comparação Git: nenhum byte alterado em `src/data/`, `pages_content/`, `src/components/carteira_b.html` ou `src/components/design_tokens.py`.
- `git diff --check` sem erros. Nenhum arquivo local de Secrets criado ou versionado.

A verificação financeira usa a mesma suíte e fixtures sintéticas da main. Não houve leitura nem alteração da planilha oficial. Portanto, a evidência comprova preservação de regras e resultados de regressão, não uma reconciliação dos números atuais da produção.

## Validação real ainda necessária

Não foram configurados cliente OAuth, credenciais, redirects ou app de homologação. Não houve login de conta corporativa ou pessoal real, nem teste real de cookie, expiração, logout no navegador ou revisão visual em Mac/iPhone. Os testes de autorização, recarga, sessão expirada e logout desta entrega simulam a identidade fornecida pelo Streamlit, sem simular sucesso de uma validação criptográfica real do Google.

O roteiro completo e as configurações exatas, incluindo os valores que dependem da URL futura de homologação, estão em `GOOGLE_WORKSPACE_LOGIN.md` e `.streamlit/secrets.toml.example`.

## Parecer

Implementação local apta a seguir para configuração e homologação OAuth em ambiente separado. Não aprovada para produção até comprovar o fluxo real com os cenários documentados, inclusive conta corporativa autorizada, pessoal negada, anônimo, recarga, logout, expiração e acesso direto. Logout entre abas e revogação de tokens já emitidos obedecem aos limites nativos descritos no guia.

Produção, senha atual, planilha oficial, regras financeiras e Design B preservados. Nenhum push, PR, merge ou deploy realizado.

## Reprodução

```sh
python -m pip install --require-hashes -r requirements-ci.txt
python -m pip check
python -m pytest -p ci.offline -q
node --input-type=module -e "import {result} from './tests/carteira_deep_link.mjs'; import {specialNamesResult} from './tests/carteira_frontend.mjs'; console.log({links:result,specialNames:specialNamesResult});"
git diff --check
```

Saídas integrais da suíte baseline e da suíte final em `evidence/google-workspace-tests.txt`. As alterações locais ainda não foram commitadas.
