"""Fix-Test-Guard (docs/specs/fix-test-guard.md, Task 3d40fce8, Kurs L10)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_fix_has_test.py"
_spec = importlib.util.spec_from_file_location("check_fix_has_test", _SCRIPT)
guard = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = guard          # @dataclass braucht das Modul in sys.modules
_spec.loader.exec_module(guard)


def _eval(files, *, title="", subjects=(), body="", branch="feat/x"):
    return guard.evaluate(list(files), title=title, subjects=list(subjects), body=body, branch=branch)


# --- Fix-Erkennung ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize(("title", "subjects", "branch"), [
    ("fix(shell): Timeout-Grenze", [], "feat/x"),
    ("fix: kaputt", [], "feat/x"),
    ("Hotfix für Login", [], "feat/x"),
    ("bugfix(db): uuid", [], "feat/x"),
    ("Neues Feature", ["feat: a", "fix(api): b"], "feat/x"),
    ("Neues Feature", [], "fix/compaction-measured-usage"),
])
def test_fix_wird_erkannt(title, subjects, branch):
    result = _eval(["core/src/a.py"], title=title, subjects=subjects, branch=branch)
    assert result.is_fix


@pytest.mark.parametrize("title", [
    "feat(system): Doctor", "Harness-Benchmark", "Prefix fixen später", "docs: fix typo",
    "Fixtures für Tests aufräumen", "fixed-width Layout",   # „fix“ nur als Wortanfang zählt
])
def test_kein_fix(title):
    assert not _eval(["core/src/a.py"], title=title).is_fix


# --- Test- und Produktivdateien ----------------------------------------------------------------------------------

@pytest.mark.parametrize("test_file", [
    "core/tests/test_shell.py",
    "modules/x/foo_test.py",
    "frontend/src/features/chat/Chat.test.tsx",
    "frontend/src/shared/api.test.ts",
    "frontend/src/x/thing.spec.ts",
    "node-agent/tests/helpers.py",
])
def test_testdatei_erfuellt_regel(test_file):
    result = _eval(["core/src/a.py", test_file], title="fix: a")
    assert result.ok and not result.violation
    assert result.test_files == [test_file]
    assert result.prod_files == ["core/src/a.py"]      # Testdatei zählt nicht als Produktivcode


@pytest.mark.parametrize("not_a_test", ["core/src/latest/x.py", "frontend/src/contest/a.ts", "core/src/attest.py"])
def test_aehnliche_namen_sind_keine_tests(not_a_test):
    assert _eval([not_a_test], title="fix: a").violation


def test_fix_ohne_test_ist_verstoss():
    result = _eval(["core/src/a.py", "installer/update.sh", "frontend/src/X.tsx"], title="fix: a")
    assert result.violation
    assert result.prod_files == ["core/src/a.py", "frontend/src/X.tsx", "installer/update.sh"]


@pytest.mark.parametrize("files", [
    ["docs/specs/a.md"],
    ["frontend/src/i18n/locales/de/system.json", "README.md"],
    ["modules/x/manifest.json", ".github/workflows/a.yml"],
])
def test_ohne_produktivcode_kein_verstoss(files):
    assert not _eval(files, title="fix: Doku").violation


def test_feature_ohne_test_ist_kein_verstoss():
    assert not _eval(["core/src/a.py"], title="feat: neu").violation


# --- Ausnahme ----------------------------------------------------------------------------------------------------

def test_begruendete_ausnahme():
    body = "Beschreibung\n\nKein Test: reine Bash-3.2-Syntax, nur auf echtem Mac prüfbar\n"
    result = _eval(["installer/update-mac.sh"], title="fix: mac", body=body)
    assert not result.violation
    assert result.exemption == "reine Bash-3.2-Syntax, nur auf echtem Mac prüfbar"


@pytest.mark.parametrize("body", ["Kein Test: egal", "Kein Test:", "kein test ist nötig", ""])
def test_ausnahme_ohne_ausreichende_begruendung(body):
    assert _eval(["core/src/a.py"], title="fix: a", body=body).violation


# --- Ausgabe und Modus -------------------------------------------------------------------------------------------

def test_meldung_nennt_was_warum_wie():
    text = guard.message(_eval(["core/src/a.py"], title="fix: a"))
    assert "Fix ohne Test" in text and "WARUM" in text and "BEHEBEN" in text and "Kein Test:" in text


def test_workflow_setzt_pr_texte_nur_ueber_env():
    """Script-Injection-Schutz: PR-Titel/-Text/Branch dürfen nie direkt in einer run:-Zeile stehen."""
    workflow = (_SCRIPT.parents[1] / ".github" / "workflows" / "fix-test-guard.yml").read_text(encoding="utf-8")
    run_lines = [line for line in workflow.splitlines() if line.strip().startswith("run:")]
    assert run_lines
    for line in run_lines:
        assert "${{" not in line
    assert "pull_request_target" not in workflow
    assert "contents: read" in workflow
    assert "FIX_TEST_GUARD_MODE: warn" in workflow


def test_main_mit_echtem_git(tmp_path, monkeypatch, capsys):
    """Ende-zu-Ende: echtes Git-Repo, Fix-Commit ohne Test → Warnung, Exit 0 (warn) bzw. 1 (block)."""
    import subprocess

    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    git("init", "-q"); git("config", "user.email", "t@t"); git("config", "user.name", "t")
    (tmp_path / "a.py").write_text("x = 1\n"); git("add", "."); git("commit", "-qm", "init")
    base = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    (tmp_path / "a.py").write_text("x = 2\n"); git("commit", "-qam", "fix: x korrigiert")
    head = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PR_TITLE", "Korrektur")
    monkeypatch.setenv("PR_BODY", "")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setenv("FIX_TEST_GUARD_MODE", "warn")
    assert guard.main(["x", base, head]) == 0
    assert "::warning title=Fix-Test-Guard::Fix ohne Test" in capsys.readouterr().out
    monkeypatch.setenv("FIX_TEST_GUARD_MODE", "block")
    assert guard.main(["x", base, head]) == 1
    assert "::error" in capsys.readouterr().out


@pytest.mark.parametrize(("mode", "violation", "code"), [
    ("warn", True, 0), ("block", True, 1), ("block", False, 0), ("", True, 0), ("quatsch", True, 0),
])
def test_exit_code_je_modus(mode, violation, code):
    files = ["core/src/a.py"] if violation else ["core/src/a.py", "core/tests/test_a.py"]
    assert guard.exit_code(_eval(files, title="fix: a"), mode) == code
