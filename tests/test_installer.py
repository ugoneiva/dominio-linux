# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
import pytest


def test_manifesto_valido(installer, spec_data):
    assert installer.valid_manifest(dict(spec_data))["hostname"] == "dc01"


def test_manifesto_recusa_netbios_igual_hostname(installer, spec_data):
    with pytest.raises(ValueError, match="NetBIOS"):
        installer.valid_manifest({**spec_data, "netbios": "DC01"})


def test_manifesto_recusa_campo_a_mais(installer, spec_data):
    with pytest.raises(ValueError, match="campos"):
        installer.valid_manifest({**spec_data, "password": "x"})


def test_auditoria_json_entra_no_global(installer, tmp_path):
    conf = tmp_path / "smb.conf"
    conf.write_text("# Global parameters\n[global]\n\tnetbios name = DC01\n\trealm = CORP.EXEMPLO.TEST\n\n[sysvol]\n\tpath = /var/lib/samba/sysvol\n")
    rot = tmp_path / "logrotate"
    assert installer.enable_audit(tmp_path, conf=conf, logrotate=rot) is True
    texto = conf.read_text()
    globais = texto.split("[sysvol]")[0]
    assert "auth_json_audit:3@/var/log/samba/audit-auth.json" in globais
    assert "dsdb_group_json_audit:5@/var/log/samba/audit-group.json" in globais
    assert (tmp_path / "smb.conf-provisionado").exists() and "rotate 14" in rot.read_text()


def test_auditoria_nao_sobrescreve_log_level_existente(installer, tmp_path):
    conf = tmp_path / "smb.conf"
    conf.write_text("[global]\n\tlog level = 3\n")
    assert installer.enable_audit(tmp_path, conf=conf, logrotate=tmp_path / "lr") is False
    assert conf.read_text().count("log level") == 1
