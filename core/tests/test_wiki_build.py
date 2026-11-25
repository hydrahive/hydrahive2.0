"""Wiki und PDF-Handbuch aus den Repos (Ziel hydrahive2-modules/ziele/wiki-automatik.md, WK1–WK4)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WIKI = REPO / "scripts" / "wiki"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"wiki_{name}", WIKI / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(WIKI))
    spec.loader.exec_module(mod)
    return mod


build = _load("build")
pdf_html = _load("pdf_html")
pages = _load("pages")


@pytest.fixture
def repos(tmp_path):
    """Kern- und Modul-Checkout mit je einem Artikel für jede Seite aus pages.py – außer zwei absichtlichen Lücken."""
    core, mods = tmp_path / "core", tmp_path / "mods"
    missing = {("core", "vault"), ("mod", "vr")}
    for _, items in pages.SECTIONS:
        for slug, title, (kind, name) in items:
            if kind == "text" or (kind, name) in missing:
                continue
            p = (core / "frontend/src/i18n/help/de" / f"{name}.md" if kind == "core"
                 else mods / name / "frontend/help/de" / f"{name}.md")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"# {name} – Titel\n\nText zu {name}. Siehe auch **{slug}**.\n\n*Stand: {name} 1.0*\n")
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "Alt-aus-Discord.md").write_text("alt")
    return core, mods, wiki


def test_baut_kern_und_modul_seiten_mit_seitenleiste(repos):
    core, mods, wiki = repos
    written, gaps, problems = build.build(core, mods, wiki)
    assert problems == []
    assert "Buddy" in written and "Haushaltsbuch" in written                  # Kern + Modul
    buddy = (wiki / "Buddy.md").read_text()
    assert buddy.startswith("# 🤖 Buddy") and "# buddy – Titel" not in buddy   # H1 aus dem Wiki-Titel
    assert "Kern-Repo `frontend/src/i18n/help/de/buddy.md`" in buddy
    assert "Modul-Repo `haushaltsbuch/frontend/help/de/haushaltsbuch.md`" in (wiki / "Haushaltsbuch.md").read_text()
    side = (wiki / "_Sidebar.md").read_text()
    assert side.index("**🚀 Einstieg**") < side.index("**🖥️ Server & Betrieb**")
    assert "PDF" in (wiki / "Home.md").read_text()


def test_keine_discord_quelle_im_werkzeug():
    for f in ("build.py", "pages.py", "pdf_html.py"):
        src = (WIKI / f).read_text(encoding="utf-8").lower()
        assert "discord.com/channels" not in src and "handbuch-2026" not in src and "/_work" not in src, f
    kinds = {src[0] for _, items in pages.SECTIONS for _, _, src in items}
    assert kinds <= {"core", "mod", "text"}


def test_luecke_seite_fehlt_bau_laeuft(repos):
    core, mods, wiki = repos
    written, gaps, problems = build.build(core, mods, wiki)
    assert "Vault" not in written and "HydraVR" not in written
    assert any(g.startswith("Vault:") for g in gaps) and any(g.startswith("HydraVR:") for g in gaps)
    assert "[[" + "Vault" not in (wiki / "_Sidebar.md").read_text()            # nicht verlinkt
    assert problems == []


def test_alte_seiten_werden_entfernt(repos):
    core, mods, wiki = repos
    written, _, _ = build.build(core, mods, wiki)
    gone = build.remove_stale(wiki, written)
    assert gone == ["Alt-aus-Discord"] and not (wiki / "Alt-aus-Discord.md").exists()
    assert (wiki / "Home.md").exists() and (wiki / "_Sidebar.md").exists()


@pytest.mark.parametrize("leak", ["Server 192.168.178.2", "auf hydrahive-master", "unter /srv/hh-arbeit",
                                  "Token ghp_abcdefghijklmnopqrstuvwxyz12", "frag Till"])
def test_datenschutz_bricht_ab(repos, leak, capsys):
    core, mods, wiki = repos
    p = core / "frontend/src/i18n/help/de/buddy.md"
    p.write_text(p.read_text() + f"\n{leak}\n")
    assert build.main(["x", str(core), str(mods), str(wiki)]) == 1
    assert "DATENSCHUTZ" in capsys.readouterr().out


def test_ohne_treffer_exit_0(repos):
    core, mods, wiki = repos
    assert build.main(["x", str(core), str(mods), str(wiki)]) == 0


def test_echte_artikel_des_repos_sind_sauber():
    """Die Kern-Hilfe dieses Checkouts besteht die Datenschutz-Prüfung (Modul-Repo prüft der Workflow)."""
    hits = []
    for p in (REPO / "frontend/src/i18n/help/de").glob("*.md"):
        hits += build.check_public(p.stem, p.read_text(encoding="utf-8"))
    for p in (WIKI / "texts").glob("*.md"):
        hits += build.check_public(p.stem, p.read_text(encoding="utf-8"))
    assert hits == []


def test_pdf_dokument_mit_inhalt_und_spruengen(repos):
    core, mods, wiki = repos
    build.build(core, mods, wiki)
    doc = pdf_html.document(wiki, lambda md: f"<pre>{md}</pre>", "23.11.2026")
    assert "HydraHive-Handbuch" in doc and "Stand: 23.11.2026" in doc and "<h1>Inhalt</h1>" in doc
    assert 'id="p-buddy"' in doc and 'href="#p-buddy"' in doc
    assert 'id="p-home"' in doc
    assert "[[" not in doc.replace("[[🏠", "")                                 # alle Wiki-Links aufgelöst
    assert doc.index('id="p-was-ist-hydrahive"') < doc.index('id="p-hydravr"' if 'id="p-hydravr"' in doc
                                                             else 'id="p-vibe"')


def test_unbekannter_wikilink_wird_text():
    assert pdf_html.wikilinks("[[Gibts nicht|Nirgends]] und [[Buddy]]", {"Buddy"}) == \
        "Gibts nicht und [Buddy](#p-buddy)"


def test_workflow_baut_wiki_und_pdf_und_haengt_an_festen_release():
    wf = (REPO / ".github/workflows/wiki.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch" in wf and "schedule" in wf and "frontend/src/i18n/help/de/**" in wf
    assert "scripts/wiki/build.py . _modules _wiki" in wf and "repository: hydrahive/hydrahive2-modules" in wf
    assert "pdf_html.py" in wf and "pdf_print.py" in wf
    assert "gh release upload handbuch HydraHive-Handbuch.pdf --clobber" in wf
    assert "contents: write" in wf
    # Wiki-Startseite verlinkt genau diese Adresse
    home = (WIKI / "texts" / "Home.md").read_text(encoding="utf-8")
    assert "releases/download/handbuch/HydraHive-Handbuch.pdf" in home
