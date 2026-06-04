"""eGA/FHIR-Import: stille Fehler werden geloggt statt nur gezählt.

Portiert aus core test_db_import_logging.py (#208 M1a/M1b). Der Health-Ingest-
Teil (M1c) bleibt Core (Apple-Health, Etappe 3).
"""
from __future__ import annotations

import logging

from backend import ega_store as ega_db
from backend import fhir_store as fhir_db


def test_ega_upsert_logs_swallowed_error(caplog):
    # set ist nicht JSON-serialisierbar → wirft im try-Block, wird verschluckt
    records = [("Medikament", {"boom": {1, 2}})]
    with caplog.at_level(logging.WARNING, logger="backend.ega_store"):
        result = ega_db.upsert_records(records, "u_ega")
    assert result["errors"] == 1
    assert any(r.levelno >= logging.WARNING for r in caplog.records)


def test_fhir_upsert_logs_swallowed_error(caplog):
    bundle = {
        "resourceType": "Bundle",
        "entry": [{"resource": {"resourceType": "Observation", "id": "1", "boom": {1, 2}}}],
    }
    with caplog.at_level(logging.WARNING, logger="backend.fhir_store"):
        result = fhir_db.upsert_bundle(bundle, "u_fhir")
    assert result["errors"] == 1
    assert any(r.levelno >= logging.WARNING for r in caplog.records)
