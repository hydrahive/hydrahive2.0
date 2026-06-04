"""TK eGA ZIP → FHIR R4 Bundle converter (in-memory)."""
from __future__ import annotations

import hashlib
import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any


def extract_ega_records(data: bytes) -> list[tuple[str, dict]]:
    """Extrahiert alle TK-EGA-Records als (dto_type, record_dict) Tupel."""
    dto_files = _load_zip(data)
    out: list[tuple[str, dict]] = []

    for item in (i for i in dto_files.get("EncounterDTO-encounter", []) if i):
        out.append(("Encounter", item))

    for item in (i for i in dto_files.get("HospitalClaimDTO-hospitalClaim", []) if i):
        out.append(("HospitalStay", item))

    for item in (i for i in dto_files.get("MedicationDispenseDTO-medicationDispense", []) if i):
        out.append(("MedicationDispense", item))

    for item in (i for i in dto_files.get("AmbulantClaimDTO-ambulantClaim", []) if i):
        out.append(("AmbulantClaim", item))

    for item in (i for i in dto_files.get("MedicationClaimDTO-medicationClaim", []) if i):
        out.append(("MedicationClaim", item))

    for item in (i for i in dto_files.get("ProcedureDTO-procedure", []) if i):
        out.append(("Procedure", item))

    # Conditions: innere ICD-Diagnosen aus contained extrahieren
    seen: set[str] = set()
    for item in (i for i in dto_files.get("ConditionDTO-condition", []) if i):
        for contained in item.get("contained", []):
            if contained.get("resourceType") != "Condition":
                continue
            codings = contained.get("code", {}).get("coding", [])
            icd = next((c for c in codings if "icd" in c.get("system", "").lower()), None)
            if not icd:
                continue
            key = icd.get("code", "") + "|" + icd.get("display", "")
            if key in seen:
                continue
            seen.add(key)
            out.append(("Condition", contained))

    return out


def convert_ega_zip(data: bytes) -> dict:
    """Convert TK eGA export ZIP bytes to a FHIR R4 Bundle dict."""
    dto_files = _load_zip(data)
    resources: list[dict] = []

    resources.extend(_encounters([i for i in dto_files.get("EncounterDTO-encounter", []) if i]))
    resources.extend(_conditions([i for i in dto_files.get("ConditionDTO-condition", []) if i]))
    resources.extend(_medication_dispenses([i for i in dto_files.get("MedicationDispenseDTO-medicationDispense", []) if i]))
    resources.extend(_procedures([i for i in dto_files.get("ProcedureDTO-procedure", []) if i]))
    resources.extend(_hospital_encounters([i for i in dto_files.get("HospitalClaimDTO-hospitalClaim", []) if i]))

    return {
        "resourceType": "Bundle",
        "id": str(uuid.uuid4()),
        "type": "collection",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(resources),
        "entry": [{"fullUrl": f"urn:uuid:{r['id']}", "resource": r} for r in resources],
    }


# ─── loaders ──────────────────────────────────────────────────────────────────

def _load_zip(data: bytes) -> dict[str, list]:
    result: dict[str, list] = {}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            if not name.endswith(".json"):
                continue
            try:
                parsed = json.loads(zf.read(name))
            except (json.JSONDecodeError, KeyError):
                continue
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    if isinstance(value, list):
                        result[key] = value
    return result


# ─── helpers ──────────────────────────────────────────────────────────────────

def _stable_id(tk_id: str | None, salt: str) -> str:
    if tk_id:
        return tk_id
    raw = hashlib.sha256(salt.encode()).hexdigest()
    return str(uuid.UUID(raw[:32]))


def _sort_date(entry: dict) -> str | None:
    dt = entry.get("metaInformation", {}).get("sortDate")
    if not dt:
        return None
    return dt.split("T")[0] if "T" in dt else dt


# ─── converters ───────────────────────────────────────────────────────────────

def _encounters(items: list[dict]) -> list[dict]:
    out = []
    for i, item in enumerate(items):
        rid = _stable_id(item.get("id"), f"enc-{i}-{json.dumps(item, sort_keys=True)[:120]}")
        sp = item.get("serviceProvider", {})
        display = sp.get("name") or (sp.get("type") or [{}])[0].get("text", "")
        resource: dict[str, Any] = {
            "resourceType": "Encounter",
            "id": rid,
            "status": item.get("status", "finished"),
            "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
        }
        p = item.get("period", {})
        if p.get("start") or p.get("end"):
            resource["period"] = {k: v for k, v in p.items() if k in ("start", "end") and v}
        if display:
            resource["serviceProvider"] = {"display": display}
        out.append(resource)
    return out


def _conditions(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []

    def _from(obj: dict, parent: str, idx: int) -> dict | None:
        code = obj.get("code", {})
        codings = code.get("coding", [])
        icd = next((c for c in codings if "icd" in c.get("system", "").lower()), None)
        if not icd:
            return None
        key = icd.get("code", "") + "|" + icd.get("display", "")
        if key in seen:
            return None
        seen.add(key)
        rid = _stable_id(obj.get("id"), f"cond-{parent}-{idx}-{key}")
        resource: dict[str, Any] = {
            "resourceType": "Condition",
            "id": rid,
            "code": {"coding": [icd], "text": code.get("text", icd.get("display", ""))},
        }
        if obj.get("verificationStatus"):
            resource["verificationStatus"] = {"coding": [{"code": obj["verificationStatus"]}]}
        return resource

    for i, item in enumerate(items):
        pid = item.get("id", str(i))
        for j, c in enumerate(item.get("contained", [])):
            if c.get("resourceType") == "Condition":
                r = _from(c, pid, j)
                if r:
                    out.append(r)
        if any("icd" in c.get("system", "").lower() for c in item.get("code", {}).get("coding", [])):
            r = _from(item, pid, 999)
            if r:
                out.append(r)
    return out


def _medication_dispenses(items: list[dict]) -> list[dict]:
    out = []
    for i, item in enumerate(items):
        med = item.get("medication", {})
        if not med:
            continue
        code = med.get("code", {})
        codings = list(code.get("coding", []))
        for ing in med.get("ingredient", []):
            for c in ing.get("itemCodeableConcept", {}).get("coding", []):
                if "atc" in c.get("system", "").lower() and c not in codings:
                    codings.append(c)
        if not codings:
            continue
        rid = _stable_id(item.get("id"), f"med-{i}-{json.dumps(codings)[:80]}")
        resource: dict[str, Any] = {
            "resourceType": "MedicationDispense",
            "id": rid,
            "status": "completed",
            "medicationCodeableConcept": {"coding": codings, "text": code.get("text", "")},
        }
        when = _sort_date(item)
        if when:
            resource["whenHandedOver"] = when
        out.append(resource)
    return out


def _procedures(items: list[dict]) -> list[dict]:
    out = []
    for i, item in enumerate(items):
        rid = _stable_id(item.get("id"), f"proc-{i}-{json.dumps(item, sort_keys=True)[:120]}")
        resource: dict[str, Any] = {
            "resourceType": "Procedure",
            "id": rid,
            "status": item.get("status", "completed"),
        }
        for field in ("category", "code"):
            if item.get(field):
                resource[field] = item[field]
        when = _sort_date(item) or item.get("performedDateTime")
        if when:
            resource["performedDateTime"] = when
        elif item.get("performedPeriod"):
            resource["performedPeriod"] = item["performedPeriod"]
        out.append(resource)
    return out


def _hospital_encounters(items: list[dict]) -> list[dict]:
    out = []
    for i, item in enumerate(items):
        rid = _stable_id(item.get("id"), f"hosp-{i}-{json.dumps(item, sort_keys=True)[:120]}")
        when = _sort_date(item)
        p = item.get("period", {})
        resource: dict[str, Any] = {
            "resourceType": "Encounter",
            "id": rid,
            "status": "finished",
            "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP"},
        }
        period: dict[str, str] = {}
        if p.get("start") or when:
            period["start"] = p.get("start") or when  # type: ignore[assignment]
        if p.get("end"):
            period["end"] = p["end"]
        if period:
            resource["period"] = period
        desc = next((si.get("service", {}).get("text", "") for si in item.get("item", []) if si.get("service", {}).get("text")), "")
        if desc:
            resource["type"] = [{"text": desc[:200]}]
        if item.get("organization", {}).get("name"):
            resource["serviceProvider"] = {"display": item["organization"]["name"]}
        out.append(resource)
    return out
