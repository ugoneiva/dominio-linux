# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
"""Persistência local do laboratório e da auditoria. Não replica a identidade real."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
        self.path = directory / "domain.sqlite3"
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS records_kind ON records(kind);
            CREATE UNIQUE INDEX IF NOT EXISTS records_name ON records(kind, lower(json_extract(data,'$.name')));
            CREATE UNIQUE INDEX IF NOT EXISTS records_account ON records(kind, lower(json_extract(data,'$.account')))
                WHERE json_extract(data,'$.account') IS NOT NULL AND json_extract(data,'$.account') != '';
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
                actor TEXT NOT NULL, operation TEXT NOT NULL, target TEXT NOT NULL,
                before_json TEXT, after_json TEXT, mode TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY, csrf TEXT NOT NULL, expires REAL NOT NULL,
                actor TEXT NOT NULL
            );
            """)
        self.path.chmod(0o600)
        if not self.get_config("initialized"):
            self.seed()

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_config(self, key, default=None):
        with self.db() as db:
            row = db.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_config(self, key, value):
        with self.db() as db:
            db.execute("INSERT INTO config VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value)))

    def records(self, kind):
        with self.db() as db:
            rows = db.execute("SELECT * FROM records WHERE kind=? ORDER BY updated_at DESC", (kind,)).fetchall()
        return [{"id": row["id"], **json.loads(row["data"]), "updated_at": row["updated_at"]} for row in rows]

    def get(self, kind, record_id):
        with self.db() as db:
            row = db.execute("SELECT * FROM records WHERE id=? AND kind=?", (record_id, kind)).fetchone()
        return {"id": row["id"], **json.loads(row["data"])} if row else None

    def write(self, kind, data, actor, record_id=None):
        record_id = record_id or str(uuid4())
        stamp = now()
        with self.db() as db:
            previous = db.execute("SELECT data FROM records WHERE id=? AND kind=?", (record_id, kind)).fetchone()
            before = json.loads(previous[0]) if previous else None
            db.execute("INSERT INTO records VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at", (record_id, kind, json.dumps(data), stamp))
            self._audit(db, actor, "atualizar" if before else "criar", f"{kind}/{record_id}", before, data)
        return {"id": record_id, **data, "updated_at": stamp}

    def delete(self, kind, record_id, actor):
        with self.db() as db:
            row = db.execute("SELECT data FROM records WHERE id=? AND kind=?", (record_id, kind)).fetchone()
            if not row:
                return False
            before = json.loads(row[0])
            db.execute("DELETE FROM records WHERE id=? AND kind=?", (record_id, kind))
            self._audit(db, actor, "excluir", f"{kind}/{record_id}", before, None)
        return True

    def _audit(self, db, actor, operation, target, before, after, mode="laboratorio"):
        db.execute("INSERT INTO audit(created_at,actor,operation,target,before_json,after_json,mode) VALUES (?,?,?,?,?,?,?)", (now(), actor, operation, target, json.dumps(before), json.dumps(after), mode))

    def audit(self, actor, operation, target, before=None, after=None, mode="laboratorio"):
        with self.db() as db:
            self._audit(db, actor, operation, target, before, after, mode)

    def history(self, limit=200):
        with self.db() as db:
            rows = db.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def seed(self):
        self.set_config("domain", {"label": "Laboratório de demonstração", "fqdn": "corp.exemplo.test", "netbios": "EXEMPLO", "hostname": "dc01", "address": "10.10.10.10", "subnet": "10.10.10.0/24", "forwarder": "1.1.1.1", "ntp_server": "pool.ntp.org", "distribution": "debian-13"})
        for name, parent in [("Pessoas", ""), ("Tecnologia", "Pessoas"), ("Financeiro", "Pessoas"), ("Estações", ""), ("Servidores", "")]:
            self.write("ous", {"name": name, "ou": parent, "description": "Estrutura de exemplo"}, "sistema")
        people = [("Ana Oliveira", "ana.oliveira", "Financeiro"), ("Lucas Martins", "lucas.martins", "Tecnologia"), ("Marina Costa", "marina.costa", "Tecnologia")]
        user_ids = []
        for name, account, ou in people:
            item = self.write("users", {"name": name, "account": account, "email": f"{account}@exemplo.test", "ou": ou, "description": "Usuário fictício", "enabled": True}, "sistema")
            user_ids.append(item["id"])
        self.write("groups", {"name": "Equipe de tecnologia", "account": "equipe-ti", "description": "Grupo de exemplo", "members": user_ids[1:], "ou": "Tecnologia"}, "sistema")
        self.write("groups", {"name": "Equipe financeira", "account": "equipe-financeiro", "description": "Grupo de exemplo", "members": user_ids[:1], "ou": "Financeiro"}, "sistema")
        for name, system, role, ou in [("WKS-FIN-01", "Windows 11 Pro", "workstation", "Estações"), ("WKS-TI-01", "Debian 13", "workstation", "Estações"), ("SRV-ARQ-01", "Debian 13", "server", "Servidores")]:
            self.write("computers", {"name": name, "os": system, "role": role, "ou": ou, "enabled": True, "description": "Máquina fictícia; não ingressada em um domínio real"}, "sistema")
        self.write("dns", {"name": "arquivos", "record_type": "A", "value": "10.10.10.20", "ttl": 3600, "priority": 10}, "sistema")
        self.write("policies", {"name": "Tela bloqueada — estações", "platform": "Windows", "policy_type": "registry", "ou": "Estações", "enabled": True, "settings": {"timeout_seconds": 600}, "description": "Rascunho de política; sem publicação no SYSVOL"}, "sistema")
        self.set_config("initialized", True)
