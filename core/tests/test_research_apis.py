"""Forschungs-API-Registry — Model/Seed/Store/Injektion (ohne Netz, ohne PG)."""
from __future__ import annotations

from hydrahive.research._seed import SEED
from hydrahive.research.models import AUTH_TYPES, CATEGORIES


def test_seed_integrity():
    ids = [a.id for a in SEED]
    assert len(ids) == len(set(ids))                      # eindeutige ids
    assert len(SEED) >= 12
    for a in SEED:
        assert a.id and a.base_url and a.name
        assert a.category in CATEGORIES
        assert a.auth_type in AUTH_TYPES
        assert a.url_pattern.startswith("https://")
        if a.needs_key:
            assert a.auth_param or a.auth_type == "bearer"  # wohin der Key geht
        else:
            assert a.enabled                                # keyless ist default aktiv


def test_keyless_pubmed_and_openalex_present():
    by_id = {a.id: a for a in SEED}
    assert by_id["pubmed"].base_url.startswith("https://eutils.ncbi.nlm.nih.gov")
    assert by_id["openalex"].polite_email_param == "mailto"
    assert by_id["core"].needs_key and not by_id["core"].enabled  # Key-Quelle startet aus
