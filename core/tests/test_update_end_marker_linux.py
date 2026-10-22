"""installer/update.sh (Linux) schreibt als letzte Zeile HH-UPDATE-ENDE (Update-Fenster, Befund 22.10.2026)."""
from __future__ import annotations

import subprocess
from pathlib import Path

UPDATE = Path(__file__).resolve().parents[2] / "installer" / "update.sh"


def _run_head(tmp_path: Path, *, root: bool) -> subprocess.CompletedProcess:
    """Nur den Kopf (bis nach der Root-Prüfung) ausführen: dort bricht ein Nicht-root-Aufruf ab."""
    text = UPDATE.read_text()
    head = text[:text.index('[ -d "$HH_REPO_DIR/.git" ]')]
    bin_ = tmp_path / "bin"
    bin_.mkdir(exist_ok=True)
    (bin_ / "id").write_text(f'#!/bin/bash\n[ "$1" = "-u" ] && echo {0 if root else 1000} && exit 0\nexec /usr/bin/id "$@"\n')
    (bin_ / "id").chmod(0o755)
    # Wie systemd (StandardOutput/StandardError=append:…): beide Ströme landen in DERSELBEN Log-Datei.
    return subprocess.run(["bash", "-c", head + 'echo "KOPF-OK"\n'], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, timeout=30, env={"PATH": f"{bin_}:/usr/bin:/bin"})


def test_linux_abort_writes_error_marker(tmp_path):
    r = _run_head(tmp_path, root=False)
    assert r.returncode != 0
    out = [l for l in r.stdout.splitlines() if l.strip()]
    assert out[-1].startswith("HH-UPDATE-ENDE: fehler")
    assert "sudo" in out[-1] or "root" in out[-1]


def test_linux_root_passes_head_without_marker(tmp_path):
    r = _run_head(tmp_path, root=True)
    assert "KOPF-OK" in r.stdout
    assert r.stdout.strip().splitlines()[-1] == "HH-UPDATE-ENDE: ok"     # Kopf-Ausschnitt endet normal → ok


def test_linux_success_path_writes_ok_marker():
    text = UPDATE.read_text()
    assert text.count("HH-UPDATE-ENDE: ok") == 1
    assert "trap _hh_end EXIT" in text
    # Der Erfolgsweg endet ohne exit ≠ 0 → trap schreibt „ok“. Gegenprobe: kein weiteres trap überschreibt es.
    assert text.count("trap ") == 1, [l for l in text.splitlines() if "trap " in l]
