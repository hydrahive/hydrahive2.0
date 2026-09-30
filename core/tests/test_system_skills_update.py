"""System-Skills aktualisieren, Admin-Änderungen schützen (docs/specs/system-skills-update.md).

Befund 30.09.2026: install_system_defaults() kopierte nur fehlende Dateien, 7 von 22
System-Skills waren live auf alten Repo-Ständen (u. a. medical-akte mit toten Pfaden).
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import pytest

from hydrahive.skills import loader

DEFAULTS = Path(loader.__file__).parent / "system_defaults"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Eigene Quelle + Ziel, damit nichts Echtes berührt wird."""
    src = tmp_path / "defaults"
    dst = tmp_path / "live"
    src.mkdir()
    monkeypatch.setattr(loader, "_DEFAULTS_SRC", src)
    monkeypatch.setattr(loader, "system_dir", lambda: dst)
    return src, dst


def _ship(src: Path, name: str, current: str, older: list[str]) -> None:
    (src / name).write_text(current, encoding="utf-8")
    hist_path = src / "_history.json"
    hist = json.loads(hist_path.read_text()) if hist_path.exists() else {}
    hist[name] = [_sha(t) for t in older + [current]]
    hist_path.write_text(json.dumps(hist))


def test_missing_skill_is_installed(env):
    src, dst = env
    _ship(src, "a.md", "neu", [])
    loader.install_system_defaults()
    assert (dst / "a.md").read_text() == "neu"


def test_old_shipped_version_is_updated(env, caplog):
    src, dst = env
    _ship(src, "a.md", "Fassung 3", ["Fassung 1", "Fassung 2"])
    dst.mkdir()
    (dst / "a.md").write_text("Fassung 1", encoding="utf-8")
    with caplog.at_level(logging.INFO):
        loader.install_system_defaults()
    assert (dst / "a.md").read_text() == "Fassung 3"
    assert any("aktualisiert" in r.getMessage() and "a.md" in r.getMessage() for r in caplog.records)


def test_admin_edit_is_kept(env, caplog):
    src, dst = env
    _ship(src, "a.md", "Fassung 2", ["Fassung 1"])
    dst.mkdir()
    (dst / "a.md").write_text("Fassung 1 + Admin-Ergänzung", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        loader.install_system_defaults()
    assert (dst / "a.md").read_text() == "Fassung 1 + Admin-Ergänzung"
    assert any("weicht ab" in r.getMessage() and "a.md" in r.getMessage() for r in caplog.records)


def test_current_version_untouched(env):
    src, dst = env
    _ship(src, "a.md", "aktuell", ["alt"])
    dst.mkdir()
    target = dst / "a.md"
    target.write_text("aktuell", encoding="utf-8")
    mtime = target.stat().st_mtime_ns
    loader.install_system_defaults()
    assert target.stat().st_mtime_ns == mtime


def test_skill_without_history_entry_is_never_overwritten(env):
    src, dst = env
    (src / "b.md").write_text("neu", encoding="utf-8")
    (src / "_history.json").write_text("{}")
    dst.mkdir()
    (dst / "b.md").write_text("irgendwas", encoding="utf-8")
    loader.install_system_defaults()
    assert (dst / "b.md").read_text() == "irgendwas"


def test_missing_or_broken_history_file_is_safe(env):
    src, dst = env
    (src / "c.md").write_text("neu", encoding="utf-8")
    (src / "_history.json").write_text("{kaputt")
    dst.mkdir()
    (dst / "c.md").write_text("alt", encoding="utf-8")
    loader.install_system_defaults()
    assert (dst / "c.md").read_text() == "alt"


def test_update_is_atomic_no_temp_files_left(env):
    src, dst = env
    _ship(src, "a.md", "neu", ["alt"])
    dst.mkdir()
    (dst / "a.md").write_text("alt", encoding="utf-8")
    loader.install_system_defaults()
    assert sorted(p.name for p in dst.iterdir()) == ["a.md"]


# ── Die echte Auslieferung ────────────────────────────────────────────────

def test_every_shipped_skill_current_version_is_in_history():
    """Wer einen System-Skill ändert, muss _history.json nachziehen
    (scripts/update_skill_history.py), sonst wird die nächste Änderung nie ausgerollt."""
    hist = json.loads((DEFAULTS / "_history.json").read_text(encoding="utf-8"))
    for f in sorted(DEFAULTS.glob("*.md")):
        assert f.name in hist, f"{f.name} fehlt in _history.json"
        assert _sha(f.read_text(encoding="utf-8")) in hist[f.name], f"aktuelle Fassung von {f.name} fehlt in _history.json"


def test_history_contains_the_old_live_versions_found_on_30_09():
    """Die 7 live veralteten Stände vom 30.09.2026 müssen erkannt werden."""
    hist = json.loads((DEFAULTS / "_history.json").read_text(encoding="utf-8"))
    for name in ("code-graph.md", "code-review.md", "debugging.md", "generate-music.md",
                 "generate-speech.md", "hh-review.md", "medical-akte.md"):
        assert len(hist[name]) >= 2, f"{name}: frühere Fassungen fehlen"


# ── medical-akte: Pfade, Port, Zugang ─────────────────────────────────────

_MODULE_ROUTES = Path(__file__).resolve().parents[3] / "hydrahive2-modules" / "patientenakte" / "backend" / "routes.py"


def _skill_text() -> str:
    return (DEFAULTS / "medical-akte.md").read_text(encoding="utf-8")


def test_medical_akte_uses_default_port_and_no_key_in_calls():
    text = _skill_text()
    assert "127.0.0.1:8000" not in text
    assert "127.0.0.1:8001/api/modules/patientenakte/akte" in text
    assert "Authorization" not in text, "Key gehört ins Credential-Profil, nicht in den Tool-Aufruf"
    assert "Credential-Profil" in text


@pytest.mark.skipif(not _MODULE_ROUTES.exists(), reason="Modul-Repo nicht neben dem Core ausgecheckt")
def test_medical_akte_paths_exist_as_module_routes():
    """Jeder Pfad im Skill passt auf eine Route des Moduls; {entity} steht für eine echte Entität."""
    import re
    routes_src = _MODULE_ROUTES.read_text(encoding="utf-8")
    schema_src = (_MODULE_ROUTES.parent / "schema.py").read_text(encoding="utf-8")
    entities = set(re.findall(r'^    "([a-z_]+)": EntitySpec\(', schema_src, re.M))
    prefix = re.search(r'APIRouter\(prefix="([^"]+)"', routes_src).group(1)
    routes = [prefix + p for p in re.findall(r'@router\.(?:get|post|patch|put|delete)\("([^"]*)"', routes_src)]

    def matches(path: str) -> bool:
        parts = path.strip("/").split("/")
        for route in routes:
            rparts = route.strip("/").split("/")
            if len(rparts) != len(parts):
                continue
            if all(r == p or (r == "{entity}" and (p in entities or p == "{entity}"))
                   or (r.startswith("{") and r != "{entity}") for r, p in zip(rparts, parts)):
                return True
        return False

    text = _skill_text()
    used = set(re.findall(r"/api/modules/patientenakte(/akte[a-z/_{}]*)", text))
    used |= {"/akte" + (p if p != "/" else "") for p in re.findall(r"^(?:GET|POST|PATCH|DELETE)\s+(/\S*)", text, re.M)}
    missing = sorted(u for u in used if not matches(u))
    assert used and not missing, f"Pfade im Skill ohne Route: {missing}"
    block = text[text.index("`{entity}` ∈"):text.index("```", text.index("`{entity}` ∈"))]
    listed = set(re.findall(r"`([a-z_]+)`", block))
    assert listed == entities, f"Entitäten im Skill {sorted(listed)} ≠ Modul {sorted(entities)}"
