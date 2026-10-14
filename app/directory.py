# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
"""Conector LDAPS de leitura. Escritas reais serão implementadas por operação."""
import ssl

from ldap3 import BASE, NO_ATTRIBUTES, SUBTREE, Connection, Server, Tls
from ldap3.core import exceptions as ldap_errors

from .models import LdapCredentials


QUERIES = {
    "users": ("(&(objectCategory=person)(objectClass=user))", ["displayName", "sAMAccountName", "mail", "userAccountControl", "description"]),
    "groups": ("(objectClass=group)", ["name", "sAMAccountName", "member", "description"]),
    "ous": ("(objectClass=organizationalUnit)", ["ou", "description"]),
    "computers": ("(objectClass=computer)", ["name", "sAMAccountName", "operatingSystem", "userAccountControl", "description"]),
    "policies": ("(objectClass=groupPolicyContainer)", ["displayName", "name", "flags", "gPCFileSysPath"]),
}


def classify(exc):
    """Categoria do erro para o usuário e para o log. Nunca inclui a senha (o ldap3 não a coloca nas mensagens)."""
    text = f"{type(exc).__name__}: {exc}"
    if isinstance(exc, ssl.SSLError) or "certificate" in text.lower() or "CERTIFICATE_VERIFY" in text or "hostname" in text.lower():
        return "certificado", "O certificado LDAPS não foi validado. Confira a CA informada e use o nome do controlador como está no certificado (FQDN, não o IP)."
    if isinstance(exc, ldap_errors.LDAPBindError) or "invalidCredentials" in text:
        return "credenciais", "Usuário ou senha da conta de consulta recusados pelo controlador."
    if isinstance(exc, (ldap_errors.LDAPSocketOpenError, ldap_errors.LDAPSocketReceiveError, ldap_errors.LDAPSessionTerminatedByServerError, OSError)):
        return "conexao", "Sem conexão LDAPS com o controlador. Confira hostname, porta 636 e o firewall."
    if isinstance(exc, ValueError):
        return "dn", str(exc)
    return "outro", "Não foi possível consultar o Samba. Confira disponibilidade, permissões e certificado LDAPS."


class Directory:
    def __init__(self, credentials: LdapCredentials):
        self.credentials = credentials

    def connection(self):
        tls = Tls(validate=ssl.CERT_REQUIRED, ca_certs_data=self.credentials.ca_pem or None)
        server = Server(self.credentials.host, port=self.credentials.port, use_ssl=True, tls=tls, connect_timeout=8)
        return Connection(server, user=self.credentials.bind_dn, password=self.credentials.password, auto_bind=True, auto_referrals=False, read_only=True, raise_exceptions=True, receive_timeout=12)

    def discover(self):
        connection = self.connection()
        try:
            connection.search("", "(objectClass=*)", search_scope=BASE, attributes=["defaultNamingContext", "dnsHostName", "vendorName"])
            attrs = connection.response[0]["attributes"] if connection.response else {}
            value = attrs.get("defaultNamingContext", "")
            actual = value[0] if isinstance(value, list) and value else value
            if str(actual).casefold() != self.credentials.base_dn.casefold():
                raise ValueError("O DN informado não corresponde ao domínio apresentado pelo controlador.")
            return {"host": self.credentials.host, "base_dn": actual, "tls": "certificado validado", "access": "somente leitura"}
        finally:
            connection.unbind()

    def counts(self, kinds):
        """Totais por tipo numa ÚNICA conexão, sem trazer atributos (a visão geral só precisa dos números)."""
        connection = self.connection()
        try:
            totals = {}
            for kind in kinds:
                total = 0
                for entry in connection.extend.standard.paged_search(self.credentials.base_dn, QUERIES[kind][0], search_scope=SUBTREE,
                                                                      attributes=NO_ATTRIBUTES, paged_size=1000, generator=True):
                    if entry.get("type") == "searchResEntry":
                        total += 1
                totals[kind] = total
            return totals
        finally:
            connection.unbind()

    def records(self, kind):
        query, attributes = QUERIES[kind]
        connection = self.connection()
        try:
            entries = connection.extend.standard.paged_search(self.credentials.base_dn, query, search_scope=SUBTREE, attributes=attributes, paged_size=250, generator=True)
            items = []
            for entry in entries:
                if entry.get("type") != "searchResEntry":
                    continue
                attrs = entry["attributes"]

                def first(key, default=""):
                    value = attrs.get(key, default)
                    if isinstance(value, list):
                        return value[0] if value else default
                    return value

                dn = entry["dn"]
                item = {"id": dn, "dn": dn, "name": str(first("displayName") or first("name") or first("ou") or dn), "account": str(first("sAMAccountName")), "description": str(first("description")), "ou": dn.split(",", 1)[-1], "enabled": not (int(first("userAccountControl", 0)) & 2)}
                if kind == "users":
                    item["email"] = str(first("mail"))
                if kind == "groups":
                    item["members"] = attrs.get("member", [])
                if kind == "computers":
                    item.update(os=str(first("operatingSystem", "Não informado")), role="Não informado pelo diretório")
                if kind == "policies":
                    item.update(platform="Windows", policy_type="GPO existente", enabled=int(first("flags", 0)) != 3, sysvol=str(first("gPCFileSysPath")), settings={})
                items.append(item)
                if len(items) >= 10000:
                    raise ValueError("A consulta excedeu 10.000 objetos; consultas com filtro serão necessárias para este domínio.")
            return sorted(items, key=lambda item: item["name"].casefold())
        finally:
            connection.unbind()
