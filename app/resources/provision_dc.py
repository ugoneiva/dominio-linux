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
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import ssl
import subprocess
import sys
import time

TLS_DIR = Path("/var/lib/samba/private/tls")
BACKUP_DIR = Path("/var/backups/samba-ad")
AUDIT_LOGS = {
    # classe de debug do Samba -> (nível, arquivo). Sintaxe "classe:nível@arquivo" existe desde o Samba 4.13.
    "auth_json_audit": (3, "/var/log/samba/audit-auth.json"),
    "dsdb_json_audit": (5, "/var/log/samba/audit-dsdb.json"),
    "dsdb_password_json_audit": (5, "/var/log/samba/audit-password.json"),
    "dsdb_group_json_audit": (5, "/var/log/samba/audit-group.json"),
}


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
    if manifest["hostname"].upper() == manifest["netbios"].upper():
        raise ValueError("O hostname precisa ser diferente do nome NetBIOS do domínio (o samba-tool recusa).")
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


def enable_audit(backup, conf=Path("/etc/samba/smb.conf"), logrotate=Path("/etc/logrotate.d/dominio-linux-samba-audit")):
    """Trilha de auditoria em JSON: autenticações, alterações no diretório, senhas e grupos.

    É o que um SIEM (Wazuh, por exemplo) precisa para ver logins e mudanças de privilégio no
    domínio desde o primeiro dia. Cada classe vai para um arquivo próprio, com rotação diária.
    """
    shutil.copy2(conf, backup / "smb.conf-provisionado")
    text = conf.read_text()
    if re.search(r"(?im)^\s*log level\s*=", text):
        print("Aviso: smb.conf já define 'log level'; auditoria JSON não alterada.", flush=True)
        return False
    level = "1 " + " ".join(f"{name}:{lvl}@{path}" for name, (lvl, path) in AUDIT_LOGS.items())
    block = ("\t# dominio-linux: auditoria JSON (autenticação, diretório, senhas, grupos) para SIEM\n"
             f"\tlog level = {level}\n\tdebug hires timestamp = yes\n")
    text, count = re.subn(r"(?im)^(\[global\][^\n]*\n)", lambda m: m.group(1) + block, text, count=1)
    if not count:
        raise RuntimeError("Seção [global] não encontrada no smb.conf gerado pelo provisionamento.")
    write_file(conf, text)
    write_file(logrotate, "/var/log/samba/audit-*.json {\n    daily\n    rotate 14\n"
               "    compress\n    delaycompress\n    missingok\n    notifempty\n    copytruncate\n}\n")
    return True


def schedule_backup():
    """Backup diário do diretório com `samba-tool domain backup offline`.

    O modo offline roda no próprio DC, com o serviço no ar (trava os bancos durante a cópia) e sem
    credencial: nenhuma senha fica gravada em disco. O arquivo contém segredos do domínio (chaves do
    krbtgt), por isso o diretório é root 0700 — copie-o para fora do servidor.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.chmod(0o700)
    write_file("/etc/systemd/system/dominio-linux-backup.service",
               "[Unit]\nDescription=Backup offline do Samba AD (dominio-linux)\nAfter=samba-ad-dc.service\n\n"
               "[Service]\nType=oneshot\nUMask=0077\n"
               f"ExecStart=/usr/bin/samba-tool domain backup offline --targetdir={BACKUP_DIR}\n"
               f"ExecStartPost=/usr/bin/find {BACKUP_DIR} -name samba-backup-*.tar.bz2 -mtime +14 -delete\n")
    write_file("/etc/systemd/system/dominio-linux-backup.timer",
               "[Unit]\nDescription=Backup diário do Samba AD (dominio-linux)\n\n"
               "[Timer]\nOnCalendar=*-*-* 02:30\nRandomizedDelaySec=15m\nPersistent=true\n\n"
               "[Install]\nWantedBy=timers.target\n")
    run("systemctl", "daemon-reload")
    run("systemctl", "enable", "--now", "dominio-linux-backup.timer")


def wait_ports(ports, limit=120):
    """O systemd diz "active" antes de o Samba abrir as portas; esperar por elas de verdade."""
    deadline = time.time() + limit
    missing = set(ports)
    while missing and time.time() < deadline:
        out = subprocess.run(["ss", "-Hltn"], capture_output=True, text=True).stdout
        open_ports = {int(m.group(1)) for m in re.finditer(r":(\d+)\s", out)}
        missing = {port for port in ports if port not in open_ports}
        if missing:
            time.sleep(3)
    return sorted(missing)


def ldaps_ca(manifest, limit=90):
    """CA autoassinada que o Samba gera no primeiro início, e o teste de que o painel conseguirá usá-la.

    A tela Integração Samba exige certificado validado e o nome do servidor como está no certificado
    (FQDN do DC, não o IP). Sem esta informação a primeira conexão do painel falha.
    """
    ca = TLS_DIR / "ca.pem"
    deadline = time.time() + limit
    while not ca.exists() and time.time() < deadline:
        time.sleep(3)
    if not ca.exists():
        return {"ok": False, "detail": f"{ca} não foi gerado; confira 'tls enabled' no smb.conf"}
    pem = ca.read_text()
    der = ssl.PEM_cert_to_DER_cert(pem)
    fqdn = f"{manifest['hostname']}.{manifest['fqdn']}"
    info = {"ok": False, "path": str(ca), "pem": pem, "sha256": hashlib.sha256(der).hexdigest(), "host": fqdn}
    try:
        context = ssl.create_default_context(cadata=pem)
        with socket.create_connection((manifest["address"], 636), timeout=10) as raw:
            with context.wrap_socket(raw, server_hostname=fqdn):
                info["ok"] = True
                info["detail"] = f"LDAPS validado com a CA do Samba e o nome {fqdn}"
    except (OSError, ssl.SSLError) as exc:
        info["detail"] = f"LDAPS não validou com a CA e o nome {fqdn}: {exc}"
    return info


def check(name, ok, detail, critical=True):
    mark = "OK  " if ok else ("FALHA" if critical else "AVISO")
    print(f"  [{mark}] {name}: {detail}", flush=True)
    return {"check": name, "ok": bool(ok), "critical": critical, "detail": detail}


def verify(manifest, backup):
    """Conferência final. Não lança: o domínio já existe; o resultado diz o que falta."""
    fqdn, host = manifest["fqdn"], f"{manifest['hostname']}.{manifest['fqdn']}"

    def out(*args, timeout=120):
        try:
            r = subprocess.run(list(args), capture_output=True, text=True, timeout=timeout)
            return r.returncode, r.stdout + r.stderr
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 1, str(exc)

    print("\nConferência final do controlador:", flush=True)
    results = []
    code, text = out("systemctl", "is-active", "samba-ad-dc")
    results.append(check("serviço samba-ad-dc", code == 0, text.strip()))
    missing = wait_ports([53, 88, 389, 445, 636])
    results.append(check("portas DNS/Kerberos/LDAP/SMB/LDAPS", not missing,
                         "53, 88, 389, 445 e 636 ouvindo" if not missing else f"sem resposta: {missing}"))
    for record, label in ((f"_ldap._tcp.{fqdn}", "SRV LDAP"), (f"_kerberos._udp.{fqdn}", "SRV Kerberos")):
        code, text = out("host", "-t", "SRV", record, manifest["address"])
        results.append(check(f"DNS {label}", code == 0 and "has SRV record" in text, record))
    code, text = out("host", "-t", "A", host, manifest["address"])
    results.append(check("DNS do controlador", code == 0 and manifest["address"] in text, f"{host} → {manifest['address']}"))
    code, text = out("smbclient", "-L", "localhost", "-N")
    has_shares = "sysvol" in text.lower() and "netlogon" in text.lower()
    results.append(check("compartilhamentos sysvol/netlogon", has_shares, "listados" if has_shares else text.strip()[-200:]))
    code, text = out("samba-tool", "dbcheck", "--cross-ncs", timeout=600)
    results.append(check("samba-tool dbcheck", code == 0, (text.strip().splitlines() or ["sem saída"])[-1]))
    code, text = out("chronyc", "-n", "tracking")
    synced = code == 0 and "Not synchronised" not in text
    results.append(check("horário (chrony)", synced, "sincronizado" if synced else "ainda sem sincronizar — Kerberos exige horário correto", critical=False))
    ntp_signd = Path("/var/lib/samba/ntp_signd/socket").exists()
    results.append(check("assinatura de horário para Windows (ntp_signd)", ntp_signd, "socket presente" if ntp_signd else "socket ausente", critical=False))
    ca = ldaps_ca(manifest)
    results.append(check("LDAPS para o painel", ca["ok"], ca["detail"]))
    if ca.get("pem"):
        shutil.copy2(ca["path"], backup / "samba-ldaps-ca.pem")
    code, text = out("systemctl", "start", "dominio-linux-backup.service", timeout=900)
    copies = sorted(BACKUP_DIR.glob("samba-backup-*.tar.bz2"))
    results.append(check("primeiro backup do domínio", code == 0 and bool(copies), str(copies[-1]) if copies else text.strip()[-200:]))
    for name, (_, path) in AUDIT_LOGS.items():
        if name == "auth_json_audit":
            results.append(check("auditoria JSON", Path(path).exists(), path if Path(path).exists() else f"{path} ainda não criado (surge no primeiro login)", critical=False))
    return results, ca


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
    audit = enable_audit(backup)
    run("systemctl", "unmask", "samba-ad-dc")
    run("systemctl", "enable", "--now", "samba-ad-dc")
    run("systemctl", "restart", "chrony")
    schedule_backup()
    checks, ca = verify(manifest, backup)
    failed = [item["check"] for item in checks if item["critical"] and not item["ok"]]
    result = {"completed_at": datetime.now(timezone.utc).isoformat(), "fqdn": manifest["fqdn"], "controller": manifest["hostname"],
              "address": manifest["address"], "backup_directory": str(backup), "checks": checks,
              "ldaps": {key: ca.get(key) for key in ("host", "path", "sha256", "ok")}, "audit_json": audit,
              "state": "provisionamento concluído e conferido; ingresso de clientes pendente" if not failed
              else "provisionamento concluído com falhas na conferência: " + ", ".join(failed)}
    (backup / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    fqdn = f"{manifest['hostname']}.{manifest['fqdn']}"
    print(f"\nControlador Samba criado em Linux: {fqdn}\nDNS dos membros: {manifest['address']}\nBackup dos arquivos anteriores: {backup}")
    if failed:
        print("\nATENÇÃO — itens da conferência que falharam: " + ", ".join(failed) + f"\nDetalhes em {backup}/result.json. Corrija antes de ingressar máquinas.")
    if ca.get("pem"):
        print(f"\nPara a tela Integração Samba do painel:\n  Hostname do controlador: {fqdn}   (use o nome, não o IP — o certificado é emitido para ele)\n"
              f"  DN do domínio: {','.join('DC=' + part for part in manifest['fqdn'].split('.'))}\n"
              f"  Certificado da CA: {ca['path']} (cópia em {backup}/samba-ldaps-ca.pem)\n"
              f"  SHA-256 da CA: {ca['sha256']}\n  Cole o conteúdo abaixo no campo 'Certificado da CA':\n\n{ca['pem']}")
    print(f"Backup diário do domínio: {BACKUP_DIR} (timer dominio-linux-backup.timer, 02:30, 14 dias). Copie para fora do servidor.")
    if audit:
        print("Auditoria JSON: /var/log/samba/audit-*.json (rotação diária, 14 dias) — pronta para coleta por um SIEM.")
    print("Libere as portas de domínio na rede e valide ingresso, políticas e recuperação antes de produção.")


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
