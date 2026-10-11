#!/usr/bin/python3
# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
"""Instalador inicial para um primeiro controlador Samba em VM Debian/Ubuntu dedicada.

Este arquivo é entregue pelo painel; só executa alterações com --manifest e a
confirmação digitada no console da VM. Nunca é executado pelo servidor web.
"""
import argparse
from datetime import datetime, timezone
import getpass
import grp
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def run(*args, env=None):
    print("→ " + " ".join(args), flush=True)
    subprocess.run(list(args), check=True, env=env)


def installer_profile(manifest):
    supported = {
        "debian-13": ("debian", "13"),
        "ubuntu-24.04": ("ubuntu", "24.04"),
        "ubuntu-26.04": ("ubuntu", "26.04"),
    }
    identifier = manifest["distribution"]
    if identifier not in supported:
        raise ValueError("O instalador desta distribuição ainda não está disponível.")
    profiles = json.loads(Path(__file__).with_name("distributions.json").read_text())
    profile = profiles.get(identifier, {})
    if (profile.get("os_id"), profile.get("version")) != supported[identifier] or profile.get("installer_available") is not True:
        raise ValueError("Catálogo de distribuições incompatível com o instalador.")
    packages = profile.get("packages")
    if not isinstance(packages, list) or not packages or not all(isinstance(name, str) and re.fullmatch(r"[a-z0-9][a-z0-9+.-]+", name) for name in packages):
        raise ValueError("Lista de pacotes inválida no catálogo.")
    return profile


def valid_manifest(manifest):
    required = {"label", "fqdn", "netbios", "hostname", "address", "subnet", "forwarder", "ntp_server", "distribution"}
    if set(manifest) != required or not all(isinstance(value, str) for value in manifest.values()):
        raise ValueError("Manifesto inválido: campos inesperados ou ausentes.")
    installer_profile(manifest)
    for key in ("fqdn", "ntp_server"):
        if len(manifest[key]) > 200 or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+", manifest[key]):
            raise ValueError(f"Nome DNS inválido: {key}.")
    if manifest["fqdn"].endswith(".local"):
        raise ValueError("O sufixo .local não é aceito por este instalador.")
    for key in ("hostname", "netbios"):
        if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9-]{0,14}", manifest[key]) or manifest[key].endswith("-"):
            raise ValueError(f"Nome curto inválido: {key}.")
    address = ipaddress.IPv4Address(manifest["address"])
    forwarder = ipaddress.IPv4Address(manifest["forwarder"])
    network = ipaddress.IPv4Network(manifest["subnet"], strict=True)
    for ip in (address, forwarder):
        if ip.is_loopback or ip.is_multicast or ip.is_unspecified or ip.is_link_local:
            raise ValueError("Endereço de rede inválido.")
    if address == forwarder or address not in network or address in (network.network_address, network.broadcast_address):
        raise ValueError("IP do controlador, sub-rede ou encaminhador inconsistentes.")
    return manifest


def os_release():
    values = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip('"')
    return values


def preflight(manifest):
    if os.geteuid() != 0:
        raise RuntimeError("Execute na VM dedicada com sudo /usr/bin/python3.")
    release = os_release()
    profile = installer_profile(manifest)
    if release.get("ID") != profile["os_id"] or release.get("VERSION_ID") != profile["version"]:
        raise RuntimeError(f"Destino incompatível: é necessária uma VM {profile['label']} dedicada, conforme o manifesto.")
    for path in ("/var/lib/samba/private/sam.ldb", "/var/lib/samba/private/secrets.ldb", "/var/lib/samba/private/secrets.tdb"):
        if Path(path).exists():
            raise RuntimeError("Já existe estado Samba neste servidor. O instalador não substitui nem migra um domínio.")
    if Path("/etc/samba/smb.conf").exists():
        configuration = Path("/etc/samba/smb.conf").read_text()
        if re.search(r"(?im)^\s*(realm|security)\s*=", configuration):
            raise RuntimeError("Foi encontrada configuração de domínio/membro Samba. Utilize uma VM vazia.")
    interfaces = json.loads(subprocess.check_output(["ip", "-j", "-4", "address", "show"], text=True))
    found = [addr for interface in interfaces for addr in interface.get("addr_info", []) if addr.get("local") == manifest["address"]]
    if not found:
        raise RuntimeError("O IP do manifesto ainda não está atribuído à VM. Configure um endereço estático antes de continuar.")
    if any(addr.get("dynamic") or "dynamic" in addr.get("flags", []) for addr in found):
        raise RuntimeError("O IP informado foi identificado como dinâmico. Configure um endereço estático.")
    if not Path("/run/systemd/system").exists():
        raise RuntimeError("É necessário systemd operacional na VM.")
    if Path("/etc/resolv.conf").is_symlink():
        target = str(Path("/etc/resolv.conf").resolve())
        if not target.startswith("/run/systemd/resolve/"):
            raise RuntimeError("O DNS é gerenciado por outro serviço. Prepare a resolução DNS da VM antes da instalação.")


def backup_files(directory):
    directory.mkdir(parents=True, mode=0o700)
    inventory = []
    for name in ("/etc/hostname", "/etc/hosts", "/etc/resolv.conf", "/etc/krb5.conf", "/etc/samba/smb.conf", "/etc/chrony/chrony.conf", "/etc/chrony/conf.d/dominio-linux.conf"):
        path = Path(name)
        record = {"path": name, "exists": path.exists(), "symlink": str(path.readlink()) if path.is_symlink() else None}
        if path.exists():
            shutil.copy2(path, directory / name.replace("/", "_").lstrip("_"))
        inventory.append(record)
    (directory / "inventory.json").write_text(json.dumps(inventory, indent=2))
    (directory / "services-before.txt").write_text(subprocess.run(["systemctl", "list-unit-files", "smbd.service", "nmbd.service", "winbind.service", "samba-ad-dc.service", "systemd-resolved.service", "chrony.service"], capture_output=True, text=True).stdout)


def write_file(path, content, mode=0o644):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        path.unlink()
    temporary = path.with_name(path.name + ".dominio-linux.tmp")
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    os.fchmod(fd, mode)
    with os.fdopen(fd, "w") as stream:
        stream.write(content)
    temporary.replace(path)


def provision(manifest, password):
    import pexpect

    args = ["domain", "provision", "--interactive", "--use-rfc2307", f"--host-name={manifest['hostname']}", f"--host-ip={manifest['address']}"]
    child = pexpect.spawn("/usr/bin/samba-tool", args, encoding="utf-8", timeout=300)
    # Somente saída é registrada; respostas e senha enviadas não são logadas.
    child.logfile_read = sys.stdout
    questions = [
        (r"Realm(?: \[[^\r\n]*\])?:", manifest["fqdn"].upper()),
        (r"Domain(?: \[[^\r\n]*\])?:", manifest["netbios"].upper()),
        (r"Server Role[^\r\n]*:", "dc"),
        (r"DNS backend[^\r\n]*:", "SAMBA_INTERNAL"),
        (r"DNS forwarder IP address[^\r\n]*:", manifest["forwarder"]),
    ]
    try:
        for prompt, answer in questions:
            child.expect(prompt)
            child.sendline(answer)
        child.expect("Administrator password:")
        if not child.waitnoecho(timeout=5):
            raise RuntimeError("O terminal do provisionamento não ocultou a senha; processo interrompido.")
        child.sendline(password)
        child.expect("Retype password:")
        child.sendline(password)
        child.expect(pexpect.EOF)
        child.close()
        if child.exitstatus != 0:
            raise RuntimeError("O Samba não concluiu o provisionamento. Preserve a saída e restaure a VM antes de repetir.")
    finally:
        if child.isalive():
            child.terminate(force=True)


def install(manifest, backup):
    password = getpass.getpass("Nova senha Administrator do domínio (mínimo 12 caracteres): ")
    repeated = getpass.getpass("Repita a senha: ")
    if password != repeated or len(password) < 12 or sum(bool(re.search(pattern, password)) for pattern in (r"[a-z]", r"[A-Z]", r"[0-9]", r"[^a-zA-Z0-9]")) < 3:
        raise ValueError("A senha deve coincidir, ter pelo menos 12 caracteres e três classes de caracteres.")
    backup_files(backup)
    env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
    run("apt-get", "update", env=env)
    run("apt-get", "install", "-y", *installer_profile(manifest)["packages"], env=env)
    run("systemctl", "disable", "--now", "smbd", "nmbd", "winbind")
    run("systemctl", "mask", "smbd", "nmbd", "winbind")
    run("hostnamectl", "set-hostname", manifest["hostname"])
    hosts = Path("/etc/hosts").read_text()
    hosts = "\n".join(line for line in hosts.splitlines() if not re.match(r"^\s*127\.0\.1\.1\s", line))
    hosts += f"\n{manifest['address']} {manifest['hostname']}.{manifest['fqdn']} {manifest['hostname']}\n"
    write_file("/etc/hosts", hosts)
    if Path("/etc/samba/smb.conf").exists():
        shutil.copy2("/etc/samba/smb.conf", backup / "smb.conf-package-default")
        Path("/etc/samba/smb.conf").unlink()
    provision(manifest, password)
    password = repeated = ""
    shutil.copy2("/var/lib/samba/private/krb5.conf", "/etc/krb5.conf")
    if subprocess.run(["systemctl", "is-active", "--quiet", "systemd-resolved"], check=False).returncode == 0:
        run("systemctl", "disable", "--now", "systemd-resolved")
    write_file("/etc/resolv.conf", f"search {manifest['fqdn']}\nnameserver {manifest['address']}\n")
    write_file("/etc/chrony/conf.d/dominio-linux.conf", f"server {manifest['ntp_server']} iburst\nallow {manifest['subnet']}\nntpsigndsocket /var/lib/samba/ntp_signd\n")
    chrony_config = Path("/etc/chrony/chrony.conf").read_text()
    if not re.search(r"(?m)^\s*confdir\s+/etc/chrony/conf.d\s*$", chrony_config):
        write_file("/etc/chrony/chrony.conf", chrony_config + "\nconfdir /etc/chrony/conf.d\n")
    socket_dir = Path("/var/lib/samba/ntp_signd")
    socket_dir.mkdir(exist_ok=True)
    socket_dir.chmod(0o750)
    os.chown(socket_dir, 0, grp.getgrnam("_chrony").gr_gid)
    run("systemctl", "unmask", "samba-ad-dc")
    run("systemctl", "enable", "--now", "samba-ad-dc")
    run("systemctl", "restart", "chrony")
    run("systemctl", "is-active", "samba-ad-dc", "chrony")
    result = {"completed_at": datetime.now(timezone.utc).isoformat(), "fqdn": manifest["fqdn"], "controller": manifest["hostname"], "address": manifest["address"], "backup_directory": str(backup), "state": "provisionamento concluído; ingresso de clientes e validação operacional pendentes"}
    (backup / "result.json").write_text(json.dumps(result, indent=2))
    print(f"\nControlador Samba criado em Linux: {manifest['hostname']}.{manifest['fqdn']}\nDNS dos membros: {manifest['address']}\nBackup dos arquivos anteriores: {backup}\nConfigure certificado LDAPS confiável para usar a tela Integração Samba.\nLibere as portas de domínio na rede e valide ingresso, políticas e recuperação antes de produção.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = valid_manifest(json.loads(args.manifest.read_text()))
        preflight(manifest)
        print("Domínio Linux — desenvolvido por JLW Security. Copyright (C) 2026 JLW Security.\nGNU GPL versão 3 ou posterior; software livre, sem garantia.\nRedistribuição permitida conforme LICENSE, incluído neste pacote.")
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        print("\nEste processo altera a VM e cria o primeiro domínio Samba em Linux.\nÉ necessário backup/snapshot anterior; nenhuma configuração de IP ou firewall será feita.")
        confirmation = input(f"Para instalar, digite CRIAR {manifest['fqdn']}: ")
        if confirmation != f"CRIAR {manifest['fqdn']}":
            raise RuntimeError("Instalação cancelada antes de alterar a VM.")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = Path("/root/dominio-linux-backups") / stamp
        os.umask(0o077)
        install(manifest, backup)
    except (Exception, KeyboardInterrupt) as exc:
        print(f"\nInterrompido: {exc}\nSe a instalação já iniciou, preserve a saída e os backups. Não repita sobre um domínio parcial; restaure o snapshot da VM.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
