"""Sprache für die Hilfe-Werkzeuge: dieselbe Spracheinstellung, die der Runner nutzt (runner/_language_rule.py)."""
from __future__ import annotations


def language_for(username: str) -> str:
    from hydrahive.runner._language_rule import language_for as _lf   # lazy: Import-Kreis tools ↔ runner vermeiden
    return _lf(username)


def help_lang(user_id: str) -> str:
    lang = language_for(user_id)
    return "de" if lang == "auto" else lang
