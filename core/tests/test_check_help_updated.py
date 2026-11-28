"""Hilfe-Guard (docs/specs/hilfe-guard.md, Abnahme HG1/HG2): nutzersichtbare Änderung bringt ihre Hilfe mit."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_help_updated.py"
_spec = importlib.util.spec_from_file_location("check_help_updated", _SCRIPT)
guard = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = guard          # @dataclass braucht das Modul in sys.modules
_spec.loader.exec_module(guard)

HELP = "frontend/src/i18n/help/de"


def _eval(files, *, body="", root=None):
    return guard.evaluate(list(files), body=body, root=root)


def _repo(tmp_path, features: dict[str, list[str]], help_articles=("agents", "communication", "users", "jobs")):
    """Mini-Checkout: features = {ordner: [topic, …]} → je eine Datei mit HelpButton-Stellen."""
    base = tmp_path / "frontend" / "src"
    for folder, topics in features.items():
        d = base / "features" / folder
        d.mkdir(parents=True)
        (d / "Page.tsx").write_text("".join(f'<HelpButton topic="{t}" />\n' for t in topics) or "export {}\n")
    h = base / "i18n" / "help" / "de"
    h.mkdir(parents=True)
    for name in help_articles:
        (h / f"{name}.md").write_text("# x\n")
    return tmp_path


# --- nutzersichtbar: je Muster ------------------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "frontend/src/features/communication/CommunicationPage.tsx",
    "frontend/src/features/agents/areas/AreaSwitch.tsx",
    "frontend/src/shared/ui/Button.tsx",
    "frontend/src/i18n/locales/de/agents.json",
    "installer/update.sh",
    "installer/update-mac.sh",
    "installer/lib/update-rollback.sh",
    "installer/lib/update-safety.sh",
    "installer/install.sh",
    "installer/install-mac.sh",
])
def test_nutzersichtbar_wird_erkannt(path):
    result = _eval([path])
    assert result.visible_files == [path]
    assert result.violation


@pytest.mark.parametrize("path", [
    "frontend/src/features/chat/Chat.test.tsx",             # Test
    "frontend/src/shared/ui/Button.test.tsx",               # Test
    "frontend/src/features/chat/tests/helper.tsx",           # tests/-Ordner
    "frontend/src/features/chat/useChat.ts",                 # nur .tsx zählt
    "frontend/src/i18n/locales/en/agents.json",              # nur Deutsch
    "frontend/src/i18n/locales/de/sub/x.json",               # nur direkt unter de/
    "installer/lib/git-update.sh",                           # kein update-*.sh
    "installer/lib/install-choices.sh",                      # nur installer/install*.sh
    "installer/uninstall.sh",
    "docs/specs/hilfe-guard.md",                             # Doku allein löst nichts aus
    "README.md",
    "core/src/hydrahive/api/x.py",
    "core/tests/test_x.py",
    "frontend/src/modules/atelier/AtelierPage.tsx",          # Module haben ihr eigenes Repo/Muster
    f"{HELP}/agents.md",                                     # Hilfe selbst ist nicht „sichtbar“
])
def test_unsichtbar_loest_nichts_aus(path):
    result = _eval([path])
    assert result.visible_files == []
    assert not result.violation
    assert result.ok


def test_tests_und_doku_zusammen_loesen_nichts_aus():
    result = _eval(["frontend/src/features/chat/Chat.test.tsx", "docs/specs/x.md", "core/tests/test_a.py"])
    assert result.ok


# --- Hilfe-Datei ---------------------------------------------------------------------------------------------------

def test_hilfe_datei_geaendert_ist_ok():
    result = _eval(["frontend/src/features/agents/areas/AreaSwitch.tsx", f"{HELP}/agents.md"])
    assert result.help_files == [f"{HELP}/agents.md"]
    assert not result.violation


def test_neue_hilfe_datei_ist_ok():
    assert _eval(["installer/update.sh", f"{HELP}/neuer-artikel.md"]).ok


@pytest.mark.parametrize("other", [
    "docs/help/agents.md",                           # falscher Ordner
    "frontend/src/i18n/help/en/agents.md",           # englische Hilfe zählt nicht (Nicht-Ziel)
    f"{HELP}/agents.txt",                            # kein Markdown
    f"{HELP}/sub/agents.md",                         # nicht direkt unter de/
    "modules/atelier/frontend/help/de/atelier.md",   # Modul-Hilfe zählt im Kern nicht
])
def test_andere_dateien_sind_keine_hilfe(other):
    result = _eval(["frontend/src/features/agents/X.tsx", other])
    assert result.help_files == []
    assert result.violation


# --- Ausnahme ------------------------------------------------------------------------------------------------------

def test_ausnahme_mit_begruendung_ist_ok():
    result = _eval(["frontend/src/features/chat/X.tsx"], body="Text\nKeine Hilfe nötig: reiner Bugfix ohne neue Bedienung\n")
    assert result.exemption == "reiner Bugfix ohne neue Bedienung"
    assert result.ok


def test_ausnahme_genau_zehn_zeichen_reicht():
    assert _eval(["installer/update.sh"], body="Keine Hilfe nötig: 0123456789").ok


def test_ausnahme_zu_kurz_gilt_nicht():
    result = _eval(["installer/update.sh"], body="Keine Hilfe nötig: Bugfix")
    assert result.exemption is None
    assert result.violation


def test_ausnahme_ohne_begruendung_gilt_nicht():
    assert _eval(["installer/update.sh"], body="Keine Hilfe nötig:").violation


def test_ausnahme_gross_klein_egal_und_mit_einrueckung():
    assert _eval(["installer/update.sh"], body="  keine hilfe nötig: interner Umbau ohne Wirkung").ok


def test_ausnahme_muss_eigene_zeile_sein():
    # Zitat mitten im Satz ist keine Ausnahme – sonst reicht jede Erwähnung der Regel im PR-Text.
    body = "Die Zeile Keine Hilfe nötig: interner Umbau steht in der Spec."
    assert _eval(["installer/update.sh"], body=body).violation


def test_ausnahme_none_body():
    assert _eval(["installer/update.sh"], body=None).violation


# --- Nachricht (Spec §4) -------------------------------------------------------------------------------------------

def test_meldung_nennt_was_warum_beheben(tmp_path):
    root = _repo(tmp_path, {"agents": ["agents"]})
    result = _eval(["frontend/src/features/agents/areas/AreaSwitch.tsx", "installer/update.sh"], root=root)
    text = guard.message(result)
    assert text.startswith("Hilfe fehlt: 2 nutzersichtbare Datei(en) geändert (")
    assert "features/agents/areas/AreaSwitch.tsx" in text
    assert "keine Hilfe-Datei" in text
    assert "WARUM:" in text and "docs/specs/hilfe-guard.md" in text
    assert "BEHEBEN: frontend/src/i18n/help/de/agents.md ergänzen" in text
    assert "Keine Hilfe nötig: <Begründung>" in text


def test_meldung_kuerzt_dateiliste():
    files = [f"frontend/src/features/chat/F{i}.tsx" for i in range(8)]
    text = guard.message(_eval(files))
    assert "F4.tsx" in text and "F5.tsx" not in text and "…" in text


def test_meldung_ok_faelle():
    assert "Regel greift nicht" in guard.message(_eval(["core/src/a.py"]))
    assert "Hilfe geändert" in guard.message(_eval(["installer/update.sh", f"{HELP}/admin.md"]))
    assert "begründet" in guard.message(_eval(["installer/update.sh"], body="Keine Hilfe nötig: interner Umbau"))


# --- HG2: Artikel-Vorschlag ----------------------------------------------------------------------------------------

def test_vorschlag_aus_topic_stellen(tmp_path):
    root = _repo(tmp_path, {"communication": ["communication"]})
    result = _eval(["frontend/src/features/communication/X.tsx"], root=root)
    assert result.suggestions == [f"{HELP}/communication.md"]
    assert f"BEHEBEN: {HELP}/communication.md ergänzen" in guard.message(result)


def test_vorschlag_settings_nennt_beide_topics(tmp_path):
    root = _repo(tmp_path, {"settings": ["agents", "projects"]}, help_articles=("agents", "projects"))
    result = _eval(["frontend/src/features/settings/detail/AgentSettings.tsx"], root=root)
    assert result.suggestions == [f"{HELP}/agents.md", f"{HELP}/projects.md"]
    assert f"{HELP}/agents.md oder {HELP}/projects.md" in guard.message(result)


def test_vorschlag_cockpit_nennt_alle_treffer(tmp_path):
    root = _repo(tmp_path, {"cockpit": ["users", "jobs", "users"]})
    result = _eval(["frontend/src/features/cockpit/admin/X.tsx"], root=root)
    assert result.suggestions == [f"{HELP}/jobs.md", f"{HELP}/users.md"]      # sortiert, ohne Doppelte


def test_vorschlag_mehrere_ordner_vereint(tmp_path):
    root = _repo(tmp_path, {"communication": ["communication"], "jobs": ["jobs"]})
    result = _eval(["frontend/src/features/communication/A.tsx", "frontend/src/features/jobs/B.tsx"], root=root)
    assert result.suggestions == [f"{HELP}/communication.md", f"{HELP}/jobs.md"]


def test_vorschlag_ordner_ohne_topic_nimmt_gleichnamigen_artikel(tmp_path):
    # features/agents hat selbst kein HelpButton (der sitzt in settings), der Artikel agents.md existiert aber.
    root = _repo(tmp_path, {"agents": []})
    result = _eval(["frontend/src/features/agents/areas/X.tsx"], root=root)
    assert result.suggestions == [f"{HELP}/agents.md"]


def test_vorschlag_unbekannter_ordner_allgemeiner_hinweis(tmp_path):
    root = _repo(tmp_path, {"unbekannt": []})
    result = _eval(["frontend/src/features/unbekannt/X.tsx"], root=root)
    assert result.suggestions == []
    text = guard.message(result)
    assert "passenden Artikel unter frontend/src/i18n/help/de/ wählen oder neu anlegen" in text


def test_vorschlag_topic_ohne_artikel_wird_nicht_genannt(tmp_path):
    root = _repo(tmp_path, {"foo": ["gibtsnicht"]})
    assert _eval(["frontend/src/features/foo/X.tsx"], root=root).suggestions == []


def test_vorschlag_ohne_root_allgemeiner_hinweis():
    assert _eval(["frontend/src/features/communication/X.tsx"], root=None).suggestions == []


def test_vorschlag_locale_json_gleichnamiger_artikel(tmp_path):
    root = _repo(tmp_path, {})
    result = _eval(["frontend/src/i18n/locales/de/agents.json"], root=root)
    assert result.suggestions == [f"{HELP}/agents.md"]


def test_vorschlag_installer_und_shared_allgemein(tmp_path):
    root = _repo(tmp_path, {})
    assert _eval(["installer/update.sh", "frontend/src/shared/ui/B.tsx"], root=root).suggestions == []


def test_vorschlag_pfad_ausbruch_wird_ignoriert(tmp_path):
    root = _repo(tmp_path, {"communication": ["../../etc/passwd", "communication"]},
                 help_articles=("communication",))
    assert _eval(["frontend/src/features/communication/X.tsx"], root=root).suggestions == [f"{HELP}/communication.md"]


def test_vorschlag_echter_kern_agents_und_communication():
    root = _SCRIPT.parents[1]
    assert _eval(["frontend/src/features/communication/X.tsx"], root=root).suggestions == [f"{HELP}/communication.md"]
    assert _eval(["frontend/src/features/agents/areas/X.tsx"], root=root).suggestions == [f"{HELP}/agents.md"]


# --- Modus / Exit-Code ---------------------------------------------------------------------------------------------

def test_warn_ist_exit_0_und_block_exit_1():
    bad = _eval(["installer/update.sh"])
    assert guard.exit_code(bad, "warn") == 0
    assert guard.exit_code(bad, "") == 0
    assert guard.exit_code(bad, "block") == 1
    assert guard.exit_code(bad, " BLOCK ") == 1


def test_block_ohne_verstoss_exit_0():
    assert guard.exit_code(_eval(["core/src/a.py"]), "block") == 0
    assert guard.exit_code(_eval(["installer/update.sh", f"{HELP}/admin.md"]), "block") == 0
    assert guard.exit_code(_eval(["installer/update.sh"], body="Keine Hilfe nötig: interner Umbau"), "block") == 0


# --- Ende-zu-Ende gegen ein echtes Git-Repo ------------------------------------------------------------------------

def _git(cwd, *args):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd, check=True, capture_output=True)


def _run(repo, base, head, env_extra, mode="warn"):
    import os
    env = {**os.environ, "HILFE_GUARD_MODE": mode, "PR_BODY": "", **env_extra}
    env.pop("GITHUB_STEP_SUMMARY", None)
    return subprocess.run([sys.executable, str(_SCRIPT), base, head], cwd=repo, env=env, capture_output=True, text=True)


@pytest.fixture
def git_repo(tmp_path):
    repo = _repo(tmp_path, {"agents": []})
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
    area = repo / "frontend/src/features/agents/areas"
    area.mkdir(parents=True)
    (area / "X.tsx").write_text("export {}\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat: X")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
    return repo, base, head


def test_e2e_warnung_exit_0_und_block_exit_1(git_repo):
    repo, base, head = git_repo
    warn = _run(repo, base, head, {})
    assert warn.returncode == 0
    assert "::warning title=Hilfe-Guard::Hilfe fehlt: 1 nutzersichtbare Datei(en)" in warn.stdout
    assert f"BEHEBEN: {HELP}/agents.md ergänzen" in warn.stdout
    block = _run(repo, base, head, {}, mode="block")
    assert block.returncode == 1
    assert "::error title=Hilfe-Guard::" in block.stdout


def test_e2e_ausnahme_aus_env_body(git_repo):
    repo, base, head = git_repo
    result = _run(repo, base, head, {"PR_BODY": "Keine Hilfe nötig: interner Umbau ohne Wirkung"}, mode="block")
    assert result.returncode == 0
    assert "begründet" in result.stdout


def test_e2e_hilfe_datei_im_pr(git_repo):
    repo, base, head = git_repo
    (repo / HELP / "agents.md").write_text("# neu\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "docs: Hilfe")
    new_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
    result = _run(repo, base, new_head, {}, mode="block")
    assert result.returncode == 0
    assert "Hilfe geändert" in result.stdout


def test_e2e_zusammenfassung_wird_geschrieben(git_repo, tmp_path):
    repo, base, head = git_repo
    summary = tmp_path / "summary.md"
    import os
    env = {**os.environ, "HILFE_GUARD_MODE": "warn", "PR_BODY": "", "GITHUB_STEP_SUMMARY": str(summary)}
    subprocess.run([sys.executable, str(_SCRIPT), base, head], cwd=repo, env=env, check=True, capture_output=True)
    assert "### Hilfe-Guard (warn)" in summary.read_text()


def test_aufruf_ohne_argumente_exit_2():
    result = subprocess.run([sys.executable, str(_SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 2
    assert "Aufruf:" in result.stdout


def test_ausnahme_platzhalter_aus_der_meldung_gilt_nicht():
    # Wer die Zeile aus der Fehlermeldung unverändert in den PR-Text kopiert, hat nichts begründet.
    assert _eval(["installer/update.sh"], body="Keine Hilfe nötig: <Begründung>").violation
