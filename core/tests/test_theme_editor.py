"""Tests für die Theme-Editor-Persistenz (themes/editor.py).

Schwerpunkt Sicherheit: Über diese Schicht werden Dateien via API geschrieben.
Deshalb explizite Tests für Pfad-Traversal, geschützte Themes und ID-/Route-
Validierung — nicht nur den Happy Path.
"""
import pytest


@pytest.fixture
def theme_env(tmp_path, monkeypatch):
    """Isolierte Theme-Umgebung — repointet themes_frontend_dir in tmp."""
    from hydrahive.settings import settings
    root = tmp_path / "repo" / "frontend" / "src" / "themes"
    monkeypatch.setattr(settings, "base_dir", tmp_path / "repo", raising=False)
    monkeypatch.setattr(settings, "themes_frontend_dir", root, raising=False)
    root.mkdir(parents=True)
    return root


def _make_theme(root, theme_id, name="Test", with_template=True):
    d = root / theme_id
    (d / "templates").mkdir(parents=True)
    (d / "theme.json").write_text(
        f'{{"id":"{theme_id}","name":"{name}","version":"1.0.0","layout":"sidebar"}}'
    )
    if with_template:
        (d / "templates" / "buddy.html").write_text("<hh-buddy/>\n")
    return d


# --- Lesen ------------------------------------------------------------------

def test_list_templates(theme_env):
    from hydrahive.themes import editor
    _make_theme(theme_env, "mytheme")
    (theme_env / "mytheme" / "templates" / "dashboard.html").write_text("<hh-dashboard/>")
    assert editor.list_templates("mytheme") == ["buddy", "dashboard"]


def test_list_templates_empty_when_no_dir(theme_env):
    from hydrahive.themes import editor
    _make_theme(theme_env, "mytheme", with_template=False)
    (theme_env / "mytheme" / "templates").rmdir()
    assert editor.list_templates("mytheme") == []


def test_read_template(theme_env):
    from hydrahive.themes import editor
    _make_theme(theme_env, "mytheme")
    assert editor.read_template("mytheme", "buddy") == "<hh-buddy/>\n"


def test_read_missing_template_returns_empty(theme_env):
    from hydrahive.themes import editor
    _make_theme(theme_env, "mytheme")
    assert editor.read_template("mytheme", "nichtda") == ""


# --- Schreiben (User-Theme) -------------------------------------------------

def test_write_template_roundtrip(theme_env):
    from hydrahive.themes import editor
    _make_theme(theme_env, "mytheme")
    editor.write_template("mytheme", "buddy", "<hh-menu/>\n<hh-buddy height=\"50vh\"/>")
    assert editor.read_template("mytheme", "buddy") == "<hh-menu/>\n<hh-buddy height=\"50vh\"/>"


def test_write_creates_templates_dir(theme_env):
    from hydrahive.themes import editor
    _make_theme(theme_env, "mytheme", with_template=False)
    (theme_env / "mytheme" / "templates").rmdir()
    editor.write_template("mytheme", "memory", "<hh-memory/>")
    assert (theme_env / "mytheme" / "templates" / "memory.html").is_file()


def test_delete_template(theme_env):
    from hydrahive.themes import editor
    _make_theme(theme_env, "mytheme")
    editor.delete_template("mytheme", "buddy")
    assert not (theme_env / "mytheme" / "templates" / "buddy.html").exists()


# --- Sicherheit: geschützte Themes ------------------------------------------

def test_write_protected_theme_rejected(theme_env):
    from hydrahive.themes import editor
    _make_theme(theme_env, "aurora")
    with pytest.raises(editor.EditorError, match="theme_protected"):
        editor.write_template("aurora", "buddy", "<hh-buddy/>")


def test_delete_protected_theme_rejected(theme_env):
    from hydrahive.themes import editor
    _make_theme(theme_env, "standard")
    with pytest.raises(editor.EditorError, match="theme_protected"):
        editor.delete_template("standard", "buddy")


def test_write_unknown_theme_rejected(theme_env):
    from hydrahive.themes import editor
    with pytest.raises(editor.EditorError, match="theme_not_found"):
        editor.write_template("gibtsnicht", "buddy", "<hh-buddy/>")


# --- Sicherheit: Pfad-Traversal / ungültige Eingaben ------------------------

@pytest.mark.parametrize("bad_id", ["../evil", "foo/bar", "..", "Foo", "a b", "", "foo/../bar"])
def test_invalid_theme_id_rejected(theme_env, bad_id):
    from hydrahive.themes import editor
    with pytest.raises(editor.EditorError):
        editor.read_template(bad_id, "buddy")


@pytest.mark.parametrize("bad_route", ["../../etc/passwd", "foo/bar", "..", "a b", "", "buddy.html"])
def test_invalid_route_rejected(theme_env, bad_route):
    from hydrahive.themes import editor
    _make_theme(theme_env, "mytheme")
    with pytest.raises(editor.EditorError):
        editor.write_template("mytheme", bad_route, "x")


def test_template_size_limit(theme_env):
    from hydrahive.themes import editor
    _make_theme(theme_env, "mytheme")
    with pytest.raises(editor.EditorError, match="too_large"):
        editor.write_template("mytheme", "buddy", "x" * (256 * 1024 + 1))


# --- Fork -------------------------------------------------------------------

def test_fork_copies_and_rewrites_manifest(theme_env):
    from hydrahive.themes import editor
    import json
    _make_theme(theme_env, "aurora", name="Aurora")
    result = editor.fork_theme("aurora", "mytheme", "Mein Theme")
    assert result["id"] == "mytheme"
    # Kopie hat die Templates
    assert editor.read_template("mytheme", "buddy") == "<hh-buddy/>\n"
    # Manifest umgeschrieben
    m = json.loads((theme_env / "mytheme" / "theme.json").read_text())
    assert m["id"] == "mytheme" and m["name"] == "Mein Theme"
    assert m["author"] == "user"
    # Und die Kopie ist editierbar (nicht geschützt)
    editor.write_template("mytheme", "buddy", "<hh-menu/>")
    assert editor.read_template("mytheme", "buddy") == "<hh-menu/>"


def test_fork_rejects_existing_target(theme_env):
    from hydrahive.themes import editor
    _make_theme(theme_env, "aurora")
    _make_theme(theme_env, "mytheme")
    with pytest.raises(editor.EditorError, match="ziel_existiert"):
        editor.fork_theme("aurora", "mytheme", "X")


def test_fork_rejects_protected_target(theme_env):
    from hydrahive.themes import editor
    _make_theme(theme_env, "aurora")
    with pytest.raises(editor.EditorError, match="geschuetzt"):
        editor.fork_theme("aurora", "standard", "X")


def test_fork_rejects_missing_source(theme_env):
    from hydrahive.themes import editor
    with pytest.raises(editor.EditorError, match="quelle_nicht_gefunden"):
        editor.fork_theme("gibtsnicht", "mytheme", "X")
