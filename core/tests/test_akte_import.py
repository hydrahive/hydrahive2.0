from __future__ import annotations

import textwrap
from pathlib import Path

from hydrahive.patientenakte import entities, patients
from hydrahive.patientenakte.import_proto import import_akte


def _write(tmp: Path, name: str, content: str):
    (tmp / name).write_text(textwrap.dedent(content), encoding="utf-8")


def test_import_maps_stammdaten_diagnosen_medications(tmp_path):
    _write(tmp_path, "stammdaten.yaml", """
        name: "Molke"
        vorname: "Alexander"
        geburtsdatum: "1970-07-31"
        adresse: {strasse: "Hahnenkammstr. 11", plz: "60388", ort: "Frankfurt am Main", land: "Deutschland"}
        versicherung: {krankenkasse: {name: "TK"}}
    """)
    _write(tmp_path, "diagnosen.yaml", """
        diagnosen:
          - diagnose: "Diabetes mellitus Typ 2"
            icd_code: "E11"
            status: "chronisch"
            quelle: "abgeleitet"
    """)
    _write(tmp_path, "medikamente.yaml", """
        medikamente:
          - {name: "Metformin", wirkstoff: "Metformin", atc: "A10BA02"}
        historische:
          - {name: "Insulin", wirkstoff: "Insulin", atc: "A10AE05"}
    """)
    pid = import_akte("u1", "alex", tmp_path)
    p = patients.get("u1", pid)
    assert p["name"] == "Molke"
    assert p["adresse"]["ort"] == "Frankfurt am Main"
    assert p["versicherung"]["krankenkasse"]["name"] == "TK"

    conds = entities.list_for("u1", pid, "conditions")
    assert any(c["icd_code"] == "E11" for c in conds)

    meds = {m["name"]: m for m in entities.list_for("u1", pid, "medications")}
    assert meds["Metformin"]["status"] == "aktuell"
    assert meds["Metformin"]["atc_code"] == "A10BA02"   # atc -> atc_code gemappt
    assert meds["Insulin"]["status"] == "historisch"


def test_import_maps_events_with_date_range_and_arrays(tmp_path):
    _write(tmp_path, "ereignisse_klinik.yaml", """
        ereignisse:
          - datum: "2024-11-15 bis 2024-11-26"
            typ: "Stationaerer Aufenthalt + OP"
            ort: "Sankt Katharinen-Krankenhaus"
            hauptdiagnose: "Leberabszess"
            nebendiagnosen: ["Hypertonie", "Diabetes"]
            therapie: "Cholezystektomie"
    """)
    pid = import_akte("u1", "alex", tmp_path)
    ev = entities.list_for("u1", pid, "events")[0]
    assert ev["datum_von"] == "2024-11-15"
    assert ev["datum_bis"] == "2024-11-26"
    assert ev["einrichtung"] == "Sankt Katharinen-Krankenhaus"   # ort -> einrichtung
    assert ev["nebendiagnosen"] == ["Hypertonie", "Diabetes"]    # array roundtrip
    assert "Cholezystektomie" in ev["verlauf"]                   # therapie -> verlauf


def test_import_maps_imaging_and_practitioners(tmp_path):
    _write(tmp_path, "bildgebung.yaml", """
        untersuchungen:
          - {datum: "2025-03-26", typ: "CT", region: "Abdomen", bilder: "831", pfad: "x/y"}
    """)
    _write(tmp_path, "aerzte.yaml", """
        hausaerztin: {praxis: "Dres. Arning-Erb", fach: "Allgemeinmedizin"}
        fachaerzte:
          - {fach: "Chirurgie", name: "Dr. Morlang", einrichtung: "St. Katharinen"}
    """)
    pid = import_akte("u1", "alex", tmp_path)
    img = entities.list_for("u1", pid, "imaging")[0]
    assert img["modalitaet"] == "CT"            # typ -> modalitaet
    assert img["anzahl_bilder"] == "831"        # bilder -> anzahl_bilder
    assert img["dicom_pfad"] == "x/y"           # pfad -> dicom_pfad
    roles = {pr["rolle"] for pr in entities.list_for("u1", pid, "practitioners")}
    assert roles == {"hausarzt", "facharzt"}


def test_import_is_idempotent(tmp_path):
    _write(tmp_path, "diagnosen.yaml", """
        diagnosen:
          - {diagnose: "X", icd_code: "E11", status: "chronisch"}
    """)
    pid1 = import_akte("u1", "alex", tmp_path)
    pid2 = import_akte("u1", "alex", tmp_path)   # zweiter Lauf
    assert pid1 == pid2                            # gleicher Patient (per slug)
    assert len(patients.list_for("u1")) == 1
    assert len(entities.list_for("u1", pid1, "conditions")) == 1


def test_import_empty_allergies_no_error(tmp_path):
    _write(tmp_path, "allergien.yaml", "allergien: []\n")
    pid = import_akte("u1", "alex", tmp_path)
    assert entities.list_for("u1", pid, "allergies") == []
