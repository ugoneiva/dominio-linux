# Fontes técnicas consultadas

Consulta em 11/10/2026. Foram utilizadas documentações dos projetos e código oficial para confirmar as integrações e a direção de implementação.

- [Samba — samba-tool](https://www.samba.org/samba/docs/current/man-html/samba-tool.8.html): operações de domínio, objetos, GPOs e políticas Linux. Suporte depende da versão do Samba instalada.
- [Samba — implementação oficial do provisionamento, ramo 4.22](https://github.com/samba-team/samba/blob/v4-22-stable/python/samba/netcmd/domain/provision.py): parâmetros e sequência de prompts interativos. O projeto chama a ferramenta instalada; não incorpora esse código.
- [Ubuntu Server — criar um controlador Samba AD](https://ubuntu.com/server/docs/how-to/samba/provision-samba-ad-controller/): pacotes e configuração de controlador Linux.
- [Ubuntu 26.04 — notas para usuários LTS](https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/): pacote samba-ad-dc e atualizações do Samba.
- [Red Hat — Samba no RHEL 9](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_using_network_file_services/assembly_using-samba-as-a-server_configuring-and-using-network-file-services): a Red Hat não oferece suporte ao papel AD DC. Isso é distinto de ingressar um servidor membro no domínio.
- [Debian 13 — pacote samba-ad-dc](https://packages.debian.org/trixie/samba-ad-dc): pacote e dependências para controlador de domínio.
- [FastAPI — templates](https://fastapi.tiangolo.com/advanced/templates/): integração da interface HTML.
- [FastAPI — segurança](https://fastapi.tiangolo.com/tutorial/security/first-steps/): referência do framework. A autenticação local desta versão utiliza sessões próprias, não o exemplo OAuth2 desta página.
- [ldap3 — TLS](https://ldap3.readthedocs.io/en/latest/ssltls.html): configuração de validação de certificado e cadeia em memória.
- [ldap3 — busca](https://ldap3.readthedocs.io/en/latest/searches.html): consulta e paginação do diretório.
- [ldap3 — conexão](https://ldap3.readthedocs.io/en/latest/connection.html): conexão de leitura, timeouts e referências.
- [Microsoft — Central Store e modelos administrativos](https://learn.microsoft.com/en-us/troubleshoot/windows-client/group-policy/create-and-manage-central-store): referência para evolução do editor de políticas dos membros Windows.
- [Red Hat — integração AD e GPOs via SSSD](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/integrating_rhel_systems_directly_with_windows_active_directory/managing-direct-connections-to-ad_integrating-rhel-systems-directly-with-active-directory): exemplo de suporte específico nos membros Linux.

- [Texto GPLv3 fornecido pela API do GitHub](https://api.github.com/licenses/gpl-3.0): cópia integral da licença utilizada nos arquivos LICENSE.

## Referências de produtos semelhantes

- [UCS — console web](https://docs.software-univention.de/manual/5.2/en/central-management-umc/index.html)
- [UCS — serviços Samba e políticas](https://docs.software-univention.de/manual/5.2/en/windows/samba-domain.html)
- [Zentyal — domínio e diretório](https://doc.zentyal.org/en/directory.html)
- [EasyDC](https://github.com/easysysio/EasyDC)
- [Samba Conductor v2](https://github.com/openbasalt/samba-conductor)
- [Samba Conductor — arquivos e ACLs](https://github.com/openbasalt/samba-conductor-files)

A implementação inicial é própria, sem copiar ou instalar esses produtos. A avaliação de reaproveitamento permanece aberta para os módulos avançados. Dependências Python e executáveis externos mantêm suas próprias licenças; o código próprio do projeto é distribuído sob GPL versão 3 ou posterior, por autorização do usuário.
