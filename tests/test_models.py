# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from pydantic import ValidationError

from app.models import DomainSpec


def test_dominio_valido(spec_data):
    spec = DomainSpec(**spec_data)
    assert spec.netbios == "EXEMPLO" and spec.hostname == "dc01"


def test_netbios_igual_ao_hostname_e_recusado(spec_data):
    # O samba-tool recusa o provisionamento nesse caso; o assistente precisa barrar antes.
    with pytest.raises(ValidationError, match="diferente do nome NetBIOS"):
        DomainSpec(**{**spec_data, "netbios": "CORP", "hostname": "corp"})


def test_sufixo_local_e_recusado(spec_data):
    with pytest.raises(ValidationError, match="mDNS"):
        DomainSpec(**{**spec_data, "fqdn": "empresa.local"})


def test_ip_fora_da_subrede_e_recusado(spec_data):
    with pytest.raises(ValidationError, match="pertencer à sub-rede"):
        DomainSpec(**{**spec_data, "address": "10.20.0.5"})


def test_encaminhador_igual_ao_controlador_e_recusado(spec_data):
    with pytest.raises(ValidationError, match="encaminhador"):
        DomainSpec(**{**spec_data, "forwarder": "10.10.10.10"})
