"""Datenmodell der Forschungs-API-Registry.

Eine ResearchApi beschreibt eine externe wissenschaftliche/medizinische Quelle:
wohin (base_url/url_pattern), ob/wie ein Key injiziert wird (auth_type/auth_param),
und ob sie aktiv ist. Secrets (key) liegen in der Registry verschlüsselt.
"""
from __future__ import annotations

from dataclasses import dataclass

CATEGORIES = ("literatur", "medikamente", "krankheiten_gene", "studien")
AUTH_TYPES = ("none", "query", "header", "bearer")


@dataclass
class ResearchApi:
    id: str
    name: str
    category: str
    base_url: str
    url_pattern: str                 # fetch_url-Matching, z.B. https://api.fda.gov/*
    docs_url: str = ""
    description: str = ""
    needs_key: bool = False          # True = ohne Key nicht nutzbar (sonst optionaler Key)
    auth_type: str = "none"          # none|query|header|bearer
    auth_param: str = ""             # Query-Param- bzw. Header-Name (bei bearer leer)
    polite_email_param: str = ""     # z.B. "mailto" (OpenAlex/Crossref) — kein Secret
    rate_limit: str = ""
    enabled: bool = True
    key: str = ""                    # Secret; in der Registry verschlüsselt persistiert

    def public_dict(self) -> dict:
        """Ohne Klartext-Key — fürs Frontend/GET (nur has_key-Flag)."""
        d = {k: getattr(self, k) for k in (
            "id", "name", "category", "base_url", "url_pattern", "docs_url",
            "description", "needs_key", "auth_type", "auth_param",
            "polite_email_param", "rate_limit", "enabled")}
        d["has_key"] = bool(self.key)
        return d
