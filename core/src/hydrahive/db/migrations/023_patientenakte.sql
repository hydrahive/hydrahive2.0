-- Patientenakte (ePA-light): eigene relationale Domäne, abgegrenzt vom
-- read-only eGA/FHIR-Blob-Store. Gemeinsame Spalten in jeder Entität +
-- entity-spezifische getypte Spalten. FK ON DELETE CASCADE (foreign_keys=ON).

CREATE TABLE akte_patient (
  id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  slug TEXT,
  name TEXT,
  vorname TEXT,
  geburtsdatum TEXT,
  geburtsort TEXT,
  geschlecht TEXT,
  blutgruppe TEXT,
  rh_faktor TEXT,
  adresse_json TEXT,
  telefon_json TEXT,
  email TEXT,
  notfallkontakt_json TEXT,
  versicherung_json TEXT,
  beruf TEXT,
  arbeitgeber TEXT,
  external_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX idx_akte_patient_owner ON akte_patient(owner_user_id);
CREATE UNIQUE INDEX idx_akte_patient_extid
  ON akte_patient(owner_user_id, external_id) WHERE external_id IS NOT NULL;

CREATE TABLE akte_condition (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL REFERENCES akte_patient(id) ON DELETE CASCADE,
  external_id TEXT, quelle TEXT, confidence REAL,
  verifiziert INTEGER NOT NULL DEFAULT 0,
  sort_date TEXT, extra_json TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  diagnose TEXT, icd_code TEXT, status TEXT, diagnostiziert_am TEXT,
  arzt TEXT, koerperstelle TEXT, erstmanifestation TEXT, bemerkungen TEXT
);
CREATE INDEX idx_akte_condition_patient ON akte_condition(patient_id, sort_date);
CREATE UNIQUE INDEX idx_akte_condition_extid
  ON akte_condition(patient_id, external_id) WHERE external_id IS NOT NULL;

CREATE TABLE akte_medication (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL REFERENCES akte_patient(id) ON DELETE CASCADE,
  external_id TEXT, quelle TEXT, confidence REAL,
  verifiziert INTEGER NOT NULL DEFAULT 0,
  sort_date TEXT, extra_json TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  name TEXT, wirkstoff TEXT, atc_code TEXT, klasse TEXT, dosierung TEXT,
  beginn TEXT, ende TEXT, arzt TEXT, zweck TEXT, status TEXT, letzte_verordnung TEXT
);
CREATE INDEX idx_akte_medication_patient ON akte_medication(patient_id, sort_date);
CREATE UNIQUE INDEX idx_akte_medication_extid
  ON akte_medication(patient_id, external_id) WHERE external_id IS NOT NULL;

CREATE TABLE akte_observation (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL REFERENCES akte_patient(id) ON DELETE CASCADE,
  external_id TEXT, quelle TEXT, confidence REAL,
  verifiziert INTEGER NOT NULL DEFAULT 0,
  sort_date TEXT, extra_json TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  parameter TEXT, wert REAL, wert_text TEXT, einheit TEXT,
  referenz_min REAL, referenz_max REAL, flag TEXT, datum TEXT,
  labor TEXT, material TEXT
);
CREATE INDEX idx_akte_observation_patient ON akte_observation(patient_id, sort_date);
CREATE INDEX idx_akte_observation_param ON akte_observation(patient_id, parameter);
CREATE UNIQUE INDEX idx_akte_observation_extid
  ON akte_observation(patient_id, external_id) WHERE external_id IS NOT NULL;

CREATE TABLE akte_encounter (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL REFERENCES akte_patient(id) ON DELETE CASCADE,
  external_id TEXT, quelle TEXT, confidence REAL,
  verifiziert INTEGER NOT NULL DEFAULT 0,
  sort_date TEXT, extra_json TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  datum_von TEXT, datum_bis TEXT, typ TEXT, einrichtung TEXT,
  fachabteilung TEXT, fallnummer TEXT, hauptdiagnose TEXT, verlauf TEXT
);
CREATE INDEX idx_akte_encounter_patient ON akte_encounter(patient_id, sort_date);
CREATE UNIQUE INDEX idx_akte_encounter_extid
  ON akte_encounter(patient_id, external_id) WHERE external_id IS NOT NULL;

CREATE TABLE akte_imaging (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL REFERENCES akte_patient(id) ON DELETE CASCADE,
  external_id TEXT, quelle TEXT, confidence REAL,
  verifiziert INTEGER NOT NULL DEFAULT 0,
  sort_date TEXT, extra_json TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  datum TEXT, modalitaet TEXT, region TEXT, einrichtung TEXT, ueberweiser TEXT,
  serien_beschreibung TEXT, anzahl_bilder TEXT, dicom_pfad TEXT, befund TEXT
);
CREATE INDEX idx_akte_imaging_patient ON akte_imaging(patient_id, sort_date);
CREATE UNIQUE INDEX idx_akte_imaging_extid
  ON akte_imaging(patient_id, external_id) WHERE external_id IS NOT NULL;

CREATE TABLE akte_allergy (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL REFERENCES akte_patient(id) ON DELETE CASCADE,
  external_id TEXT, quelle TEXT, confidence REAL,
  verifiziert INTEGER NOT NULL DEFAULT 0,
  sort_date TEXT, extra_json TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  substanz TEXT, reaktion TEXT, schweregrad TEXT, festgestellt_am TEXT
);
CREATE INDEX idx_akte_allergy_patient ON akte_allergy(patient_id, sort_date);
CREATE UNIQUE INDEX idx_akte_allergy_extid
  ON akte_allergy(patient_id, external_id) WHERE external_id IS NOT NULL;

CREATE TABLE akte_practitioner (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL REFERENCES akte_patient(id) ON DELETE CASCADE,
  external_id TEXT, quelle TEXT, confidence REAL,
  verifiziert INTEGER NOT NULL DEFAULT 0,
  sort_date TEXT, extra_json TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  name TEXT, fach TEXT, einrichtung TEXT, adresse TEXT, telefon TEXT, rolle TEXT
);
CREATE INDEX idx_akte_practitioner_patient ON akte_practitioner(patient_id, sort_date);
CREATE UNIQUE INDEX idx_akte_practitioner_extid
  ON akte_practitioner(patient_id, external_id) WHERE external_id IS NOT NULL;

CREATE TABLE akte_document (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL REFERENCES akte_patient(id) ON DELETE CASCADE,
  external_id TEXT, quelle TEXT, confidence REAL,
  verifiziert INTEGER NOT NULL DEFAULT 0,
  sort_date TEXT, extra_json TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  titel TEXT, typ TEXT, datum TEXT, datei_pfad TEXT, mime_type TEXT, ocr_text TEXT
);
CREATE INDEX idx_akte_document_patient ON akte_document(patient_id, sort_date);
CREATE UNIQUE INDEX idx_akte_document_extid
  ON akte_document(patient_id, external_id) WHERE external_id IS NOT NULL;

CREATE TABLE akte_note (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL REFERENCES akte_patient(id) ON DELETE CASCADE,
  external_id TEXT, quelle TEXT, confidence REAL,
  verifiziert INTEGER NOT NULL DEFAULT 0,
  sort_date TEXT, extra_json TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  titel TEXT, inhalt TEXT, kategorie TEXT, datum TEXT
);
CREATE INDEX idx_akte_note_patient ON akte_note(patient_id, sort_date);
CREATE UNIQUE INDEX idx_akte_note_extid
  ON akte_note(patient_id, external_id) WHERE external_id IS NOT NULL;
