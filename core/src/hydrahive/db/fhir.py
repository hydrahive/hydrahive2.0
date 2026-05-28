"""FHIR-Ressourcen — Datenbankoperationen."""
from __future__ import annotations

import json

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db

# FHIR resourceType → Sidebar-Kategorie
RESOURCE_LABELS: dict[str, str] = {
    "Condition": "Diagnosen",
    "MedicationRequest": "Medikamente",
    "MedicationStatement": "Medikamente",
    "Observation": "Laborwerte",
    "AllergyIntolerance": "Allergien",
    "Immunization": "Impfungen",
    "Procedure": "Eingriffe",
    "Encounter": "Arztbesuche",
    "DiagnosticReport": "Befunde",
    "DocumentReference": "Dokumente",
    "Patient": "Stammdaten",
}


def upsert_bundle(bundle: dict, user_id: str) -> dict:
    """Importiert ein FHIR Bundle. Gibt Import-Statistik zurück."""
    if bundle.get("resourceType") != "Bundle":
        raise ValueError("Kein gültiges FHIR Bundle")

    entries = bundle.get("entry", [])
    imported = updated = errors = 0

    with db() as conn:
        for entry in entries:
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType", "")
            resource_id = resource.get("id", "")
            if not resource_type or not resource_id:
                errors += 1
                continue
            try:
                exists = conn.execute(
                    "SELECT id FROM fhir_resources WHERE user_id=? AND resource_type=? AND resource_id=?",
                    (user_id, resource_type, resource_id),
                ).fetchone()
                if exists:
                    conn.execute(
                        "UPDATE fhir_resources SET resource_json=?, imported_at=? WHERE user_id=? AND resource_type=? AND resource_id=?",
                        (json.dumps(resource), now_iso(), user_id, resource_type, resource_id),
                    )
                    updated += 1
                else:
                    conn.execute(
                        "INSERT INTO fhir_resources (id, user_id, resource_type, resource_id, resource_json, imported_at) VALUES (?,?,?,?,?,?)",
                        (uuid7(), user_id, resource_type, resource_id, json.dumps(resource), now_iso()),
                    )
                    imported += 1
            except Exception:
                errors += 1

    return {"imported": imported, "updated": updated, "errors": errors}


def query_by_type(user_id: str, resource_type: str) -> list[dict]:
    """Gibt alle Ressourcen eines Typs für einen User zurück."""
    with db() as conn:
        rows = conn.execute(
            "SELECT resource_json, imported_at FROM fhir_resources WHERE user_id=? AND resource_type=? ORDER BY imported_at DESC",
            (user_id, resource_type),
        ).fetchall()
    return [{"resource": json.loads(r["resource_json"]), "imported_at": r["imported_at"]} for r in rows]


def summary(user_id: str) -> dict:
    """Gibt Zähler pro Ressourcentyp zurück."""
    with db() as conn:
        rows = conn.execute(
            "SELECT resource_type, COUNT(*) as count FROM fhir_resources WHERE user_id=? GROUP BY resource_type",
            (user_id,),
        ).fetchall()
    return {r["resource_type"]: r["count"] for r in rows}


def timeline(user_id: str) -> list[dict]:
    """Gibt alle Ressourcen chronologisch sortiert zurück (neueste zuerst)."""
    with db() as conn:
        rows = conn.execute(
            "SELECT resource_type, resource_json, imported_at FROM fhir_resources WHERE user_id=? ORDER BY imported_at DESC",
            (user_id,),
        ).fetchall()
    return [
        {
            "resource_type": r["resource_type"],
            "label": RESOURCE_LABELS.get(r["resource_type"], r["resource_type"]),
            "resource": json.loads(r["resource_json"]),
            "imported_at": r["imported_at"],
        }
        for r in rows
    ]


def query_fulltext(user_id: str, search: str, resource_types: list[str] | None = None) -> list[dict]:
    """Volltextsuche im resource_json für den KI-Assistenten."""
    with db() as conn:
        if resource_types:
            placeholders = ",".join("?" * len(resource_types))
            rows = conn.execute(
                f"SELECT resource_type, resource_json FROM fhir_resources WHERE user_id=? AND resource_type IN ({placeholders}) AND resource_json LIKE ? ORDER BY imported_at DESC LIMIT 50",
                (user_id, *resource_types, f"%{search}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT resource_type, resource_json FROM fhir_resources WHERE user_id=? AND resource_json LIKE ? ORDER BY imported_at DESC LIMIT 50",
                (user_id, f"%{search}%"),
            ).fetchall()
    return [{"resource_type": r["resource_type"], "resource": json.loads(r["resource_json"])} for r in rows]
