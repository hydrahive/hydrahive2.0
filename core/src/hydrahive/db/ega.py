"""TK eGA-Daten — Datenbankoperationen."""
from __future__ import annotations

import hashlib
import json

from hydrahive.db.connection import db


def _stable_id(dto_type: str, record: dict) -> str:
    tk_id = record.get("id")
    if tk_id:
        return f"{dto_type[:3]}-{tk_id}"
    boid = record.get("metaInformation", {}).get("contentProviderDetails", {}).get("businessObjectId", "")
    seed = boid or json.dumps(record, sort_keys=True)[:200]
    return hashlib.sha256(f"{dto_type}:{seed}".encode()).hexdigest()[:32]


def _sort_date(record: dict) -> str | None:
    dt = (record.get("metaInformation", {}).get("sortDate")
          or record.get("period", {}).get("start")
          or record.get("billablePeriod", {}).get("start"))
    if not dt:
        return None
    return dt.split("T")[0] if "T" in dt else dt


def _display(dto_type: str, record: dict) -> str:
    if dto_type == "Encounter":
        sp = record.get("serviceProvider", {})
        name = sp.get("name") or (sp.get("type") or [{}])[0].get("text", "")
        date = _sort_date(record) or record.get("period", {}).get("start", "")
        return f"{date} — {name}" if name else date or "Arztbesuch"
    if dto_type == "MedicationDispense":
        med = record.get("medication", {})
        name = med.get("code", {}).get("text", "")
        if not name:
            ings = med.get("ingredient", [])
            name = (ings[0].get("itemCodeableConcept", {}).get("text", "") if ings else "") or "Medikament"
        return name
    if dto_type == "Procedure":
        code = record.get("code", {}).get("text") or record.get("category", {}).get("text", "Prozedur")
        return code
    if dto_type == "Condition":
        code = record.get("code", {})
        codings = code.get("coding", [])
        return next((c.get("display") or c.get("code") for c in codings if c.get("display") or c.get("code")), code.get("text", "Diagnose"))
    if dto_type == "HospitalStay":
        org = record.get("organization", {}).get("name", "")
        items = record.get("item", [])
        desc = next((i.get("service", {}).get("text", "") for i in items if i.get("service", {}).get("text")), "")
        return org or desc[:80] or "Krankenhausaufenthalt"
    if dto_type == "AmbulantClaim":
        org = record.get("organization", {}).get("name", "")
        bp = record.get("billablePeriod", {})
        date = bp.get("start", "")[:7] if bp.get("start") else ""
        return f"{org} ({date})" if org and date else org or "Ambulante Abrechnung"
    return dto_type


def upsert_records(records: list[tuple[str, dict]], user_id: str) -> dict:
    """Speichert TK-EGA-Records (dto_type, record_dict). Gibt Import-Statistik zurück."""
    imported = updated = errors = 0
    with db() as conn:
        for dto_type, record in records:
            try:
                rid = _stable_id(dto_type, record)
                display = _display(dto_type, record)
                sort_date = _sort_date(record)
                record_json = json.dumps(record, ensure_ascii=False)
                existing = conn.execute("SELECT id FROM ega_records WHERE id=? AND user_id=?", (rid, user_id)).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE ega_records SET display=?, sort_date=?, record_json=?, imported_at=datetime('now') WHERE id=? AND user_id=?",
                        (display, sort_date, record_json, rid, user_id),
                    )
                    updated += 1
                else:
                    conn.execute(
                        "INSERT INTO ega_records(id, user_id, dto_type, display, sort_date, record_json) VALUES(?,?,?,?,?,?)",
                        (rid, user_id, dto_type, display, sort_date, record_json),
                    )
                    imported += 1
            except Exception:
                errors += 1
    return {"imported": imported, "updated": updated, "errors": errors}


def summary(user_id: str) -> dict:
    with db() as conn:
        rows = conn.execute(
            "SELECT dto_type, COUNT(*) FROM ega_records WHERE user_id=? GROUP BY dto_type",
            (user_id,),
        ).fetchall()
    return {r[0]: r[1] for r in rows}


def query_by_type(user_id: str, dto_type: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT id, display, sort_date, record_json FROM ega_records WHERE user_id=? AND dto_type=? ORDER BY sort_date DESC",
            (user_id, dto_type),
        ).fetchall()
    return [{"id": r[0], "display": r[1], "sort_date": r[2], "record": json.loads(r[3])} for r in rows]


def timeline(user_id: str, limit: int = 200) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT id, dto_type, display, sort_date FROM ega_records WHERE user_id=? ORDER BY sort_date DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{"id": r[0], "dto_type": r[1], "display": r[2], "sort_date": r[3]} for r in rows]
