# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
# Precisa valer antes de importar app.main: o TrustedHost lê a lista na importação.
os.environ.setdefault("DL_ALLOWED_HOSTS", "testserver,127.0.0.1,localhost")
sys.path.insert(0, str(ROOT))

VALID = {"label": "Laboratório", "fqdn": "corp.exemplo.test", "netbios": "EXEMPLO", "hostname": "dc01",
         "address": "10.10.10.10", "subnet": "10.10.10.0/24", "forwarder": "1.1.1.1", "ntp_server": "pool.ntp.org",
         "distribution": "debian-13"}


@pytest.fixture
def spec_data():
    return dict(VALID)


@pytest.fixture
def installer(tmp_path):
    """O instalador como é entregue no ZIP: provision_dc.py ao lado de distributions.json."""
    from app.distributions import DISTRIBUTIONS
    shutil.copy(ROOT / "app" / "resources" / "provision_dc.py", tmp_path / "provision_dc.py")
    (tmp_path / "distributions.json").write_text(json.dumps(DISTRIBUTIONS))
    spec = importlib.util.spec_from_file_location("provision_dc_teste", tmp_path / "provision_dc.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DL_STATE_DIR", str(tmp_path / "state"))
    import app.main as main
    monkeypatch.setattr(main, "STATE", tmp_path / "state")
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        c.main = main
        c.state_dir = tmp_path / "state"
        yield c


@pytest.fixture
def logged(client):
    senha = (client.state_dir / "initial-password.txt").read_text().strip()
    r = client.post("/api/login", json={"username": "admin", "password": senha}, headers={"Origin": "http://testserver"})
    assert r.status_code == 200
    client.csrf = client.get("/api/session").json()["csrf"]
    client.escrita = {"Origin": "http://testserver", "X-CSRF-Token": client.csrf}
    return client
