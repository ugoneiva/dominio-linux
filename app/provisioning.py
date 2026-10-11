# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
"""Plano e pacote para criação de um DC Linux. A API nunca executa comandos root."""
import hashlib
import io
import json
from pathlib import Path
import zipfile

from .distributions import DISTRIBUTIONS
from .models import DomainSpec


def plan(spec: DomainSpec):
    manifest = spec.model_dump()
    profile = DISTRIBUTIONS[spec.distribution]
    available = profile["installer_available"]
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    steps = [
        {"title": "Preparar a VM", "detail": f"Reservar {profile['label']} dedicado, com endereço estático, backup e sem domínio Samba existente."},
        {"title": "Preservar a configuração anterior", "detail": "Copiar hostname, hosts, resolução DNS, Kerberos, Samba e horário para um diretório root protegido."},
        {"title": "Instalar os serviços" if available else "Definir a integração Samba AD DC", "detail": "Instalar Samba AD DC, Kerberos, ferramentas DNS e chrony pelo repositório da distribuição." if available else "Selecionar uma origem de Samba com o papel AD DC e definir pacotes, serviços, SELinux e firewall. Este adaptador ainda não está implementado."},
        {"title": "Criar o domínio", "detail": f"Provisionar {spec.fqdn} no controlador {spec.hostname}; a senha Administrator será solicitada diretamente na VM."},
        {"title": "Configurar DNS e horário", "detail": f"Usar o controlador {spec.address} para resolver o domínio; encaminhador {spec.forwarder}; horário {spec.ntp_server}."},
        {"title": "Iniciar o controlador Linux", "detail": "Ativar samba-ad-dc e chrony; emitir instruções de conexão e ingresso de membros." if available else "Definir as unidades de serviço do adaptador e validar autenticação, DNS, horário e ingresso de Windows e Linux."},
    ]
    changes = ["Pacotes instalados por apt" if available else "Origem de pacotes AD DC e serviços ainda a definir", "/etc/hostname e hostname da VM", "/etc/hosts", "/etc/resolv.conf", "/etc/krb5.conf", "/etc/samba/smb.conf e estado do domínio", "/etc/chrony/conf.d/dominio-linux.conf" if available else "Configuração chrony conforme a distribuição", "Serviços Samba, resolução local e chrony"]
    requirements = ["VM dedicada e snapshot ou backup anterior", "IP estático atribuído à interface; esta versão não altera a configuração da placa", f"Acesso aos repositórios de {profile['label']} e fonte de horário", "Portas do domínio liberadas na rede do laboratório", "Certificado LDAPS confiável para consultar pelo painel"]
    if not available:
        requirements.append("Implementação e validação do instalador específico de Samba AD DC; pacotes para servidor membro não comprovam o papel de controlador")
    return {
        "manifest": manifest, "digest": digest, "distribution": profile,
        "installer_available": available,
        "target": f"VM {profile['label']} dedicada com IPv4 estático já configurado",
        "execution": "Pacote para executar na VM; o painel não instala serviços nesta máquina." if available else "Plano de preparação; o instalador desta distribuição ainda não está disponível.",
        "steps": steps, "changes": changes, "requirements": requirements,
        "state": "plano; não executado",
    }


def package(spec: DomainSpec):
    payload = io.BytesIO()
    result = plan(spec)
    profile = result["distribution"]
    header = f"""Domínio Linux — pacote de laboratório
Desenvolvido por JLW Security. Copyright (C) 2026 JLW Security.
Software livre sob GNU GPL versão 3 ou posterior, sem garantia.
Consulte LICENSE; redistribuição permitida nos termos da licença.
Código-fonte: https://github.com/ugoneiva/dominio-linux

Domínio: {spec.fqdn}
Controlador Linux: {spec.hostname}.{spec.fqdn} / {spec.address}
Destino: VM {profile['label']} dedicada, vazia, com IP estático configurado.
Estado: {profile['status']}

"""
    if profile["installer_available"]:
        instructions = header + """1. Preserve um snapshot/backup da VM e confirme a rede e o IP.
2. Leia manifest.json, distributions.json e provision_dc.py antes da execução.
3. Na VM: sudo /usr/bin/python3 provision_dc.py --manifest manifest.json
4. Confirme o domínio no terminal. A senha Administrator será solicitada na VM.
5. Siga o resultado emitido pelo instalador.

O instalador é uma implementação inicial, ainda sem execução validada em VM.
Ele não configura firewall, IP da interface, certificado de CA ou segundo DC.
Configure a cadeia LDAPS antes de usar a tela Integração Samba.
O painel não transmite nem persiste a senha Administrator.
Falhas interrompem o processo. Não há rollback automático de domínio parcial;
consulte os backups e restaure o snapshot da VM quando necessário.
"""
    else:
        instructions = header + f"""Este ZIP contém planejamento, manifesto e catálogo de distribuições.
O instalador para {profile['label']} ainda não está implementado.

{profile['note']}

Antes de automatizar a criação do domínio nesta distribuição:
1. Definir a origem e manutenção de Samba com suporte ao papel AD DC.
2. Implementar o adaptador de pacotes e serviços específico.
3. Definir configuração SELinux, firewall, DNS, Kerberos e chrony.
4. Validar a criação e recuperação em VM isolada e o ingresso dos membros.

As etapas em plano.json são uma proposta de implementação e não foram executadas.
"""
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("LICENSE", (Path(__file__).resolve().parent / "resources" / "LICENSE").read_text())
        archive.writestr("manifest.json", json.dumps(spec.model_dump(), indent=2, ensure_ascii=False))
        archive.writestr("LEIA-ME.txt", instructions)
        archive.writestr("plano.json", json.dumps(result, indent=2, ensure_ascii=False))
        archive.writestr("distributions.json", json.dumps(DISTRIBUTIONS, indent=2, ensure_ascii=False))
        if profile["installer_available"]:
            script = Path(__file__).resolve().parent / "resources" / "provision_dc.py"
            archive.writestr("provision_dc.py", script.read_text())
    return payload.getvalue()
