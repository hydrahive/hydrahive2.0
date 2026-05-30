"""Registry der Patientenakte-Entitäten — bildet API-Felder auf SQL-Spalten ab.

Die SQL-Migration (023) ist die DDL-Quelle; diese Registry mappt die API auf
die Spalten. Ein Guard-Test (PRAGMA table_info) erzwingt Konsistenz.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntitySpec:
    key: str                              # API-Pfadsegment, z.B. "conditions"
    table: str                            # SQL-Tabelle, z.B. "akte_condition"
    label: str                            # UI-Label
    fields: tuple[str, ...]               # getypte Spalten (API akzeptiert/liefert)
    date_field: str | None = None         # speist sort_date
    array_fields: tuple[str, ...] = ()    # -> extra_json
    numeric_fields: tuple[str, ...] = ()  # in REST als Zahl casten


COMMON_FIELDS = ("external_id", "quelle", "confidence", "verifiziert")

ENTITIES: dict[str, EntitySpec] = {
    "conditions": EntitySpec(
        "conditions", "akte_condition", "Diagnosen",
        ("diagnose", "icd_code", "status", "diagnostiziert_am", "arzt",
         "koerperstelle", "erstmanifestation", "bemerkungen"),
        date_field="diagnostiziert_am"),
    "medications": EntitySpec(
        "medications", "akte_medication", "Medikamente",
        ("name", "wirkstoff", "atc_code", "klasse", "dosierung", "beginn", "ende",
         "arzt", "zweck", "status", "letzte_verordnung"),
        date_field="beginn", array_fields=("nebenwirkungen",)),
    "observations": EntitySpec(
        "observations", "akte_observation", "Laborwerte",
        ("parameter", "wert", "wert_text", "einheit", "referenz_min", "referenz_max",
         "flag", "datum", "labor", "material"),
        date_field="datum", numeric_fields=("wert", "referenz_min", "referenz_max")),
    "events": EntitySpec(
        "events", "akte_encounter", "Ereignisse",
        ("datum_von", "datum_bis", "typ", "einrichtung", "fachabteilung", "fallnummer",
         "hauptdiagnose", "verlauf"),
        date_field="datum_von",
        array_fields=("nebendiagnosen", "prozeduren", "op_codes", "entlassmedikation")),
    "imaging": EntitySpec(
        "imaging", "akte_imaging", "Bildgebung",
        ("datum", "modalitaet", "region", "einrichtung", "ueberweiser",
         "serien_beschreibung", "anzahl_bilder", "dicom_pfad", "befund"),
        date_field="datum", array_fields=("vorschau_bilder",)),
    "allergies": EntitySpec(
        "allergies", "akte_allergy", "Allergien",
        ("substanz", "reaktion", "schweregrad", "festgestellt_am"),
        date_field="festgestellt_am"),
    "practitioners": EntitySpec(
        "practitioners", "akte_practitioner", "Ärzte",
        ("name", "fach", "einrichtung", "adresse", "telefon", "rolle")),
    "documents": EntitySpec(
        "documents", "akte_document", "Dokumente",
        ("titel", "typ", "datum", "datei_pfad", "mime_type", "ocr_text"),
        date_field="datum", array_fields=("verknuepfte_entitaeten",)),
    "notes": EntitySpec(
        "notes", "akte_note", "Notizen",
        ("titel", "inhalt", "kategorie", "datum"),
        date_field="datum"),
}
