# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
"""Catálogo de destinos; disponibilidade do instalador é uma decisão do projeto."""

# samba-ad-provision traz os arquivos usados pelo `samba-tool domain provision`. No Ubuntu 24.04
# ele vem só como Recommends do samba-ad-dc; imagens mínimas/nuvem com Install-Recommends=false
# ficariam sem ele e o provisionamento falharia. Por isso vai explícito em todos os perfis apt.
APT_PACKAGES = ["samba-ad-dc", "samba-ad-provision", "krb5-user", "smbclient", "bind9-dnsutils", "chrony", "acl", "attr", "python3-pexpect"]


def apt_profile(identifier, label, os_id, version):
    return {
        "id": identifier, "label": label, "os_id": os_id, "version": version,
        "family": "Debian / Ubuntu", "installer_available": True,
        "status": "Instalador inicial",
        "note": "Pacote de criação do primeiro controlador disponível. A execução e a validação em VM ainda estão pendentes.",
        "packages": list(APT_PACKAGES),
    }


def rpm_profile(identifier, label, os_id):
    note = "Plano disponível. O instalador Samba AD DC para esta distribuição ainda precisa de integração; o download contém a configuração e os requisitos."
    if os_id == "rhel":
        note += " A Red Hat não oferece suporte ao papel AD DC nos pacotes padrão do RHEL."
    return {
        "id": identifier, "label": label, "os_id": os_id, "version": "9",
        "family": "Enterprise Linux / RPM", "installer_available": False,
        "status": "Planejamento", "note": note, "packages": [],
    }


DISTRIBUTIONS = {
    profile["id"]: profile for profile in [
        apt_profile("debian-13", "Debian 13", "debian", "13"),
        apt_profile("ubuntu-24.04", "Ubuntu 24.04 LTS", "ubuntu", "24.04"),
        apt_profile("ubuntu-26.04", "Ubuntu 26.04 LTS", "ubuntu", "26.04"),
        rpm_profile("rhel-9", "Red Hat Enterprise Linux 9", "rhel"),
        rpm_profile("oracle-9", "Oracle Linux 9", "ol"),
        rpm_profile("alma-9", "AlmaLinux 9", "almalinux"),
        rpm_profile("rocky-9", "Rocky Linux 9", "rocky"),
    ]
}
