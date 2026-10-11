# Ampliação de distribuições e tema azul — 11/10/2026

Solicitação: incluir Ubuntu, Red Hat, Oracle Linux, AlmaLinux e Rocky Linux e adotar cores próximas ao azul, preservando leitura.

## Alterações implementadas

- Catálogo central com Debian 13, Ubuntu 24.04/26.04 LTS e perfis Enterprise Linux 9.
- Validação da distribuição na API, seleção no assistente e persistência na configuração.
- Disponibilidade do instalador exibida por distribuição, com notas e download correspondente.
- Pacote e instruções ajustados ao destino; o instalador inicial confere distribuição e versão antes de modificar a VM.
- Debian e Ubuntu incluem script; perfis RPM incluem plano/manifesto, com integração de instalação pendente.
- Sugestões de sistemas no cadastro de computadores, mantendo entrada livre.
- Azul no login, navegação, botões, cartões, diálogos e mensagens; texto secundário mais escuro, foco visível e placeholders legíveis.
- Referências de arquivos estáticos atualizadas para renovar o cache do navegador.

## Limites

Não foram adicionados nem executados testes. Inspeção do código e inicialização local não validam instalação em VM, integração com domínio real ou contraste medido em navegador. Nenhuma VM ou domínio de cliente foi alterado. Os perfis RPM permanecem no planejamento e não recebem um instalador apt incompatível.
