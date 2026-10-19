# Representações comerciais — implementação para homologação

## Fonte oficial

Aba `REPRESENTACOES` da mesma planilha de vendas, criada mediante autorização expressa em 19/10/2026. Colunas: `GRUPO`, `STATUS_REPRESENTACAO`, `CONFIRMADO_EM`, `FONTE`, `FIM_REPRESENTACAO`.

Status aceitos: ATIVA, ENCERRADA e NÃO INFORMADO. ATIVA/ENCERRADA exigem confirmação ISO textual e fonte preenchida. Fim da representação é opcional e não é inferido da data de confirmação, da última venda, de campos de campanha ou de metas.

Registro autorizado: CATRACA LIVRE / ENCERRADA / confirmação em 2026-10-19 / confirmação expressa do responsável / fim em branco. A chave CATRACA LIVRE foi conferida diretamente em GRUPO e VEICULO de 2025. Nenhum status de outro parceiro foi presumido ou cadastrado.

## Validação automática da fonte e ativação controlada

Atualização aprovada em 19/10/2026. A aplicação consulta o `spreadsheetId` retornado pelos metadados do Google Sheets, na conexão existente, e compara sua impressão SHA-256 com a referência pública homologada. O ID completo não é incluído no código novo, na interface ou em mensagens de diagnóstico. Não há consulta à tela de Secrets nem nova credencial, dependência ou permissão.

Antes de ativar a exclusão, exige fonte confirmada, leitura e validação de REPRESENTACOES e registro CATRACA LIVRE = ENCERRADA. O fim da representação pode continuar vazio. Essa âncora comprova a homologação solicitada; não é uma exclusão específica: a regra de recuperação continua baseada no status de qualquer grupo.

Sem confirmação completa, o loader retorna uma pendência segura e cadastro sem status acionáveis. O Radar também verifica `validacao_concluida` antes de usar status, de forma que apenas parsear um cadastro não autoriza exclusões. A interface apresenta somente “Validação de representações pendente; alertas anteriores preservados.” ou “Fonte confirmada · cadastro acessível · regra de representações ativa.”, além de avisos de qualidade sem conteúdo da fonte.

O cache de 15 minutos inclui sucesso e pendência; reruns do dashboard reutilizam esse resultado. O botão Atualizar invalida o cache e permite nova tentativa. As exceções de acesso/estrutura não escapam do loader com detalhes da API. Não há logs de IDs, credenciais, metadados completos ou conteúdo de Secrets.

A validação ocorre no ambiente onde a aplicação está executando. A execução local confirmou fonte, leitura e ativação nas quatro combinações de métrica/critério. A confirmação em produção permanece futura até publicação expressamente autorizada.

## Regra do Radar

`src/data/representacoes.py` lê e valida o cadastro usando o cliente existente, com acesso somente leitura na aplicação. `app.py` mantém cache independente de 15 minutos, invalidado pelo botão Atualizar; consulta apenas na Performance Comercial. A criação da aba ocorreu pelo conector autorizado, sem ampliar permissões da aplicação.

`src/data/radar.py` consulta o status na geração de candidatos: ENCERRADA não gera recomendações de recuperação (insights de queda). A exclusão ocorre antes de escolher a maior queda, permitindo mostrar outro parceiro elegível. Crescimento e destaque consolidado mantêm as regras existentes. A representação atual orienta ações atuais, inclusive ao visualizar um ano passado; não reconstrói vigência histórica.

Não existe lista de parceiros excluídos no código. Identidades usam trim, caixa alta e somente os aliases já aprovados: RÁDIO MELODIA → MELODIA; CARREGA + → CARREGA+. Não há aproximação textual, busca por substring ou remoção de acentos/pontuação para unir nomes. A chave do cadastro é GRUPO, a dimensão usada pelo Radar; o status não é inferido de VEICULO.

Ausência, status inválido ou confirmação não validada ficam como NÃO INFORMADO e preservam alertas. Duplicidade de chave, inclusive após alias, invalida o status de toda a identidade envolvida, sem escolher uma linha arbitrária. Linhas inválidas e duplicidades são sinalizadas na página; cabeçalho inválido ou falha de acesso exibem diagnóstico e preservam os alertas. Isso pode fazer um alerta de parceiro encerrado reaparecer se a fonte estiver indisponível: é o comportamento solicitado de não excluir sem status validado.

O status fica disponível em `CadastroRepresentacoes.status(grupo)` e nos insights de parceiro em `status_representacao`. Não foi acrescentado um novo painel de gestão ou filtro financeiro.

## Preservação financeira e metas

Nenhuma linha de venda é removida. Os módulos de métricas, metas, rankings e comparações financeiras não foram alterados. A base completa continua alimentando indicadores, histórico, séries anuais e recorde consolidado. ATIVO/REVISAO de METAS mantêm sua semântica mensal original.

## Testes e verificação

Testes novos cobrem: encerramento sem data; substituição por outra queda elegível; ativo e NÃO INFORMADO com alerta; ausência/erro de cadastro; validação e duplicidades; aliases exatos e nomes semelhantes distintos; visualização histórica; bruto/líquido × ganho/veiculação; preservação do DataFrame e destaque consolidado; leitura somente leitura; integração da página; cache e atualização manual.

Foi validada a leitura real com o acesso já configurado da aplicação. Nos quatro pares de valor/critério, Catraca Livre não gera recuperação, os demais tipos de insight são preservados e YTD/séries financeiras permanecem iguais. Fonte transacional não sofreu mutação. A aba foi relida após a escrita e conferida visualmente em Google Planilhas.

A etapa anterior aprovou 1.488 testes. A validação automática acrescenta cenários de fonte divergente, metadados inválidos, âncora ausente/inválida/duplicada, falhas em cada etapa, preservação dos alertas sem confirmação e cache de pendências. Resultado atualizado: 1.515 testes aprovados em 117,07 segundos; 146 testes específicos aprovados em 7,20 segundos.

## Homologação e limites

Branch local isolada: `codex/radar-representacao-ativa`, baseada na main `2ce7423`. Checkout original preservado. Alterações locais sem push, PR, merge ou publicação. A aba e o registro autorizados já existem; o aplicativo publicado ainda não utiliza a regra nova.

Verificar na homologação: abrir Performance Comercial, atualizar os dados, confirmar ausência de recuperação para Catraca Livre e manutenção das comparações e indicadores. Parceiros sem registro continuam elegíveis aos alertas. O cadastro deve ser mantido com uma linha por grupo e evidência de confirmação; datas efetivas desconhecidas ficam vazias.

Um eventual Dot semanal poderá reutilizar esta fonte e a mesma regra. Dot não foi implementado.

## Procedimento de implantação controlada (ainda não executado)

1. Revisar a branch e os testes; push e PR dependem de autorização expressa.
2. Tratar a autorização de merge na main como autorização de publicação, pois o Streamlit acompanha a main. Nenhuma dessas operações está autorizada nesta etapa.
3. Na primeira carga da Performance Comercial no ambiente publicado, a checagem executará usando a conexão daquele ambiente. A exclusão fica bloqueada até a confirmação automática completa. Não é necessário abrir ou comparar Secrets.
4. Confirmar a mensagem de fonte/cadastro/regra ativa, ausência de recuperação para Catraca Livre e manutenção dos demais alertas elegíveis. Se houver pendência, a regra não entra em vigor; investigar por diagnósticos seguros, sem ativação forçada ou alteração de permissões.
5. Conferir os indicadores contra o retrato de dados usado na homologação, levando em conta novos lançamentos legítimos na planilha. Não comparar números capturados em horários diferentes como se fossem um retrato imutável.
6. Aprovar a operação somente após o resultado observado em produção. Caso uma regressão exija rollback, fazê-lo apenas com autorização correspondente, retornando à versão anterior sem alterar a planilha.

Riscos residuais: uma falha pode manter a regra pendente por até 15 minutos, antecipável com Atualizar; mudança legítima de fonte ou reativação de Catraca Livre requer nova homologação da referência/âncora. A âncora é uma condição explícita desta implantação, não uma data de vigência nem uma inferência sobre outros parceiros.
