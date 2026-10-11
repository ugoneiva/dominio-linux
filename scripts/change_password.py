#!/usr/bin/env python3
# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
"""Alterar a senha do administrador local do painel; não altera senha do domínio."""
import getpass
import os
from pathlib import Path
import secrets

from app.auth import Auth
from app.store import Store


def main():
    directory = Path(os.environ.get("DL_STATE_DIR", str(Path(__file__).resolve().parents[1] / ".state")))
    if not (directory / "domain.sqlite3").is_file():
        raise SystemExit("Inicialize o painel antes de alterar a senha.")
    store = Store(directory)
    auth = Auth(store)
    current = getpass.getpass("Senha atual do administrador local: ")
    saved = store.get_config("admin_hash")
    import hmac
    if not hmac.compare_digest(auth.hash_password(current, saved["salt"]), saved["digest"]):
        raise SystemExit("Senha atual incorreta.")
    password = getpass.getpass("Nova senha (mínimo 12 caracteres): ")
    repeated = getpass.getpass("Repita a nova senha: ")
    if password != repeated or len(password) < 12:
        raise SystemExit("As senhas precisam coincidir e ter pelo menos 12 caracteres.")
    salt = secrets.token_hex(16)
    with store.db() as db:
        import json
        db.execute("UPDATE config SET value=? WHERE key='admin_hash'", (json.dumps({"salt": salt, "digest": auth.hash_password(password, salt)}),))
        db.execute("DELETE FROM sessions")
        store._audit(db, "admin", "alterar senha local", "painel", None, {"sessions": "revogadas"})
    initial = directory / "initial-password.txt"
    if initial.exists():
        initial.unlink()
    print("Senha local alterada. Sessões revogadas. Entre novamente no painel.")


if __name__ == "__main__":
    main()
