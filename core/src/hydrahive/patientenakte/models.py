"""Typen der Patientenakte."""
from __future__ import annotations

from typing import Any, TypedDict


class Patient(TypedDict, total=False):
    id: str
    owner_user_id: str
    slug: str
    name: str
    vorname: str
    geburtsdatum: str
    geschlecht: str
    adresse: dict[str, Any]
    versicherung: dict[str, Any]
    notfallkontakt: dict[str, Any]
    external_id: str
    created_at: str
    updated_at: str
