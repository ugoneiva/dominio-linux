# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import time

from fastapi import HTTPException, Request


class Auth:
    def __init__(self, store):
        self.store = store
        self.attempts = {}
        if not store.get_config("admin_hash"):
            password = secrets.token_urlsafe(24)
            salt = secrets.token_hex(16)
            digest = self.hash_password(password, salt)
            store.set_config("admin_hash", {"salt": salt, "digest": digest})
            path = store.directory / "initial-password.txt"
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(password + "\n")
            print(f"Domínio Linux: usuário admin; senha inicial em {path}", flush=True)

    @staticmethod
    def hash_password(password, salt):
        return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000).hex()

    def login(self, username, password, client):
        now = time.time()
        self.attempts = {key: value for key, value in self.attempts.items() if now - value[0] < 300}
        count = self.attempts.get(client, (now, 0))[1]
        if count >= 8:
            raise HTTPException(429, "Aguarde alguns minutos antes de tentar novamente.")
        self.attempts[client] = (now, count + 1)
        saved = self.store.get_config("admin_hash")
        matches = hmac.compare_digest(self.hash_password(password, saved["salt"]), saved["digest"])
        if username != "admin" or not matches:
            raise HTTPException(401, "Usuário ou senha inválidos.")
        self.attempts.pop(client, None)
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        with self.store.db() as db:
            db.execute("DELETE FROM sessions WHERE expires < ?", (now,))
            db.execute("INSERT INTO sessions VALUES (?,?,?,?)", (self.token_hash(token), csrf, now + 8 * 3600, "admin"))
        self.store.audit("admin", "entrar", "painel")
        return token

    @staticmethod
    def token_hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def session(self, request: Request):
        token = request.cookies.get("dl_session", "")
        with self.store.db() as db:
            row = db.execute("SELECT * FROM sessions WHERE token_hash=? AND expires>?", (self.token_hash(token), time.time())).fetchone()
        if not row:
            raise HTTPException(401, "Entre novamente no painel.")
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            supplied = request.headers.get("X-CSRF-Token", "")
            if not hmac.compare_digest(supplied, row["csrf"]):
                raise HTTPException(403, "A sessão precisa ser atualizada antes desta alteração.")
        return dict(row)

    def logout(self, request):
        token = request.cookies.get("dl_session", "")
        with self.store.db() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (self.token_hash(token),))
