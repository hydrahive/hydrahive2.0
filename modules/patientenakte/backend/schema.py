"""Registry der Patientenakte-Entitäten — die EINE Quelle der Wahrheit (SSOT).

Die SQL-Migration (023) ist die DDL-Quelle; diese Registry mappt die API auf
die Spalten UND trägt die UI-Metadaten (Formularfelder, Label-Felder, Listen-
Spalten). Frontend zieht sie über GET /api/modules/patientenakte/akte/_schema und
rendert generisch — kein handgespiegeltes akteFields.ts / ENTITY_COLUMNS mehr.

Guard-Tests (test_akte_schema.py) erzwingen Konsistenz:
- ui_fields-Keys existieren als Spalten (PRAGMA table_info)
- label_fields / list_columns / numeric_fields ⊆ fields
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Erlaubte Frontend-Eingabetypen (gespiegelt in FieldType der UI).
FieldType = str  # "text" | "number" | "date" | "textarea" | "select"


@dataclass(frozen=True)
class FieldSpec:
    """Ein Formularfeld einer Entität — speist sowohl Eingabe als auch Anzeige."""
    key: str
    label: str
    type: FieldType = "text"
    required: bool = False
    options: tuple[str, ...] = ()      # für type="select"
    placeholder: str = ""


@dataclass(frozen=True)
class EntitySpec:
    key: str                              # API-Pfadsegment, z.B. "conditions"
    table: str                            # SQL-Tabelle, z.B. "akte_condition"
    label: str                            # UI-Label, z.B. "Diagnosen"
    ui_fields: tuple[FieldSpec, ...]      # SSOT der getypten Felder (= Spalten)
    label_fields: tuple[str, ...]         # Reihenfolge für die Label-Ableitung
    list_columns: tuple[str, ...] = ()    # Daten-Spalten der Listenansicht
    date_field: str | None = None         # speist sort_date
    array_fields: tuple[str, ...] = ()    # -> extra_json
    numeric_fields: tuple[str, ...] = ()  # in REST als Zahl casten

    @property
    def fields(self) -> tuple[str, ...]:
        """Getypte Spaltennamen — abgeleitet aus ui_fields (keine Doppelung)."""
        return tuple(f.key for f in self.ui_fields)


COMMON_FIELDS = ("external_id", "quelle", "confidence", "verifiziert")


def ui_schema() -> dict[str, Any]:
    """Serialisiert die Registry für das Frontend (GET .../_schema).

    Das ist der Vertrag, den die UI generisch rendert — Formularfelder,
    Label-Ableitung und Listen-Spalten. Eine Quelle, kein Handspiegel.
    """
    return {
        "entities": {
            key: {
                "key": spec.key,
                "label": spec.label,
                "label_fields": list(spec.label_fields),
                "list_columns": list(spec.list_columns),
                "date_field": spec.date_field,
                "numeric_fields": list(spec.numeric_fields),
                "ui_fields": [
                    {
                        "key": f.key,
                        "label": f.label,
                        "type": f.type,
                        "required": f.required,
                        "options": list(f.options),
                        "placeholder": f.placeholder,
                    }
                    for f in spec.ui_fields
                ],
            }
            for key, spec in ENTITIES.items()
        }
    }


def _f(key: str, label: str, type: str = "text", *, required: bool = False,
       options: tuple[str, ...] = (), placeholder: str = "") -> FieldSpec:
    return FieldSpec(key, label, type, required, options, placeholder)


ENTITIES: dict[str, EntitySpec] = {
    "conditions": EntitySpec(
        "conditions", "akte_condition", "Diagnosen",
        ui_fields=(
            _f("diagnose", "Diagnose", required=True),
            _f("icd_code", "ICD-Code", placeholder="z.B. E11.9"),
            _f("status", "Status", "select",
               options=("aktuell", "chronisch", "ausgeheilt", "verdacht")),
            _f("diagnostiziert_am", "Diagnostiziert am", "date"),
            _f("arzt", "Arzt"),
            _f("koerperstelle", "Körperstelle"),
            _f("erstmanifestation", "Erstmanifestation"),
            _f("bemerkungen", "Bemerkungen", "textarea"),
        ),
        label_fields=("diagnose",),
        list_columns=("icd_code", "status"),
        date_field="diagnostiziert_am"),
    "medications": EntitySpec(
        "medications", "akte_medication", "Medikamente",
        ui_fields=(
            _f("name", "Name", required=True),
            _f("wirkstoff", "Wirkstoff"),
            _f("atc_code", "ATC-Code"),
            _f("klasse", "Klasse"),
            _f("dosierung", "Dosierung", placeholder="z.B. 1-0-1"),
            _f("beginn", "Beginn", "date"),
            _f("ende", "Ende", "date"),
            _f("arzt", "Arzt"),
            _f("zweck", "Zweck"),
            _f("status", "Status", "select",
               options=("aktuell", "historisch", "entlassung")),
            _f("letzte_verordnung", "Letzte Verordnung", "date"),
        ),
        label_fields=("name", "wirkstoff"),
        list_columns=("wirkstoff", "dosierung", "status"),
        date_field="beginn", array_fields=("nebenwirkungen",)),
    "observations": EntitySpec(
        "observations", "akte_observation", "Laborwerte",
        ui_fields=(
            _f("parameter", "Parameter", required=True, placeholder="z.B. HbA1c"),
            _f("wert", "Wert (Zahl)", "number"),
            _f("wert_text", "Wert (Text)", placeholder="falls nicht numerisch, z.B. negativ"),
            _f("einheit", "Einheit", placeholder="z.B. %"),
            _f("referenz_min", "Referenz min", "number"),
            _f("referenz_max", "Referenz max", "number"),
            _f("flag", "Flag", "select", options=("normal", "high", "low")),
            _f("datum", "Datum", "date"),
            _f("labor", "Labor"),
            _f("material", "Material"),
        ),
        label_fields=("parameter",),
        list_columns=("wert", "einheit"),
        date_field="datum", numeric_fields=("wert", "referenz_min", "referenz_max")),
    "events": EntitySpec(
        "events", "akte_encounter", "Ereignisse",
        ui_fields=(
            _f("typ", "Typ", required=True, placeholder="z.B. Stationärer Aufenthalt"),
            _f("datum_von", "Datum von", "date"),
            _f("datum_bis", "Datum bis", "date"),
            _f("einrichtung", "Einrichtung"),
            _f("fachabteilung", "Fachabteilung"),
            _f("fallnummer", "Fallnummer"),
            _f("hauptdiagnose", "Hauptdiagnose"),
            _f("verlauf", "Verlauf", "textarea"),
        ),
        label_fields=("typ", "hauptdiagnose", "einrichtung"),
        list_columns=("typ",),
        date_field="datum_von",
        array_fields=("nebendiagnosen", "prozeduren", "op_codes", "entlassmedikation")),
    "imaging": EntitySpec(
        "imaging", "akte_imaging", "Bildgebung",
        ui_fields=(
            _f("modalitaet", "Modalität", required=True, placeholder="z.B. CT, MRT"),
            _f("datum", "Datum", "date"),
            _f("region", "Region"),
            _f("einrichtung", "Einrichtung"),
            _f("ueberweiser", "Überweiser"),
            _f("serien_beschreibung", "Serien-Beschreibung"),
            _f("anzahl_bilder", "Anzahl Bilder"),
            _f("dicom_pfad", "DICOM-Pfad"),
            _f("befund", "Befund", "textarea"),
        ),
        label_fields=("befund", "modalitaet", "region"),
        list_columns=("modalitaet", "region"),
        date_field="datum", array_fields=("vorschau_bilder",)),
    "allergies": EntitySpec(
        "allergies", "akte_allergy", "Allergien",
        ui_fields=(
            _f("substanz", "Substanz", required=True),
            _f("reaktion", "Reaktion"),
            _f("schweregrad", "Schweregrad", "select",
               options=("leicht", "mittel", "schwer")),
            _f("festgestellt_am", "Festgestellt am", "date"),
        ),
        label_fields=("substanz",),
        list_columns=("reaktion", "schweregrad"),
        date_field="festgestellt_am"),
    "practitioners": EntitySpec(
        "practitioners", "akte_practitioner", "Ärzte",
        ui_fields=(
            _f("name", "Name", required=True),
            _f("fach", "Fach"),
            _f("einrichtung", "Einrichtung"),
            _f("adresse", "Adresse"),
            _f("telefon", "Telefon"),
            _f("rolle", "Rolle", "select",
               options=("hausarzt", "facharzt", "sonstige")),
        ),
        label_fields=("name", "einrichtung"),
        list_columns=("fach", "einrichtung")),
    "documents": EntitySpec(
        "documents", "akte_document", "Dokumente",
        ui_fields=(
            _f("titel", "Titel", required=True),
            _f("typ", "Typ"),
            _f("datum", "Datum", "date"),
            _f("datei_pfad", "Datei-Pfad"),
            _f("mime_type", "MIME-Type"),
            _f("ocr_text", "OCR-Text", "textarea"),
        ),
        label_fields=("titel",),
        list_columns=("typ",),
        date_field="datum", array_fields=("verknuepfte_entitaeten",)),
    "notes": EntitySpec(
        "notes", "akte_note", "Notizen",
        ui_fields=(
            _f("titel", "Titel", required=True),
            _f("inhalt", "Inhalt", "textarea"),
            _f("kategorie", "Kategorie"),
            _f("datum", "Datum", "date"),
        ),
        label_fields=("titel",),
        list_columns=("kategorie",),
        date_field="datum"),
}
