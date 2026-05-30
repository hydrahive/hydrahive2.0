import type { AkteEntityKey } from "./api"

export type FieldType = "text" | "number" | "date" | "textarea" | "select"

export interface FieldDef {
  key: string
  label: string
  type: FieldType
  required?: boolean
  options?: string[]      // für type: "select"
  placeholder?: string
}

// Feld-Definitionen je Entität — gespiegelt von core schema.py ENTITIES.
// Pflichtfeld pro Entität ist das Haupt-Label-Feld (sonst leerer Eintrag).
export const ENTITY_FIELDS: Record<AkteEntityKey, FieldDef[]> = {
  conditions: [
    { key: "diagnose", label: "Diagnose", type: "text", required: true },
    { key: "icd_code", label: "ICD-Code", type: "text", placeholder: "z.B. E11.9" },
    { key: "status", label: "Status", type: "select", options: ["aktuell", "chronisch", "ausgeheilt", "verdacht"] },
    { key: "diagnostiziert_am", label: "Diagnostiziert am", type: "date" },
    { key: "arzt", label: "Arzt", type: "text" },
    { key: "koerperstelle", label: "Körperstelle", type: "text" },
    { key: "erstmanifestation", label: "Erstmanifestation", type: "text" },
    { key: "bemerkungen", label: "Bemerkungen", type: "textarea" },
  ],
  medications: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "wirkstoff", label: "Wirkstoff", type: "text" },
    { key: "atc_code", label: "ATC-Code", type: "text" },
    { key: "klasse", label: "Klasse", type: "text" },
    { key: "dosierung", label: "Dosierung", type: "text", placeholder: "z.B. 1-0-1" },
    { key: "beginn", label: "Beginn", type: "date" },
    { key: "ende", label: "Ende", type: "date" },
    { key: "arzt", label: "Arzt", type: "text" },
    { key: "zweck", label: "Zweck", type: "text" },
    { key: "status", label: "Status", type: "select", options: ["aktuell", "historisch", "entlassung"] },
    { key: "letzte_verordnung", label: "Letzte Verordnung", type: "date" },
  ],
  observations: [
    { key: "parameter", label: "Parameter", type: "text", required: true, placeholder: "z.B. HbA1c" },
    { key: "wert", label: "Wert (Zahl)", type: "number" },
    { key: "wert_text", label: "Wert (Text)", type: "text", placeholder: "falls nicht numerisch, z.B. negativ" },
    { key: "einheit", label: "Einheit", type: "text", placeholder: "z.B. %" },
    { key: "referenz_min", label: "Referenz min", type: "number" },
    { key: "referenz_max", label: "Referenz max", type: "number" },
    { key: "flag", label: "Flag", type: "select", options: ["normal", "high", "low"] },
    { key: "datum", label: "Datum", type: "date" },
    { key: "labor", label: "Labor", type: "text" },
    { key: "material", label: "Material", type: "text" },
  ],
  events: [
    { key: "typ", label: "Typ", type: "text", required: true, placeholder: "z.B. Stationärer Aufenthalt" },
    { key: "datum_von", label: "Datum von", type: "date" },
    { key: "datum_bis", label: "Datum bis", type: "date" },
    { key: "einrichtung", label: "Einrichtung", type: "text" },
    { key: "fachabteilung", label: "Fachabteilung", type: "text" },
    { key: "fallnummer", label: "Fallnummer", type: "text" },
    { key: "hauptdiagnose", label: "Hauptdiagnose", type: "text" },
    { key: "verlauf", label: "Verlauf", type: "textarea" },
  ],
  imaging: [
    { key: "modalitaet", label: "Modalität", type: "text", required: true, placeholder: "z.B. CT, MRT" },
    { key: "datum", label: "Datum", type: "date" },
    { key: "region", label: "Region", type: "text" },
    { key: "einrichtung", label: "Einrichtung", type: "text" },
    { key: "ueberweiser", label: "Überweiser", type: "text" },
    { key: "serien_beschreibung", label: "Serien-Beschreibung", type: "text" },
    { key: "anzahl_bilder", label: "Anzahl Bilder", type: "text" },
    { key: "dicom_pfad", label: "DICOM-Pfad", type: "text" },
    { key: "befund", label: "Befund", type: "textarea" },
  ],
  allergies: [
    { key: "substanz", label: "Substanz", type: "text", required: true },
    { key: "reaktion", label: "Reaktion", type: "text" },
    { key: "schweregrad", label: "Schweregrad", type: "select", options: ["leicht", "mittel", "schwer"] },
    { key: "festgestellt_am", label: "Festgestellt am", type: "date" },
  ],
  practitioners: [
    { key: "name", label: "Name", type: "text", required: true },
    { key: "fach", label: "Fach", type: "text" },
    { key: "einrichtung", label: "Einrichtung", type: "text" },
    { key: "adresse", label: "Adresse", type: "text" },
    { key: "telefon", label: "Telefon", type: "text" },
    { key: "rolle", label: "Rolle", type: "select", options: ["hausarzt", "facharzt", "sonstige"] },
  ],
  documents: [
    { key: "titel", label: "Titel", type: "text", required: true },
    { key: "typ", label: "Typ", type: "text" },
    { key: "datum", label: "Datum", type: "date" },
    { key: "datei_pfad", label: "Datei-Pfad", type: "text" },
    { key: "mime_type", label: "MIME-Type", type: "text" },
    { key: "ocr_text", label: "OCR-Text", type: "textarea" },
  ],
  notes: [
    { key: "titel", label: "Titel", type: "text", required: true },
    { key: "inhalt", label: "Inhalt", type: "textarea" },
    { key: "kategorie", label: "Kategorie", type: "text" },
    { key: "datum", label: "Datum", type: "date" },
  ],
}
