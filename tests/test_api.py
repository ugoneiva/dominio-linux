# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
import ssl

from ldap3.core.exceptions import LDAPBindError, LDAPSocketOpenError

from app.directory import classify
from app.models import LdapCredentials


def test_login_exige_origem(client):
    senha = (client.state_dir / "initial-password.txt").read_text().strip()
    assert client.post("/api/login", json={"username": "admin", "password": senha}).status_code == 403


def test_escrita_exige_csrf(logged):
    corpo = {"name": "Teste", "account": "teste"}
    assert logged.post("/api/records/users", json=corpo, headers={"Origin": "http://testserver"}).status_code == 403
    assert logged.post("/api/records/users", json=corpo, headers=logged.escrita).status_code == 201


def test_corpo_grande_recusado_com_e_sem_content_length(logged):
    grande = b'{"name":"' + b"x" * 70000 + b'"}'
    r = logged.post("/api/records/users", content=grande, headers={**logged.escrita, "Content-Type": "application/json"})
    assert r.status_code == 413

    def pedacos():
        for _ in range(20):
            yield b"x" * 5000
    r = logged.post("/api/records/users", content=pedacos(), headers={**logged.escrita, "Content-Type": "application/json"})
    assert r.status_code == 413


def test_corpo_normal_continua_chegando_a_aplicacao(logged):
    r = logged.post("/api/records/dns", json={"name": "web", "record_type": "A", "value": "10.10.10.30"}, headers=logged.escrita)
    assert r.status_code == 201 and r.json()["value"] == "10.10.10.30"


def test_classificacao_de_erros_ldap():
    assert classify(ssl.SSLCertVerificationError("certificate verify failed"))[0] == "certificado"
    assert classify(LDAPBindError("invalidCredentials"))[0] == "credenciais"
    assert classify(LDAPSocketOpenError("socket connection error"))[0] == "conexao"
    assert classify(ValueError("O DN informado não corresponde"))[0] == "dn"


def test_visao_geral_conectada_usa_cache(logged, monkeypatch):
    chamadas = []

    def falsa_contagem(self, kinds):
        chamadas.append(kinds)
        return {kind: 7 for kind in kinds}

    monkeypatch.setattr("app.directory.Directory.counts", falsa_contagem)
    credenciais = LdapCredentials(host="dc01.corp.exemplo.test", bind_dn="consulta@corp.exemplo.test", password="x",
                                  base_dn="DC=corp,DC=exemplo,DC=test")
    sessao = logged.main.app.state.auth
    token_hash = sessao.token_hash(logged.cookies.get("dl_session"))
    import time
    logged.main.connections[token_hash] = (credenciais, time.time() + 600)
    for _ in range(3):
        dados = logged.get("/api/overview").json()
        assert dados["counts"]["users"] == 7 and dados["mode"] == "ldaps"
    assert len(chamadas) == 1, "a visão geral deveria consultar o diretório uma vez e reaproveitar"
