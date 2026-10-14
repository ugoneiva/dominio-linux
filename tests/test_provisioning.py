# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
import io
import json
import zipfile

from app.distributions import DISTRIBUTIONS
from app.models import DomainSpec
from app.provisioning import package, plan


def test_todos_os_perfis_apt_trazem_samba_ad_provision():
    # No Ubuntu 24.04 ele é só Recommends do samba-ad-dc; sem ele o provision falha.
    for profile in DISTRIBUTIONS.values():
        if profile["installer_available"]:
            assert "samba-ad-provision" in profile["packages"], profile["id"]


def test_plano_e_pacote_nao_levam_senha(spec_data):
    spec = DomainSpec(**spec_data)
    # O plano só descreve que a senha será pedida NA VM; nenhum campo de senha viaja nele.
    assert not any("password" in chave or "senha" in chave for chave in plan(spec)["manifest"])
    with zipfile.ZipFile(io.BytesIO(package(spec))) as z:
        nomes = set(z.namelist())
        manifest = json.loads(z.read("manifest.json"))
    assert {"manifest.json", "LEIA-ME.txt", "plano.json", "distributions.json", "provision_dc.py", "LICENSE"} <= nomes
    assert not any("password" in chave or "senha" in chave for chave in manifest)


def test_perfil_sem_instalador_nao_leva_script(spec_data):
    spec = DomainSpec(**{**spec_data, "distribution": "rocky-9"})
    with zipfile.ZipFile(io.BytesIO(package(spec))) as z:
        assert "provision_dc.py" not in z.namelist()


def test_plano_anuncia_conferencia_auditoria_e_backup(spec_data):
    resultado = plan(DomainSpec(**spec_data))
    titulos = [passo["title"] for passo in resultado["steps"]]
    assert "Conferir o controlador" in titulos
    assert any("audit" in item for item in resultado["changes"])
    assert any("/var/backups/samba-ad" in item for item in resultado["changes"])
