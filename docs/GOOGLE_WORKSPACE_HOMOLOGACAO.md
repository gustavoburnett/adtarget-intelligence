# Homologação isolada — 02/11/2026

A autorização atual permite commit/push desta branch e um aplicativo Streamlit
separado. Não permite merge nem implantação na aplicação de produção.
Os documentos anteriores registram a etapa local original.

## Aplicativo separado

- Repositório: `gustavoburnett/adtarget-intelligence`.
- Branch: `feat/google-workspace-login`.
- Entrada: **`app_homologacao.py`**, Python 3.12.
- Subdomínio pretendido: `adtarget-intelligence-homologacao` (confirmar disponibilidade no painel).
- Secrets: usar somente `.streamlit/secrets.homologacao.toml.example`, preenchido privadamente.
- Não copiar Secrets de produção. Não fornecer chave de conta de serviço.
- O entrypoint substitui exclusivamente as fontes por vendas geradas localmente,
  metas vazias e cadastro sintético. O cliente Sheets real é bloqueado.
- Gate nativo, renderização das cinco páginas e cálculos usam a implementação existente.
- Os testes de navegação sintética não reconciliam indicadores reais de produção.

## Evidência desta etapa

Sete testes offline adicionais passaram: render das cinco páginas com identidade
sintética, bloqueio anônimo no entrypoint e rejeição do cliente Sheets real.
Não representam autenticação real Google.

Google Cloud corporativo acessível após reautenticação. Projeto
`adtarget-intelligence`, plataforma OAuth ainda não configurada no início da visita.
Formulário preparado com nome “AdTarget Intelligence — Homologação”, público Interno
e contato corporativo. Política e criação ainda dependem da confirmação na interface.
Streamlit Cloud acessível; aplicação existente identificada na main com `app.py`.
Nenhuma alteração de configuração ou Secrets dessa aplicação foi feita.

## Critério para aprovação

Registrar separadamente resultados reais: corporativa, Gmail, outro Workspace,
anônimo/deep link, logout, recarga, expiração, troca de conta e cinco páginas.
Até a execução desses casos, login real permanece **pendente**, sem aprovação para produção.

Na migração futura: concluir casos reais, revisar PR/CI, autorizar explicitamente
produção, cadastrar redirect da produção e Secrets próprios, preservar revisão e
Secrets anteriores para rollback. Esta etapa não executa essa migração.
