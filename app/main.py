# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
from contextlib import asynccontextmanager
import ipaddress
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .auth import Auth
from .directory import Directory, QUERIES
from .distributions import DISTRIBUTIONS
from .models import DomainSpec, LdapCredentials, Login, Record
from .provisioning import package, plan
from .store import Store

ROOT = Path(__file__).resolve().parent
STATE = Path(os.environ.get("DL_STATE_DIR", str(ROOT.parent / ".state")))
KINDS = {"users", "groups", "ous", "computers", "dns", "policies", "shares"}
connections = {}
connections_lock = threading.RLock()


@asynccontextmanager
async def lifespan(app):
    app.state.store = Store(STATE)
    app.state.auth = Auth(app.state.store)
    yield
    with connections_lock:
        connections.clear()


app = FastAPI(title="Domínio Linux", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[host.strip() for host in os.environ.get("DL_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")])
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "templates")


@app.middleware("http")
async def security_headers(request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin", "")
        if not origin or urlsplit(origin).netloc != request.headers.get("host", ""):
            return JSONResponse({"detail": "Origem da operação não autorizada."}, status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "Origem da operação não autorizada."}, status_code=403)
        try:
            length = int(request.headers.get("content-length", "0") or "0")
        except ValueError:
            return JSONResponse({"detail": "Tamanho de solicitação inválido."}, status_code=400)
        if length < 0 or length > 65536:
            return JSONResponse({"detail": "A solicitação excede o tamanho permitido."}, status_code=413)
        # Também limitar corpos sem Content-Length. O Request cacheia o corpo
        # para que os modelos FastAPI consigam consumi-lo em seguida.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 65536:
                return JSONResponse({"detail": "A solicitação excede o tamanho permitido."}, status_code=413)
        request._body = bytes(body)
    response = await call_next(request)
    response.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "same-origin", "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'", "Cache-Control": "no-store"})
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Pydantic inclui a entrada inválida em errors(); senhas nunca retornam nela.
    errors = [{"field": ".".join(str(part) for part in error["loc"][1:]), "message": error["msg"]} for error in exc.errors()]
    return JSONResponse({"detail": errors}, status_code=422)


def session(request: Request):
    return request.app.state.auth.session(request)


def connection_for(session):
    with connections_lock:
        for key in list(connections):
            if connections[key][1] <= time.time():
                del connections[key]
        entry = connections.get(session["token_hash"])
    return entry[0] if entry else None


def writable(session):
    if connection_for(session):
        raise HTTPException(409, "O domínio conectado está em leitura nesta versão. Desconecte para editar o laboratório.")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    try:
        session(request)
    except HTTPException:
        return templates.TemplateResponse(request=request, name="login.html", context={})
    return templates.TemplateResponse(request=request, name="index.html", context={"version": "0.1.0"})


@app.get("/license", response_class=FileResponse)
def license_text():
    return FileResponse(ROOT / "resources" / "LICENSE", media_type="text/plain; charset=utf-8")


@app.post("/api/login")
def login(body: Login, request: Request):
    token = request.app.state.auth.login(body.username, body.password, request.client.host if request.client else "local")
    response = JSONResponse({"ok": True})
    response.set_cookie("dl_session", token, httponly=True, samesite="strict", secure=os.environ.get("DL_SECURE_COOKIE") == "1", max_age=8 * 3600)
    return response


@app.post("/api/logout")
def logout(request: Request, s=Depends(session)):
    with connections_lock:
        connections.pop(s["token_hash"], None)
    request.app.state.auth.logout(request)
    response = JSONResponse({"ok": True})
    response.delete_cookie("dl_session")
    return response


@app.get("/api/session")
def session_info(request: Request, s=Depends(session)):
    credentials = connection_for(s)
    return {"actor": s["actor"], "csrf": s["csrf"], "mode": "ldaps" if credentials else "laboratorio", "connection": {"host": credentials.host, "base_dn": credentials.base_dn} if credentials else None, "version": "0.1.0"}


def list_records(request, s, kind):
    if kind not in KINDS:
        raise HTTPException(404, "Módulo não encontrado.")
    credentials = connection_for(s)
    if credentials:
        if kind not in QUERIES:
            raise HTTPException(501, "Este módulo ainda não possui integração de leitura com o domínio real.")
        try:
            return Directory(credentials).records(kind)
        except Exception:
            raise HTTPException(502, "Não foi possível consultar o Samba. Confira disponibilidade, permissões e certificado LDAPS.") from None
    return request.app.state.store.records(kind)


@app.get("/api/overview")
def overview(request: Request, s=Depends(session)):
    credentials = connection_for(s)
    if credentials:
        domain = {"label": "Domínio Samba conectado", "fqdn": ".".join(part[3:] for part in credentials.base_dn.split(",")), "hostname": credentials.host, "distribution": "Linux — versão não consultada"}
        counts = {kind: len(list_records(request, s, kind)) for kind in ("users", "groups", "ous", "computers", "policies")}
    else:
        domain = request.app.state.store.get_config("domain")
        counts = {kind: len(request.app.state.store.records(kind)) for kind in KINDS}
    return {"domain": domain, "counts": counts, "mode": "ldaps" if credentials else "laboratorio", "audit": request.app.state.store.history(6), "services": [{"name": name, "status": "Não consultado"} for name in ("Samba AD DC", "DNS do domínio", "Kerberos", "Sincronização de horário", "Replicação entre DCs", "Backup do domínio")]}


@app.get("/api/records/{kind}")
def records(kind: str, request: Request, s=Depends(session)):
    return {"items": list_records(request, s, kind), "mode": "ldaps" if connection_for(s) else "laboratorio"}


def validate_record(store, kind, data, record_id=None):
    if kind not in KINDS:
        raise HTTPException(404, "Módulo não encontrado.")
    if kind == "users" and not data["account"]:
        raise HTTPException(422, "Informe o nome de login do usuário.")
    if kind == "dns" and not data["value"]:
        raise HTTPException(422, "Informe o destino ou conteúdo do registro DNS.")
    if kind == "dns" and data["record_type"] in {"A", "AAAA"}:
        try:
            address = ipaddress.ip_address(data["value"])
            if address.version != (4 if data["record_type"] == "A" else 6):
                raise ValueError()
        except ValueError:
            raise HTTPException(422, "O endereço precisa corresponder ao tipo do registro DNS.") from None
    ous = store.records("ous")
    ou_names = {item["name"] for item in ous}
    if kind != "dns" and data["ou"] and data["ou"] not in ou_names:
        raise HTTPException(422, "A unidade organizacional selecionada não existe.")
    if kind == "ous":
        parents = {item["name"]: item.get("ou", "") for item in ous if item["id"] != record_id}
        parents[data["name"]] = data["ou"]
        seen = set()
        current = data["name"]
        while current:
            if current in seen:
                raise HTTPException(422, "A hierarquia de OUs não pode conter ciclos.")
            seen.add(current)
            current = parents.get(current, "")
        previous = store.get(kind, record_id) if record_id else None
        if previous and previous["name"] != data["name"]:
            if any(item.get("ou") == previous["name"] for category in KINDS for item in store.records(category)):
                raise HTTPException(409, "Esta OU tem objetos associados. Movimente-os antes de renomeá-la nesta versão.")
    if kind in {"groups", "shares"}:
        allowed = {item["id"] for item in store.records("users" if kind == "groups" else "groups")}
        if not set(data["members"]).issubset(allowed):
            raise HTTPException(422, "Um dos membros selecionados não existe.")
    if kind == "policies":
        allowed = {"registry", "linux-sudo", "linux-ssh"}
        if data["policy_type"] not in allowed:
            raise HTTPException(422, "O tipo de política não faz parte do catálogo inicial.")
        if (data["platform"] == "Windows") != (data["policy_type"] == "registry"):
            raise HTTPException(422, "O tipo da política não corresponde à plataforma.")
        if len(json.dumps(data["settings"])) > 16000:
            raise HTTPException(422, "As configurações da política excedem o tamanho permitido.")


@app.post("/api/records/{kind}", status_code=201)
def create_record(kind: str, body: Record, request: Request, s=Depends(session)):
    writable(s)
    data = body.model_dump()
    validate_record(request.app.state.store, kind, data)
    try:
        return request.app.state.store.write(kind, data, s["actor"])
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Já existe um objeto com este nome ou login neste módulo.") from None


@app.put("/api/records/{kind}/{record_id}")
def update_record(kind: str, record_id: str, body: Record, request: Request, s=Depends(session)):
    writable(s)
    store = request.app.state.store
    if not store.get(kind, record_id):
        raise HTTPException(404, "Objeto não encontrado.")
    data = body.model_dump()
    validate_record(store, kind, data, record_id)
    try:
        return store.write(kind, data, s["actor"], record_id)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Já existe um objeto com este nome ou login neste módulo.") from None


@app.delete("/api/records/{kind}/{record_id}")
def delete_record(kind: str, record_id: str, request: Request, s=Depends(session)):
    writable(s)
    if kind not in KINDS:
        raise HTTPException(404, "Módulo não encontrado.")
    store = request.app.state.store
    record = store.get(kind, record_id)
    if not record:
        raise HTTPException(404, "Objeto não encontrado.")
    if kind == "ous" and any(item.get("ou") == record["name"] for category in KINDS for item in store.records(category)):
        raise HTTPException(409, "Movimente os objetos associados antes de excluir esta OU.")
    if kind in {"users", "groups"}:
        related_kind = "groups" if kind == "users" else "shares"
        if any(record_id in item.get("members", []) for item in store.records(related_kind)):
            raise HTTPException(409, "Remova as associações deste objeto antes de excluí-lo.")
    store.delete(kind, record_id, s["actor"])
    return {"ok": True}


@app.get("/api/distributions")
def distributions(s=Depends(session)):
    return {"items": list(DISTRIBUTIONS.values())}


@app.get("/api/domain")
def domain(request: Request, s=Depends(session)):
    return request.app.state.store.get_config("domain")


@app.post("/api/domain/plan")
def domain_plan(body: DomainSpec, request: Request, s=Depends(session)):
    return plan(body)


@app.put("/api/domain")
def save_domain(body: DomainSpec, request: Request, s=Depends(session)):
    writable(s)
    store = request.app.state.store
    previous = store.get_config("domain")
    store.set_config("domain", body.model_dump())
    store.audit(s["actor"], "salvar plano", "domínio Linux", previous, body.model_dump())
    return {"ok": True, "state": "plano; não executado"}


@app.post("/api/domain/package")
def domain_package(body: DomainSpec, request: Request, s=Depends(session)):
    payload = package(body)
    request.app.state.store.audit(s["actor"], "gerar pacote", body.fqdn, after={"manifest": body.model_dump(), "digest": plan(body)["digest"]}, mode="plano")
    return Response(payload, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="dominio-linux-{body.netbios.lower()}-{body.distribution}.zip"'})


@app.get("/api/audit")
def audit(request: Request, s=Depends(session)):
    return {"items": request.app.state.store.history()}


@app.post("/api/integration/connect")
def connect(body: LdapCredentials, request: Request, s=Depends(session)):
    try:
        result = Directory(body).discover()
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except Exception:
        raise HTTPException(502, "Não foi possível conectar. Confira hostname, DN, credenciais, acesso LDAPS e cadeia do certificado.") from None
    with connections_lock:
        connections[s["token_hash"]] = (body, s["expires"])
    request.app.state.store.audit(s["actor"], "conectar leitura", body.host, after={"base_dn": body.base_dn, "tls": "validado"}, mode="ldaps")
    return result


@app.post("/api/integration/disconnect")
def disconnect(request: Request, s=Depends(session)):
    with connections_lock:
        connections.pop(s["token_hash"], None)
    request.app.state.store.audit(s["actor"], "desconectar", "LDAPS", mode="ldaps")
    return {"ok": True}
