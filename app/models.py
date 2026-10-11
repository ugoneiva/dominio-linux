# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
import ipaddress
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .distributions import DISTRIBUTIONS


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(StrictModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class DomainSpec(StrictModel):
    label: str = Field(min_length=2, max_length=80)
    fqdn: str = Field(min_length=4, max_length=200)
    netbios: str = Field(min_length=1, max_length=15)
    hostname: str = Field(min_length=1, max_length=15)
    address: str
    subnet: str
    forwarder: str
    ntp_server: str = "pool.ntp.org"
    distribution: str = Field(default="debian-13", max_length=40)

    @field_validator("distribution")
    @classmethod
    def valid_distribution(cls, value):
        if value not in DISTRIBUTIONS:
            raise ValueError("Escolha uma das distribuições disponíveis no assistente.")
        return value

    @field_validator("fqdn", "ntp_server")
    @classmethod
    def valid_fqdn(cls, value):
        value = value.lower().rstrip(".")
        labels = value.split(".")
        if len(labels) < 2 or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", part) for part in labels):
            raise ValueError("Informe um nome DNS completo válido.")
        if value.endswith(".local"):
            raise ValueError("Utilize um subdomínio DNS controlado ou .test no laboratório; .local conflita com mDNS.")
        return value

    @field_validator("netbios", "hostname")
    @classmethod
    def valid_short_name(cls, value, info):
        if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9-]{0,14}", value) or value.endswith("-"):
            raise ValueError("Use até 15 caracteres: letras, números e hífen, começando por letra.")
        return value.upper() if info.field_name == "netbios" else value.lower()

    @field_validator("address", "forwarder")
    @classmethod
    def valid_address(cls, value):
        addr = ipaddress.IPv4Address(value)
        if addr.is_loopback or addr.is_multicast or addr.is_unspecified or addr.is_link_local:
            raise ValueError("Informe um endereço IPv4 de rede válido.")
        return str(addr)

    @field_validator("subnet")
    @classmethod
    def valid_subnet(cls, value):
        return str(ipaddress.IPv4Network(value, strict=True))

    @model_validator(mode="after")
    def consistent_network(self):
        network = ipaddress.IPv4Network(self.subnet)
        address = ipaddress.IPv4Address(self.address)
        if address not in network or address in (network.network_address, network.broadcast_address):
            raise ValueError("O IP do controlador precisa pertencer à sub-rede e ser um endereço de host.")
        if self.address == self.forwarder:
            raise ValueError("O encaminhador DNS precisa ser diferente do próprio controlador.")
        return self


class Record(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    account: str = Field(default="", max_length=64)
    email: str = Field(default="", max_length=200)
    ou: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=500)
    enabled: bool = True
    os: str = Field(default="Linux", max_length=100)
    role: Literal["workstation", "server"] = "workstation"
    members: list[str] = Field(default_factory=list, max_length=500)
    record_type: Literal["A", "AAAA", "CNAME", "TXT", "MX", "PTR"] = "A"
    value: str = Field(default="", max_length=1000)
    priority: int = Field(default=10, ge=0, le=65535)
    ttl: int = Field(default=3600, ge=60, le=86400)
    platform: Literal["Windows", "Linux"] = "Windows"
    policy_type: str = Field(default="registry", max_length=80)
    settings: dict = Field(default_factory=dict)

    @field_validator("account")
    @classmethod
    def valid_account(cls, value):
        if value and not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", value):
            raise ValueError("A conta aceita letras, números, ponto, hífen e sublinhado.")
        return value.lower()


class LdapCredentials(StrictModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    host: str = Field(min_length=3, max_length=200)
    port: int = Field(default=636, ge=1, le=65535)
    bind_dn: str = Field(min_length=3, max_length=500)
    password: str = Field(min_length=1, max_length=256)
    base_dn: str = Field(min_length=5, max_length=500)
    ca_pem: str = Field(default="", max_length=20000)

    @field_validator("host")
    @classmethod
    def host_only(cls, value):
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]{1,199}", value):
            raise ValueError("Informe somente o hostname ou IPv4 do controlador, sem protocolo ou caminho.")
        return value

    @field_validator("base_dn")
    @classmethod
    def base_is_domain(cls, value):
        if not re.fullmatch(r"(?i)DC=[a-z0-9-]+(?:,DC=[a-z0-9-]+)+", value):
            raise ValueError("Utilize o DN do domínio no formato DC=empresa,DC=example,DC=com.")
        return value
