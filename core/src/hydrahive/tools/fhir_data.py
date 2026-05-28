"""query_fhir_data — KI-Tool für Zugriff auf die FHIR-Patientenakte."""
from __future__ import annotations

import json

from hydrahive.db import fhir as fhir_db
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Liest Daten aus der digitalen Patientenakte (FHIR R4 Format, importiert aus der TK-App). "
    "Enthält Diagnosen, Medikamente, Laborwerte, Allergien, Impfungen, Eingriffe, "
    "Arztbesuche, Befunde und Dokumente. "
    "Nutze dieses Tool um Fragen zur Krankengeschichte zu beantworten. "
    "Stelle keine Diagnosen — erkläre nur was in der Akte steht. "
    "Verweise bei medizinischen Unsicherheiten auf den behandelnden Arzt."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "resource_types": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Optional: Welche Ressourcentypen abfragen. "
                "Mögliche Werte: Condition, MedicationRequest, MedicationStatement, "
                "Observation, AllergyIntolerance, Immunization, Procedure, "
                "Encounter, DiagnosticReport, DocumentReference, Patient. "
                "Leer lassen für alle Typen."
            ),
        },
        "search_text": {
            "type": "string",
            "description": "Optional: Volltextsuche im JSON (z.B. 'HbA1c', 'Ramipril', 'Kardiologie').",
        },
    },
}


def _format_resource(r: dict) -> str:
    """Wandelt eine FHIR-Ressource in lesbaren Text um."""
    rt = r.get("resourceType", "")
    rid = r.get("id", "")

    if rt == "Condition":
        code = r.get("code", {})
        codings = code.get("coding", [{}])
        display = codings[0].get("display", code.get("text", "Unbekannt"))
        icd = codings[0].get("code", "")
        status = r.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "")
        onset = r.get("onsetDateTime", r.get("onsetString", ""))
        return f"Diagnose [{rid}]: {display} (ICD: {icd}, Status: {status}, Beginn: {onset})"

    if rt in ("MedicationRequest", "MedicationStatement"):
        med = r.get("medicationCodeableConcept", r.get("medicationReference", {}))
        name = med.get("text", med.get("display", "Unbekannt")) if isinstance(med, dict) else str(med)
        status = r.get("status", "")
        return f"Medikament [{rid}]: {name} (Status: {status})"

    if rt == "Observation":
        code = r.get("code", {}).get("text", r.get("code", {}).get("coding", [{}])[0].get("display", ""))
        value = r.get("valueQuantity", {})
        val_str = f"{value.get('value', '')} {value.get('unit', '')}".strip() if value else r.get("valueString", "")
        date = r.get("effectiveDateTime", "")
        return f"Laborwert [{rid}]: {code} = {val_str} (am {date})"

    if rt == "AllergyIntolerance":
        substance = r.get("code", {}).get("text", "Unbekannt")
        return f"Allergie [{rid}]: {substance}"

    if rt == "Immunization":
        vaccine = r.get("vaccineCode", {}).get("text", "Unbekannt")
        date = r.get("occurrenceDateTime", "")
        return f"Impfung [{rid}]: {vaccine} (am {date})"

    if rt == "Encounter":
        class_ = r.get("class", {}).get("display", "")
        date = r.get("period", {}).get("start", "")
        return f"Arztbesuch [{rid}]: {class_} (am {date})"

    # Fallback: JSON-Kurzform
    return f"{rt} [{rid}]: {json.dumps(r)[:200]}"


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    user_id = ctx.user_id
    if not user_id:
        return ToolResult.fail("Kein User-Kontext verfügbar.")

    resource_types: list[str] | None = args.get("resource_types") or None
    search_text: str = (args.get("search_text") or "").strip()

    try:
        if search_text:
            resources = fhir_db.query_fulltext(user_id, search_text, resource_types)
            entries = [r["resource"] for r in resources]
        elif resource_types:
            entries = []
            for rt in resource_types:
                for row in fhir_db.query_by_type(user_id, rt):
                    entries.append(row["resource"])
        else:
            entries = [row["resource"] for row in fhir_db.timeline(user_id)]

    except Exception as exc:
        return ToolResult.fail(f"FHIR-DB-Fehler: {exc}")

    if not entries:
        scope = f" für '{search_text}'" if search_text else ""
        return ToolResult.ok({"message": f"Keine FHIR-Daten gefunden{scope}.", "count": 0})

    lines = [_format_resource(e) for e in entries[:100]]
    return ToolResult.ok({
        "count": len(entries),
        "data": "\n".join(lines),
    })


TOOL = Tool(
    name="query_fhir_data",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="personal",
)
