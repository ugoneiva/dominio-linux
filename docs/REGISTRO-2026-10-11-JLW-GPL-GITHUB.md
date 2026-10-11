# JLW Security, GPL e publicação GitHub — 11/10/2026

## Solicitação

Adicionar menções ao desenvolvimento pela JLW Security, aplicar licença GPL Open Source e publicar no repositório https://github.com/ugoneiva/dominio-linux.

## Implementação

- Copyright JLW Security e identificadores SPDX GPL-3.0-or-later no código próprio.
- Texto integral GPLv3 em LICENSE e no recurso incluído nos pacotes Python e ZIP.
- NOTICE, metadados de autoria/licença e orientações de contribuição.
- Créditos e avisos da licença acessíveis no login e no painel, incluindo telas pequenas.
- Rota pública /license para leitura do texto, sem necessidade de login.
- Créditos, licença e referência ao código-fonte nos pacotes de provisionamento.
- README com clone do repositório, instruções e situação das integrações.
- Preservação do commit inicial existente no GitHub; commit local preparado para envio por avanço normal, sem force push.

## Publicação

Destino: repositório público ugoneiva/dominio-linux, branch main. A autenticação da sessão de publicação usa credencial transitória em memória; URLs Git não incluem o token. Dados locais, ambiente virtual, bancos, chaves privadas e arquivos de ambiente permanecem fora do conjunto publicado.

### Situação do envio

O GitHub recusou o push com HTTP 403. A API confirmou `Resource not accessible by personal access token`, exigindo `contents=write`. O token autentica e permite consulta do repositório, mas não autoriza esta escrita. Publicação pendente de ajuste de **Repository permissions → Contents → Read and write** no token, com acesso ao repositório alvo. Nenhum código novo foi publicado nesta tentativa.

## Limites

Não foram adicionados nem executados testes de implementação nesta atividade. A publicação não representa validação em controlador Samba real ou execução do instalador em VM.
