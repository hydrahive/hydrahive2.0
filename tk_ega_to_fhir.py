#!/usr/bin/env python3
"""Convert TK Techniker Krankenkasse eGA export to a FHIR R4 Bundle.

Usage:
    python tk_ega_to_fhir.py <export-dir-or-zip> [output.json]

The script reads all DTO files from a TK eGA export (directory or ZIP),
maps them to FHIR R4 resources, and writes a single Bundle JSON that can
be imported via the "Akte aktualisieren" button in the Gesundheit section.
"""

import hashlib
import json
import os
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ─── helpers ──────────────────────────────────────────────────────────────────

def stable_id(tk_id: str | None, salt: str) -> str:
    """Return the TK id as-is, or derive a stable UUID-shaped id from a hash."""
    if tk_id:
        return tk_id
    raw = hashlib.sha256(salt.encode()).hexdigest()
    return str(uuid.UUID(raw[:32]))


def sort_date(entry: dict) -> str | None:
    return entry.get("metaInformation", {}).get("sortDate")


def iso_date(dt_str: str | None) -> str | None:
    if not dt_str:
        return None
    # Normalise "2020-03-22T23:00:00.000Z" → keep as-is; plain "2023-03-27" → keep
    return dt_str.split("T")[0] if "T" in dt_str else dt_str


def fhir_entry(resource: dict) -> dict:
    return {
        "fullUrl": f"urn:uuid:{resource['id']}",
        "resource": resource,
    }


# ─── EncounterDTO → Encounter ─────────────────────────────────────────────────

def convert_encounters(items: list[dict]) -> list[dict]:
    resources = []
    for i, item in enumerate(items):
        if not item:
            continue
        rid = stable_id(item.get("id"), f"encounter-{i}-{json.dumps(item, sort_keys=True)[:200]}")
        period = item.get("period", {})
        provider_type = ""
        provider_name = ""
        sp = item.get("serviceProvider", {})
        if sp.get("type"):
            provider_type = sp["type"][0].get("text", "")
        for ident in sp.get("identifier", []):
            if ident.get("system", "").endswith("bsnr") or ident.get("type", {}).get("text") == "BSNR":
                pass
        if sp.get("name"):
            provider_name = sp["name"]

        resource: dict[str, Any] = {
            "resourceType": "Encounter",
            "id": rid,
            "status": item.get("status", "finished"),
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "AMB",
                "display": "ambulatory",
            },
        }
        if period.get("start") or period.get("end"):
            resource["period"] = {}
            if period.get("start"):
                resource["period"]["start"] = period["start"]
            if period.get("end"):
                resource["period"]["end"] = period["end"]
        display = provider_name or provider_type
        if display:
            resource["serviceProvider"] = {"display": display}
        resources.append(resource)
    return resources


# ─── ConditionDTO → Condition (extract contained ICD conditions) ──────────────

def convert_conditions(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    resources = []

    def _extract(cond_obj: dict, parent_id: str, idx: int) -> dict | None:
        code = cond_obj.get("code")
        if not code:
            return None
        codings = code.get("coding", [])
        icd_coding = next(
            (c for c in codings if "icd" in c.get("system", "").lower()),
            codings[0] if codings else None,
        )
        if not icd_coding:
            return None
        dedup_key = icd_coding.get("code", "") + "|" + icd_coding.get("display", "")
        if dedup_key in seen:
            return None
        seen.add(dedup_key)

        rid = stable_id(
            cond_obj.get("id"),
            f"condition-{parent_id}-{idx}-{dedup_key}",
        )
        resource: dict[str, Any] = {
            "resourceType": "Condition",
            "id": rid,
            "code": {
                "coding": [icd_coding],
                "text": code.get("text", icd_coding.get("display", "")),
            },
        }
        if cond_obj.get("verificationStatus"):
            resource["verificationStatus"] = {
                "coding": [{"code": cond_obj["verificationStatus"]}]
            }
        if cond_obj.get("onsetDateTime"):
            resource["onsetDateTime"] = cond_obj["onsetDateTime"]
        if cond_obj.get("recordedDate"):
            resource["recordedDate"] = cond_obj["recordedDate"]
        return resource

    for i, item in enumerate(items):
        if not item:
            continue
        parent_id = item.get("id", str(i))
        # The outer condition is usually "Sick Leave" wrapper; real diagnoses are in contained
        for j, contained in enumerate(item.get("contained", [])):
            if contained.get("resourceType") == "Condition":
                r = _extract(contained, parent_id, j)
                if r:
                    resources.append(r)
        # Also try the outer condition itself if it has an ICD code
        if item.get("code"):
            codings = item.get("code", {}).get("coding", [])
            if any("icd" in c.get("system", "").lower() for c in codings):
                r = _extract(item, parent_id, 999)
                if r:
                    resources.append(r)

    return resources


# ─── MedicationDispenseDTO → MedicationDispense ───────────────────────────────

def convert_medication_dispenses(items: list[dict]) -> list[dict]:
    resources = []
    for i, item in enumerate(items):
        if not item:
            continue
        medication = item.get("medication", {})
        if not medication:
            continue
        code = medication.get("code", {})
        codings = code.get("coding", [])
        if not codings and not medication.get("ingredient"):
            continue

        rid = stable_id(item.get("id"), f"meddispense-{i}-{json.dumps(codings)[:100]}")
        when = iso_date(sort_date(item))

        resource: dict[str, Any] = {
            "resourceType": "MedicationDispense",
            "id": rid,
            "status": "completed",
            "medicationCodeableConcept": {
                "coding": codings,
                "text": code.get("text", ""),
            },
        }
        if when:
            resource["whenHandedOver"] = when

        # Add ATC code from ingredient if present
        ingredients = medication.get("ingredient", [])
        if ingredients:
            atc_coding = None
            for ing in ingredients:
                atc_codings = ing.get("itemCodeableConcept", {}).get("coding", [])
                atc = next(
                    (c for c in atc_codings if "atc" in c.get("system", "").lower()),
                    None,
                )
                if atc:
                    atc_coding = atc
                    break
            if atc_coding:
                resource["medicationCodeableConcept"].setdefault("coding", [])
                existing_systems = {c.get("system") for c in resource["medicationCodeableConcept"]["coding"]}
                if atc_coding.get("system") not in existing_systems:
                    resource["medicationCodeableConcept"]["coding"].append(atc_coding)
                if not resource["medicationCodeableConcept"].get("text"):
                    resource["medicationCodeableConcept"]["text"] = atc_coding.get("display", "")

        resources.append(resource)
    return resources


# ─── ProcedureDTO → Procedure ─────────────────────────────────────────────────

def convert_procedures(items: list[dict]) -> list[dict]:
    resources = []
    for i, item in enumerate(items):
        if not item:
            continue
        rid = stable_id(item.get("id"), f"procedure-{i}-{json.dumps(item, sort_keys=True)[:200]}")
        when = iso_date(sort_date(item))

        resource: dict[str, Any] = {
            "resourceType": "Procedure",
            "id": rid,
            "status": item.get("status", "completed"),
        }
        if item.get("category"):
            resource["category"] = item["category"]
        if item.get("code"):
            resource["code"] = item["code"]
        if when:
            resource["performedDateTime"] = when
        elif item.get("performedDateTime"):
            resource["performedDateTime"] = item["performedDateTime"]
        elif item.get("performedPeriod"):
            resource["performedPeriod"] = item["performedPeriod"]

        resources.append(resource)
    return resources


# ─── HospitalClaimDTO → Encounter (inpatient) ────────────────────────────────

def convert_hospital_claims(items: list[dict]) -> list[dict]:
    resources = []
    for i, item in enumerate(items):
        if not item:
            continue
        rid = stable_id(item.get("id"), f"hospital-{i}-{json.dumps(item, sort_keys=True)[:200]}")
        when = iso_date(sort_date(item))
        period_start = when
        period_end = None
        if item.get("period"):
            period_start = item["period"].get("start", when)
            period_end = item["period"].get("end")

        service_items = item.get("item", [])
        description = ""
        for si in service_items:
            if si.get("service", {}).get("text"):
                description = si["service"]["text"]
                break

        resource: dict[str, Any] = {
            "resourceType": "Encounter",
            "id": rid,
            "status": "finished",
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "IMP",
                "display": "inpatient encounter",
            },
        }
        if period_start:
            resource["period"] = {"start": period_start}
            if period_end:
                resource["period"]["end"] = period_end
        if description:
            resource["type"] = [{"text": description[:200]}]
        if item.get("organization", {}).get("name"):
            resource["serviceProvider"] = {"display": item["organization"]["name"]}

        resources.append(resource)
    return resources


# ─── load files from directory or ZIP ────────────────────────────────────────

def load_dto_files(source: str) -> dict[str, list]:
    """Returns mapping: dto_key → list of entries."""
    result: dict[str, list] = {}

    def _read_file(name: str, content: bytes) -> None:
        if not name.endswith(".json"):
            return
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return
        if not isinstance(data, dict):
            return
        for key, value in data.items():
            if isinstance(value, list):
                result[key] = value

    if os.path.isdir(source):
        for fname in os.listdir(source):
            fpath = os.path.join(source, fname)
            if os.path.isfile(fpath) and fname.endswith(".json"):
                with open(fpath, "rb") as f:
                    _read_file(fname, f.read())
    elif zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as zf:
            for name in zf.namelist():
                if name.endswith(".json"):
                    _read_file(name, zf.read(name))
    else:
        raise ValueError(f"Not a directory or ZIP file: {source}")

    return result


# ─── main ─────────────────────────────────────────────────────────────────────

def convert(source: str, output: str) -> None:
    print(f"Reading TK eGA export from: {source}")
    dto_files = load_dto_files(source)

    for key, items in dto_files.items():
        non_empty = [i for i in items if i]
        print(f"  {key}: {len(items)} entries ({len(non_empty)} non-empty)")

    all_resources: list[dict] = []

    # Encounters
    encounter_items = dto_files.get("EncounterDTO-encounter", [])
    encounters = convert_encounters([i for i in encounter_items if i])
    print(f"\nConverted {len(encounters)} Encounters (outpatient visits)")
    all_resources.extend(encounters)

    # Conditions (ICD diagnoses from contained resources)
    condition_items = dto_files.get("ConditionDTO-condition", [])
    conditions = convert_conditions([i for i in condition_items if i])
    print(f"Converted {len(conditions)} Conditions (deduplicated ICD diagnoses)")
    all_resources.extend(conditions)

    # Medication dispenses
    med_items = dto_files.get("MedicationDispenseDTO-medicationDispense", [])
    meds = convert_medication_dispenses([i for i in med_items if i])
    print(f"Converted {len(meds)} MedicationDispenses")
    all_resources.extend(meds)

    # Procedures
    proc_items = dto_files.get("ProcedureDTO-procedure", [])
    procs = convert_procedures([i for i in proc_items if i])
    print(f"Converted {len(procs)} Procedures")
    all_resources.extend(procs)

    # Hospital stays
    hospital_items = dto_files.get("HospitalClaimDTO-hospitalClaim", [])
    hospitals = convert_hospital_claims([i for i in hospital_items if i])
    print(f"Converted {len(hospitals)} Encounters (hospital stays)")
    all_resources.extend(hospitals)

    # Immunizations (pass through if present)
    imm_items = [i for i in dto_files.get("ImmunizationDTO-immunization", []) if i]
    if imm_items:
        print(f"Skipping {len(imm_items)} Immunizations (empty in this export)")

    bundle = {
        "resourceType": "Bundle",
        "id": str(uuid.uuid4()),
        "type": "collection",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(all_resources),
        "entry": [fhir_entry(r) for r in all_resources],
    }

    with open(output, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)

    print(f"\nTotal resources: {len(all_resources)}")
    print(f"Written to: {output}")
    print("\nUpload this file via Gesundheit → Digitale Akte → Akte aktualisieren")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    source_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "tk_fhir_bundle.json"

    convert(source_path, output_path)
