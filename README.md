# Domínio Linux

**Desenvolvido por JLW Security** · [Código-fonte](https://github.com/ugoneiva/dominio-linux) · **GPL-3.0-or-later**

Plataforma local para **criar e administrar um domínio Samba em Linux**, com servidores e workstations Windows e Linux como membros. Nome provisório do projeto.

## Versão inicial — 0.1.0

Esta entrega inicia o projeto com aplicação executável e fluxo de provisionamento. Ainda não é uma plataforma pronta para produção.

| Recurso | Estado desta versão |
| --- | --- |
| Painel em português | Visão geral, navegação, busca e telas responsivas |
| Autenticação | Administrador local, senha inicial aleatória, hash PBKDF2 e sessões com expiração |
| Usuários, grupos, OUs e computadores | Criar, editar e excluir objetos fictícios no laboratório local |
| DNS | Cadastrar e editar registros de laboratório; não publicados no DNS real |
| Políticas | Editor de rascunhos de Registro Windows, OpenSSH e sudo Linux; exportação JSON |
| Compartilhamentos | Rascunhos de caminhos, grupos e permissões; sem criar arquivos ou ACLs reais |
| Histórico | Alterações locais e conexões; sem senhas nos eventos |
| Criação de domínio Linux | Assistente para Debian, Ubuntu, Red Hat, Oracle Linux, AlmaLinux e Rocky Linux; instaladores iniciais Debian/Ubuntu e planos Enterprise Linux |
| Consulta Samba | Conector LDAPS de leitura para usuários, grupos, OUs, computadores e metadados de GPO |
| Escritas reais, SYSVOL, segundo DC, MFA, perfis e recuperação | Próximas entregas |

Os dados iniciais são fictícios e usam `corp.exemplo.test`. Os serviços apresentados no painel têm estado **não consultado** até existir diagnóstico real. O cadastro de uma máquina no laboratório não significa ingresso no domínio.

## Executar localmente

Requer Python 3.11 ou superior. Utilize um ambiente virtual do projeto:

```bash
git clone https://github.com/ugoneiva/dominio-linux.git
cd dominio-linux
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
./scripts/start.sh
```

Abra **http://127.0.0.1:8840**. Usuário: **admin**.

A senha aleatória do primeiro acesso está em [`.state/initial-password.txt`](.state/initial-password.txt), com permissão 0600. Esse arquivo, o banco e o ambiente virtual são excluídos do Git. A aplicação não escreve credenciais do Samba no banco. O arquivo da senha inicial permanece acessível ao usuário local que é dono do projeto; mantenha o diretório privado.

Para alterar a senha local, execute `.venv/bin/python scripts/change_password.py` na pasta do projeto. A operação solicita a senha atual, revoga as sessões e remove o arquivo da senha inicial. Não altera a senha Administrator do domínio.

O servidor usa somente loopback por padrão. Para implantação futura na rede, usar TLS, autenticação administrativa evoluída, perfis e validação operacional antes da exposição. A configuração `DL_SECURE_COOKIE=1` exige acesso HTTPS.

## Distribuições do controlador

| Distribuição | Estado nesta versão |
| --- | --- |
| Debian 13 | Instalador inicial, execução em VM ainda não validada |
| Ubuntu 24.04 LTS e 26.04 LTS | Instalador inicial, execução em VM ainda não validada |
| Red Hat Enterprise Linux 9 | Planejamento e manifesto; integração do instalador pendente |
| Oracle Linux 9 | Planejamento e manifesto; integração do instalador pendente |
| AlmaLinux 9 | Planejamento e manifesto; integração do instalador pendente |
| Rocky Linux 9 | Planejamento e manifesto; integração do instalador pendente |

As opções são persistidas e aparecem no plano e no nome do ZIP. Para perfis sem instalador, o ZIP contém configuração e requisitos, sem script de instalação. A Red Hat não oferece suporte ao papel Samba AD DC no RHEL padrão, conforme a [documentação oficial](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_using_network_file_services/assembly_using-samba-as-a-server_configuring-and-using-network-file-services). A integração Enterprise Linux deverá definir origem e manutenção de Samba AD DC, serviços, SELinux e firewall.

O cadastro de computadores sugere essas distribuições e Windows, permitindo informar outras versões. Isso descreve a máquina no laboratório; não comprova ingresso ou suporte operacional.

O painel e o login usam tons de azul, superfícies claras, texto escuro e foco de teclado visível. Avisos e exclusões mantêm cores próprias e rótulos descritivos.

## Criar um domínio em Linux

1. No painel, abra **Criar domínio Linux**.
2. Escolha a distribuição e defina domínio DNS, nome curto, hostname, IPv4 estático, sub-rede, encaminhador DNS e fonte de horário.
3. Gere o plano e revise os requisitos e arquivos alterados.
4. Baixe o ZIP. O download não altera nenhum servidor.
5. Para Debian/Ubuntu, em uma **VM dedicada e vazia da distribuição e versão selecionadas**, configure previamente o IP estático e preserve snapshot/backup.
6. Extraia o pacote na VM e leia `LEIA-ME.txt`, `manifest.json`, `distributions.json` e `provision_dc.py`.
7. Execute no console da VM:

```bash
sudo /usr/bin/python3 provision_dc.py --manifest manifest.json
```

O instalador solicita confirmação do domínio e a senha Administrator no terminal. Instala os pacotes da distribuição selecionada, provisiona Samba, configura resolução DNS/Kerberos/chrony e inicia o controlador. A senha não aparece em argumentos de processo, no manifesto ou no plano.

**Limites:** instalador escrito, ainda sem execução validada em VM nesta entrega. Não altera o IP da interface, não configura firewall, não emite certificado de CA, não ingressa estações e não configura outro DC. Em falha, interrompe o processo; não há rollback automático de um domínio parcial. Preserve a saída, consulte `/root/dominio-linux-backups` e restaure o snapshot antes de repetir sobre uma VM parcialmente provisionada.

## Consultar Samba pelo painel

Abra **Integração Samba** e informe hostname, porta LDAPS, DN do domínio, conta de consulta e cadeia PEM da CA se ela não estiver no trust store do sistema.

- O certificado e o hostname precisam ser válidos; não há opção para ignorar TLS.
- Utilize um controlador Samba em Linux e uma conta com os direitos de leitura necessários.
- As credenciais permanecem somente na memória da sessão, por até 8 horas, e são removidas ao desconectar, sair ou expirar. O servidor deve operar com um único worker nesta versão.
- As consultas usam paginação e recusam uma listagem acima de 10.000 objetos; filtro de servidor está previsto para domínios maiores.
- Ao conectar, o painel mostra dados do diretório e bloqueia as escritas de laboratório. Ao desconectar, os exemplos locais reaparecem.
- DNS e compartilhamentos não têm conector real nesta versão; GPOs apresentam somente metadados, sem leitura de vínculos ou conteúdo SYSVOL.

## Estrutura

```text
app/
  main.py              API e regras das operações
  auth.py              Administrador local e sessões
  store.py             SQLite do laboratório e histórico
  models.py            Validação das entradas
  directory.py         Conector LDAPS de leitura
  provisioning.py      Plano e pacote de criação
  resources/           Instalador empacotado para a VM
  static/              Interface web, sem CDN
  templates/           Login e estrutura do painel
docs/                  Escopo, arquitetura, entregas e fontes
scripts/               Inicialização local e administração do painel
.state/                Dados locais e senha inicial; fora do Git
```

SQLite atende a primeira entrega local. O diretório Samba será a fonte das identidades reais; o banco do painel armazena configuração, tarefas e auditoria. PostgreSQL e trabalhadores de tarefas serão avaliados para implantação com múltiplos administradores.

## Desenvolvimento e continuidade

Consulte [arquitetura](docs/ARQUITETURA.md), [plano de entregas](docs/ENTREGAS.md), [fontes técnicas](docs/FONTES.md) e [registro desta entrega](docs/REGISTRO-2026-10-11.md).

Não foram adicionados nem executados testes automatizados nesta atividade. Inicialização local, instalação de dependências e inspeção do código não comprovam funcionamento em Samba real ou em produção.

## Licença e créditos

Copyright (C) 2026 **JLW Security**. Projeto Open Source, distribuído sob a **GNU General Public License, versão 3 ou posterior (GPL-3.0-or-later)**.

Você pode utilizar, estudar, modificar e redistribuir o projeto nos termos da licença. O software é fornecido **sem garantia**. Consulte o texto integral em [LICENSE](LICENSE) e os avisos em [NOTICE](NOTICE).

Login, painel e pacotes de provisionamento incluem os créditos e acesso à licença. Dependências Python e ferramentas externas mantêm seus próprios avisos e licenças.

Contribuições são bem-vindas: consulte [CONTRIBUTING.md](CONTRIBUTING.md).
