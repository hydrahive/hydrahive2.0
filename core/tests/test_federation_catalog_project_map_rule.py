"""G3/P1 — Regel der Projektzuordnung (docs/specs/federation-shared-tasks.md §Projektzuordnung):
manuell → gleicher Name (getrimmt, ohne Groß/Klein, Mitglied, Admin jedes) → nicht zugeordnet.
Reine Rechnung mit Projekten als Dicts; nichts wird gespeichert.
"""
from __future__ import annotations

from hydrahive.federation import catalog_project_map as pm

FP = "fp-o"


def _p(pid, name, *, members=("till",), created_by="root"):
    return {"id": pid, "name": name, "created_by": created_by, "members": [{"username": m, "role": "write"}
                                                                           for m in members]}


def _r(projects, manual=None, *, user="till", admin=False):
    return pm.Resolver(user, is_admin=admin, projects=projects, manual=manual or {})


def test_gleicher_name_getrimmt_und_ohne_gross_klein():
    r = _r([_p("p1", "Hydrahive DEV")])
    a = r.resolve(FP, "o-1", "  hydrahive   dev ")
    assert a == pm.Assignment("p1", False, pm.NAME) and a.assigned


def test_kein_treffer():
    assert _r([_p("p1", "Garten")]).resolve(FP, "o-1", "Hydrahive DEV").reason == pm.NO_MATCH


def test_mehrdeutig_keine_automatische_zuordnung():
    a = _r([_p("p1", "Hydrahive DEV"), _p("p2", "hydrahive dev")]).resolve(FP, "o-1", "Hydrahive DEV")
    assert a.local_project_id is None and a.reason == pm.AMBIGUOUS


def test_nicht_mitglied_aber_admin_darf():
    projects = [_p("p1", "Hydrahive DEV", members=("anna",))]
    assert _r(projects).resolve(FP, "o-1", "Hydrahive DEV").reason == pm.NOT_MEMBER
    assert _r(projects, admin=True).resolve(FP, "o-1", "Hydrahive DEV").local_project_id == "p1"


def test_ersteller_zaehlt_als_mitglied():
    a = _r([_p("p1", "Hydrahive DEV", members=(), created_by="till")]).resolve(FP, "o-1", "Hydrahive DEV")
    assert a.local_project_id == "p1"


def test_manuell_geht_vor_name_und_bleibt_bei_umbenennung():
    projects = [_p("p1", "Hydrahive DEV"), _p("p2", "Anderes")]
    r = _r(projects, {(FP, "o-1"): "p2"})
    assert r.resolve(FP, "o-1", "Hydrahive DEV") == pm.Assignment("p2", False, pm.MANUAL)
    assert r.resolve(FP, "o-1", "Neuer Name").local_project_id == "p2"   # Ursprung hat umbenannt


def test_automatisch_wandert_mit_dem_namen():
    r = _r([_p("p1", "Hydrahive DEV"), _p("p2", "Hydrahive NEU")])
    assert r.resolve(FP, "o-1", "Hydrahive DEV").local_project_id == "p1"
    assert r.resolve(FP, "o-1", "Hydrahive NEU").local_project_id == "p2"


def test_hidden_blendet_aus():
    a = _r([_p("p1", "Hydrahive DEV")], {(FP, "o-1"): pm.HIDDEN}).resolve(FP, "o-1", "Hydrahive DEV")
    assert a == pm.Assignment(None, True, pm.HIDDEN_REASON) and not a.assigned


def test_manuelles_ziel_weg_oder_kein_mitglied_mehr():
    r = _r([_p("p2", "X", members=("anna",))], {(FP, "o-1"): "p2", (FP, "o-2"): "geloescht"})
    assert r.resolve(FP, "o-1", "X").reason == pm.TARGET_GONE           # nicht mehr Mitglied
    assert r.resolve(FP, "o-2", "X").reason == pm.TARGET_GONE           # Projekt gelöscht


def test_zuordnung_je_ursprung_getrennt():
    r = _r([_p("p1", "Hydrahive DEV"), _p("p2", "B")], {("fp-anderer", "o-1"): "p2"})
    assert r.resolve(FP, "o-1", "Hydrahive DEV").local_project_id == "p1"


def test_ohne_projekt_beim_ursprung_und_leerer_name():
    r = _r([_p("p1", "")])
    assert r.resolve(FP, None, "Hydrahive DEV").reason == pm.NO_PROJECT
    assert r.resolve(FP, "o-1", "   ").reason == pm.NO_MATCH            # leerer Name trifft nichts
