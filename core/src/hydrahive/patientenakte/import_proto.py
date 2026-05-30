"""Import des YAML/CSV-Prototyps (akten/<slug>/) in die Patientenakte.

Idempotent: Patient wird per (owner, slug) wiedergefunden; Einträge tragen eine
deterministische external_id, sodass ein erneuter Lauf upsertet statt dupliziert.
Mapping gemäß Lastenheft §6.
"""
from __future__ import annotations

import csv
import glob
from pathlib import Path
from typing import Any

import yaml

from hydrahive.patientenakte import entities, patients


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _find_patient(user_id: str, slug: str) -> str | None:
    for p in patients.list_for(user_id):
        if p.get("slug") == slug:
            return p["id"]
    return None


def import_akte(user_id: str, slug: str, dir_path: str | Path) -> str:
    d = Path(dir_path)

    # --- Patient (stammdaten) ---
    stamm = _load_yaml(d / "stammdaten.yaml") or {}
    pdata: dict[str, Any] = {"slug": slug}
    for k in ("name", "vorname", "geburtsdatum", "geburtsort", "geschlecht",
              "blutgruppe", "rh_faktor", "email", "beruf", "arbeitgeber"):
        if stamm.get(k):
            pdata[k] = stamm[k]
    if stamm.get("adresse"):
        pdata["adresse"] = stamm["adresse"]
    if stamm.get("versicherung"):
        pdata["versicherung"] = stamm["versicherung"]
    if stamm.get("notfall_kontakt") or stamm.get("notfallkontakt"):
        pdata["notfallkontakt"] = stamm.get("notfall_kontakt") or stamm.get("notfallkontakt")

    pid = _find_patient(user_id, slug)
    if pid:
        patients.update(user_id, pid, pdata)
    else:
        pid = patients.create(user_id, pdata)

    def _add(entity: str, suffix: str, data: dict[str, Any]) -> None:
        rec = dict(data)
        rec.setdefault("external_id", f"proto:{slug}:{entity}:{suffix}")
        rec.setdefault("quelle", "YAML-Prototyp")
        rec.setdefault("verifiziert", False)
        entities.create(user_id, pid, entity, rec)

    # --- Diagnosen ---
    diag = _load_yaml(d / "diagnosen.yaml") or {}
    for i, c in enumerate(diag.get("diagnosen") or []):
        _add("conditions", str(i), dict(c))

    # --- Medikamente (aktuell / historisch) ---
    med = _load_yaml(d / "medikamente.yaml") or {}
    for label, status in (("medikamente", "aktuell"), ("historische", "historisch")):
        for i, m in enumerate(med.get(label) or []):
            mm = dict(m)
            mm["status"] = status
            if "atc" in mm:
                mm["atc_code"] = mm.pop("atc")
            _add("medications", f"{status}-{i}", mm)

    # --- Ereignisse / Klinik ---
    ev = _load_yaml(d / "ereignisse_klinik.yaml") or {}
    for i, e in enumerate(ev.get("ereignisse") or []):
        ee = dict(e)
        datum = ee.pop("datum", None)
        if datum and " bis " in str(datum):
            a, b = str(datum).split(" bis ", 1)
            ee["datum_von"], ee["datum_bis"] = a.strip(), b.strip()
        elif datum:
            ee["datum_von"] = str(datum)
        if "ort" in ee:
            ee["einrichtung"] = ee.pop("ort")
        verlauf = [str(ee.pop(k)) for k in ("inhalt", "therapie", "befund", "bemerkung") if ee.get(k)]
        if verlauf:
            ee["verlauf"] = "\n\n".join(verlauf)
        _add("events", str(i), ee)
    for key, val in (ev.items() if isinstance(ev, dict) else []):
        if key.startswith("entlassmedikation") and isinstance(val, list):
            for j, line in enumerate(val):
                _add("medications", f"entl-{key}-{j}",
                     {"name": str(line), "status": "entlassung", "quelle": "Entlassbrief"})

    # --- Bildgebung ---
    img = _load_yaml(d / "bildgebung.yaml") or {}
    _IMG_MAP = {"typ": "modalitaet", "serien": "serien_beschreibung",
                "bilder": "anzahl_bilder", "pfad": "dicom_pfad", "kontext": "befund"}
    for i, u in enumerate(img.get("untersuchungen") or []):
        uu = {}
        for k, v in dict(u).items():
            tgt = _IMG_MAP.get(k, k)
            uu[tgt] = str(v) if tgt == "anzahl_bilder" else v
        _add("imaging", str(i), uu)

    # --- Allergien ---
    alg = _load_yaml(d / "allergien.yaml") or {}
    _ALG_MAP = {"stoff": "substanz", "schwere": "schweregrad", "dokumentiert": "festgestellt_am"}
    for i, a in enumerate(alg.get("allergien") or []):
        aa = {_ALG_MAP.get(k, k): v for k, v in dict(a).items()}
        _add("allergies", str(i), aa)

    # --- Ärzte ---
    aer = _load_yaml(d / "aerzte.yaml") or {}
    if isinstance(aer, dict):
        ha = aer.get("hausaerztin") or aer.get("hausarzt")
        if isinstance(ha, dict):
            hh = dict(ha)
            hh["rolle"] = "hausarzt"
            if "praxis" in hh and "name" not in hh:
                hh["name"] = hh.pop("praxis")
            _add("practitioners", "haus", hh)
        for i, fa in enumerate(aer.get("fachaerzte") or []):
            ff = dict(fa)
            ff.setdefault("rolle", "facharzt")
            _add("practitioners", f"fa-{i}", ff)

    # --- Laborwerte (CSV, Batch) ---
    _import_labor_csv(user_id, pid, slug, d, _add)

    # --- Notizen (Markdown) ---
    for mdfile in sorted(d.glob("*.md")):
        _add("notes", mdfile.stem,
             {"titel": mdfile.stem, "inhalt": mdfile.read_text(encoding="utf-8"),
              "kategorie": "zusammenfassung"})

    return pid


def _import_labor_csv(user_id, pid, slug, d: Path, _add) -> None:
    matches = (glob.glob(str(d / "**" / "labor_werte.csv"), recursive=True)
               + glob.glob(str(d.parent / "**" / "labor_werte.csv"), recursive=True))
    if not matches:
        return
    with open(matches[0], encoding="utf-8", newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh)):
            obs = {k.lower(): v for k, v in row.items() if v not in (None, "")}
            wert = obs.get("wert") or obs.get("value")
            try:
                if wert is not None:
                    obs["wert"] = float(str(wert).replace(",", "."))
            except ValueError:
                obs["wert_text"] = str(wert)
                obs.pop("wert", None)
            _add("observations", f"csv-{i}", obs)


if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) != 4:
        print("usage: import_akte_prototype.py <user_id> <slug> <dir>")
        raise SystemExit(2)
    new_pid = import_akte(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"imported patient {sys.argv[2]} -> {new_pid}")
