"""Attrappen für die Update-Tests (U4): systemctl, curl, journalctl. Kein Test darf je den echten Dienst anfassen.

Zustand liegt in ``sysd`` (Ordner):  active (Datei = Dienst läuft), calls.log, nrestarts + nrestarts_step (Zähler, wächst bei
jeder Abfrage um step), nostart_commits (Commits, mit denen der Dienst nicht hochkommt), bad_health_commits (Dienst läuft, Health
antwortet nicht), health_commit_override (Health meldet diesen Commit), active_since.
Health-Antwort = HEAD des Attrappen-Repos (so verhält sich der echte Dienst: er liefert den ausgecheckten Code).
"""
from __future__ import annotations

from pathlib import Path

SYSTEMCTL = r'''#!/bin/bash
S="$HH_FAKE_SYSD"
echo "systemctl $*" >> "$S/calls.log"
head_commit() { git -C "$HH_FAKE_REPO" rev-parse HEAD 2>/dev/null; }
listed() { [ -f "$S/$1" ] && grep -qx "$(head_commit)" "$S/$1"; }
unit=""; for a in "$@"; do case "$a" in *.service|*.timer) unit="$a" ;; esac; done
case "$1" in
  is-active) [ "$unit" = "hydrahive2.service" ] && [ -f "$S/active" ] ;;
  stop) [ "$unit" = "hydrahive2.service" ] && rm -f "$S/active"; exit 0 ;;
  start|restart)
    [ "$unit" = "hydrahive2.service" ] || exit 0
    date '+%F %T' > "$S/active_since"
    if listed nostart_commits; then rm -f "$S/active"; exit 0; fi
    touch "$S/active"; exit 0 ;;
  show)
    case "$*" in
      *NRestarts*) n=$(cat "$S/nrestarts" 2>/dev/null || echo 0); echo "$n"
                   echo $((n + $(cat "$S/nrestarts_step" 2>/dev/null || echo 0))) > "$S/nrestarts" ;;
      *ActiveEnterTimestamp*) cat "$S/active_since" 2>/dev/null || echo "2020-01-01 00:00:00" ;;
    esac; exit 0 ;;
  cat) exit 1 ;;
  *) exit 0 ;;
esac
'''

CURL = r'''#!/bin/bash
S="$HH_FAKE_SYSD"
echo "curl $*" >> "$S/calls.log"
[ -f "$S/active" ] || exit 7
c=$(git -C "$HH_FAKE_REPO" rev-parse HEAD 2>/dev/null)
if [ -f "$S/bad_health_commits" ] && grep -qx "$c" "$S/bad_health_commits"; then exit 22; fi
[ -f "$S/health_commit_override" ] && c=$(cat "$S/health_commit_override")
echo "{\"status\":\"ok\",\"version\":\"2.0.0\",\"commit\":\"$c\",\"update_behind\":0}"
'''

JOURNALCTL = "#!/bin/bash\necho 'attrappe: journal'\n"


def install_fakes(bin_: Path, sysd: Path, repo: Path) -> dict[str, str]:
    sysd.mkdir(parents=True, exist_ok=True)
    (sysd / "active").write_text("")
    for name, body in (("systemctl", SYSTEMCTL), ("curl", CURL), ("journalctl", JOURNALCTL)):
        (bin_ / name).write_text(body)
        (bin_ / name).chmod(0o755)
    return {"HH_FAKE_SYSD": str(sysd), "HH_FAKE_REPO": str(repo),
            "HH_UPDATE_HEALTH_TIMEOUT": "1", "HH_UPDATE_HEALTH_INTERVAL": "0.2"}
