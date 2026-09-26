"""Service-Secrets gehören nicht in für alle lesbare systemd-Units.

Befund 26.09.2026: HH_SECRET_KEY (signiert alle Logins) stand als
Environment= in /etc/systemd/system/hydrahive2.service (0644), der
Postgres-Mirror-DSN samt Passwort in hydrahive2.service.d/pg-mirror.conf
(0644). Jeder lokale Benutzer konnte beides lesen, auch per
`systemctl show hydrahive2`. Vorbild für die Lösung: hydralink#4.
"""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
LIB = INSTALLER / "lib" / "service-secrets.sh"
SYSTEMD = INSTALLER / "modules" / "50-systemd.sh"
POSTGRES = INSTALLER / "modules" / "48-postgres.sh"
UPDATE = INSTALLER / "update.sh"


def _write(tmp: Path, *, key: str | None = "k" * 64, dsn: str | None = None) -> subprocess.CompletedProcess:
    cfg = tmp / "etc"
    cfg.mkdir(exist_ok=True)
    if key is not None:
        (cfg / "secret_key").write_text(key + "\n")
    if dsn is not None:
        (cfg / "pg_mirror.dsn").write_text(dsn + "\n")
    script = f'set -euo pipefail\nsource "{LIB}"\nwrite_service_secrets\n'
    env = {**os.environ, "HH_CONFIG_DIR": str(cfg), "HH_SERVICE_SECRETS_SKIP_CHOWN": "1"}
    return subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=30)


def _env_file(tmp: Path) -> Path:
    return tmp / "etc" / "service-secrets.env"


def _systemd_unquote(value: str) -> str:
    """Auswertung eines doppelt gequoteten Werts wie systemd EnvironmentFile=.

    In "…" gilt nur \\ als Escape, $ bleibt wörtlich. Gegen den echten Parser
    geprüft (systemd-run -p EnvironmentFile=… printenv), auch mit $, ', ",
    \\, ${HOME}, %n und Leerzeichen.
    """
    assert value.startswith('"') and value.endswith('"'), value
    out, i, inner = [], 0, value[1:-1]
    while i < len(inner):
        if inner[i] == "\\" and i + 1 < len(inner):
            out.append(inner[i + 1])
            i += 2
        else:
            out.append(inner[i])
            i += 1
    return "".join(out)


def _parsed(tmp: Path) -> dict[str, str]:
    lines = _env_file(tmp).read_text().splitlines()
    return {k: _systemd_unquote(v) for k, v in (line.split("=", 1) for line in lines)}


def test_env_file_is_private_and_contains_key(tmp_path: Path) -> None:
    r = _write(tmp_path)
    assert r.returncode == 0, r.stderr
    assert stat.S_IMODE(_env_file(tmp_path).stat().st_mode) == 0o600
    assert _parsed(tmp_path) == {"HH_SECRET_KEY": "k" * 64}


def test_dsn_is_added_when_present(tmp_path: Path) -> None:
    dsn = "postgresql://hydrahive_mirror:pw@127.0.0.1:5432/hydrahive_mirror"
    _write(tmp_path, dsn=dsn)
    assert _parsed(tmp_path) == {"HH_SECRET_KEY": "k" * 64, "HH_PG_MIRROR_DSN": dsn}


def test_special_characters_survive_unchanged(tmp_path: Path) -> None:
    dsn = "postgresql://u:p$a'ss w\"x\\y${HOME}%n@h/db"
    _write(tmp_path, dsn=dsn)
    assert _parsed(tmp_path)["HH_PG_MIRROR_DSN"] == dsn


def test_missing_key_fails_instead_of_writing_empty(tmp_path: Path) -> None:
    r = _write(tmp_path, key=None)
    assert r.returncode != 0
    assert not _env_file(tmp_path).exists()


def test_old_file_is_replaced_atomically(tmp_path: Path) -> None:
    _write(tmp_path, key="alt" * 20)
    _write(tmp_path, key="neu" * 20)
    assert _parsed(tmp_path) == {"HH_SECRET_KEY": "neu" * 20}
    assert not list((tmp_path / "etc").glob("service-secrets.env.*"))


# ------------------------------------------------------------ Installer-Vorlagen

def _unit_template() -> str:
    text = SYSTEMD.read_text()
    start = text.index('cat > "$SERVICE_FILE" <<EOF')
    return text[start:text.index("\nEOF", start)]


def test_unit_has_no_secret_but_env_file() -> None:
    unit = _unit_template()
    assert "HH_SECRET_KEY" not in unit
    assert "HH_PG_MIRROR_DSN" not in unit
    assert "EnvironmentFile=$SERVICE_SECRETS_ENV" in unit


def test_systemd_module_writes_env_file_before_unit() -> None:
    text = SYSTEMD.read_text()
    assert text.index("write_service_secrets") < text.index('cat > "$SERVICE_FILE" <<EOF')


def test_postgres_module_writes_no_dsn_dropin() -> None:
    text = POSTGRES.read_text()
    assert "Environment=HH_PG_MIRROR_DSN" not in text
    assert "write_service_secrets" in text
    assert 'rm -f "$DROPIN_FILE"' in text


def test_update_migrates_existing_units() -> None:
    text = UPDATE.read_text()
    assert 'grep -q "^Environment=HH_SECRET_KEY=" "$SERVICE_FILE" && NEEDS_REWRITE=1' in text
    assert 'grep -Fq "EnvironmentFile=$HH_CONFIG_DIR/service-secrets.env" "$SERVICE_FILE" || NEEDS_REWRITE=1' in text
    assert '[ -f /etc/systemd/system/hydrahive2.service.d/pg-mirror.conf ] && NEEDS_REWRITE=1' in text


def test_rotation_by_deleting_secret_key_triggers_rewrite() -> None:
    # Rotation wie bei AgentLink: Quelle löschen + Update. Ohne diese Bedingung
    # hätte das Update den alten Schlüssel aus service-secrets.env weiterbenutzt.
    text = UPDATE.read_text()
    assert '[ -s "$HH_CONFIG_DIR/secret_key" ] || NEEDS_REWRITE=1' in text


def test_env_file_is_rebuilt_on_every_update() -> None:
    # Auch ohne Unit-Rewrite: Änderungen an secret_key/pg_mirror.dsn kommen an.
    text = UPDATE.read_text()
    rewrite = text.index('bash "$HH_REPO_DIR/installer/modules/50-systemd.sh"')
    restart = text.index('log "Service neu starten"\nsystemctl restart hydrahive2.service')
    rebuild = text.index("write_service_secrets", rewrite)
    assert rewrite < rebuild < restart


def test_update_postgres_check_no_longer_requires_dropin() -> None:
    text = UPDATE.read_text()
    block = text[text.index('if [ "${HH_INSTALL_POSTGRES:-yes}" != "no" ]; then'):]
    block = block[:block.index("\nfi\n")]
    assert "DROPIN_FILE" not in block


@pytest.mark.parametrize("path", [SYSTEMD, POSTGRES])
def test_modules_load_the_shared_helper(path: Path) -> None:
    assert 'source "$INSTALLER_DIR/lib/service-secrets.sh"' in path.read_text()
