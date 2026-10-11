# Entregas e continuidade

## 0.1 — Fundação, implementada nesta atividade

- [x] Repositório independente e documentação do foco em domínio Linux.
- [x] Painel em português, com layout responsivo e navegação por módulos.
- [x] Login administrativo local, sessão e proteção das operações de alteração.
- [x] Cadastros persistidos de usuários, grupos, OUs e computadores fictícios.
- [x] Associações de grupos e hierarquia de OUs com regras de integridade.
- [x] DNS de laboratório e rascunhos de compartilhamentos.
- [x] Editor de rascunhos de políticas Windows/Registro, Linux/OpenSSH e Linux/sudo.
- [x] Exportação JSON das políticas com indicação de rascunho não publicado.
- [x] Histórico de alterações locais.
- [x] Assistente para Debian, Ubuntu, Red Hat, Oracle Linux, AlmaLinux e Rocky Linux; pacotes iniciais Debian/Ubuntu e planos Enterprise Linux.
- [x] Tema azul no painel e login, com textos secundários mais escuros e foco visível.
- [x] Conector de leitura Samba/LDAPS implementado, sem execução em domínio real.
- [x] Dependências instaladas em ambiente virtual e versões registradas.

Os itens marcados representam implementação. Não representam testes aprovados ou validação em produção.

## 0.2 — Domínio real em laboratório

- [ ] Definir VM nova, rede, nome DNS e primeiro controlador.
- [ ] Executar e validar os instaladores Debian e Ubuntu nas versões do catálogo.
- [ ] Implementar adaptadores Samba AD DC para Red Hat, Oracle Linux, AlmaLinux e Rocky Linux, definindo origem de pacotes, serviços, SELinux e firewall.
- [ ] Configurar cadeia LDAPS confiável e comprovar consulta do diretório.
- [ ] Ingressar pelo menos uma workstation Windows e uma Linux.
- [ ] Implementar criação/alteração real de usuários e grupos, movimentação de OUs, senhas e expiração.
- [ ] Implementar autorização com direitos delegados, MFA e perfis administrativos.
- [ ] Integrar DNS e diagnóstico de serviços/horário.
- [ ] Implementar tarefas com resultado por operação e cancelamento quando suportado.

## 0.3 — Políticas, arquivos e máquinas

- [ ] Definir lista inicial de políticas obrigatórias do usuário.
- [ ] Ler e publicar arquivos de políticas no SYSVOL com controle de versão e direitos.
- [ ] Implementar vínculos, ordem, herança e filtros de aplicação de GPO.
- [ ] Evoluir o editor Windows com modelos ADMX/ADML.
- [ ] Implementar políticas Linux conforme mecanismo de cliente escolhido.
- [ ] Integrar servidor Samba membro para compartilhamentos e ACLs.
- [ ] Mostrar permissões efetivas e grupos envolvidos.
- [ ] Implementar renomeação e tarefas remotas nas estações com retorno de resultado.
- [ ] Mostrar configurações publicadas e estado aplicado separadamente.

## 0.4 — Continuidade e operação

- [ ] Incluir segundo DC Linux, replicação e distribuição do SYSVOL.
- [ ] Implementar backups do domínio e recuperação em laboratório isolado.
- [ ] Documentar atualização, migração e retomada de tarefas interrompidas.
- [ ] Exportar auditoria para destino externo com retenção.
- [ ] Preparar implantação por TLS na rede e limites operacionais.
- [ ] Definir matriz de versões suportadas e critérios de aceitação.

## Dependências de ambiente

Foi solicitado ao usuário informar uma VM Linux dedicada disponível, distribuição e IP. O desenvolvimento local prossegue sem depender dessa resposta. A implantação real depende de um destino específico; a autorização geral não seleciona uma máquina de cliente como alvo.

## Escopo e estimativas

O objetivo original inclui criação e administração completas do domínio Linux. A versão 0.1 é a primeira entrega, sem declaração de conclusão do produto. Estimativas de prazo e orçamento precisam considerar o ambiente, o reaproveitamento de módulos, as políticas prioritárias e a matriz de suporte.
