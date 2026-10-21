"""macOS: AgentLink (HydraLink) gehört zur Mac-Installation (Plan docs/plans/mac-agentlink.md, Task f4a303a9).

Befund 21.10.2026: install-mac.sh hatte keine AgentLink-Phase → auf jedem Mac „AgentLink nicht verbunden“,
ask_agent scheitert. Außerdem fehlten im Mac-nginx /agentlink/, die Tailnet-Sperre für /api/peering/ und die
Sicherheits-Kopfzeilen des Linux-nginx.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
AGENTLINK = INSTALLER / "modules-mac" / "75-agentlink.sh"
INSTALL = INSTALLER / "install-mac.sh"
UPDATE = INSTALLER / "update-mac.sh"
NGINX_MAC = INSTALLER / "modules-mac" / "60-nginx.sh"
NGINX_LINUX = INSTALLER / "modules" / "60-nginx.sh"


@pytest.fixture
def mac(tmp_path: Path) -> dict:
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    calls = tmp_path / "calls.log"
    calls.write_text("")
    hl = tmp_path / "hydralink"
    # git: clone legt einen Schein-Klon mit install-mac.sh an, das seine Umgebung protokolliert.
    (bin_ / "git").write_text(f'''#!/bin/bash
echo "git $*" >> "{calls}"
case "$*" in
  *clone*)
    for d in "$@"; do :; done
    mkdir -p "$d/.git" "$d/installer"
    printf '#!/bin/bash\\necho "hl-install user=$HL_USER be=$HL_BACKEND_PORT fe=$HL_FRONTEND_PORT uid=$(id -u)" >> "{calls}"\\n[ -f "{tmp_path}/hl_fail" ] && exit 1\\nexit 0\\n' > "$d/installer/install-mac.sh" ;;
esac
exit 0
''')
    (bin_ / "sudo").write_text(f'#!/bin/bash\necho "sudo $*" >> "{calls}"\nwhile [ $# -gt 0 ]; do case "$1" in -u) shift 2;; -H|-n) shift;; *) break;; esac; done\nexec "$@"\n')
    (bin_ / "id").write_text('#!/bin/bash\nif [ "$#" -eq 1 ] && [ "$1" = "-u" ]; then echo "${FAKE_UID:-501}"; else exec /usr/bin/id "$@"; fi\n')
    (bin_ / "chown").write_text(f'#!/bin/bash\necho "chown $*" >> "{calls}"\n')
    for f in bin_.iterdir():
        f.chmod(0o755)
    return {"tmp": tmp_path, "bin": bin_, "calls": calls, "hl": hl}


def _env(m: dict, **extra) -> dict:
    return {**os.environ, "PATH": f"{m['bin']}:{os.environ['PATH']}", "HH_USER": "tester",
            "HL_DIR": str(m["hl"]), **extra}


def _run(m: dict, **extra) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(AGENTLINK)], env=_env(m, **extra), capture_output=True, text=True,
                          timeout=60, stdin=subprocess.DEVNULL)


def _calls(m: dict) -> list[str]:
    return m["calls"].read_text().splitlines()


# --- 75-agentlink.sh ---------------------------------------------------------------------------------

def test_clones_hydralink_when_missing(mac):
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    clone = [c for c in _calls(mac) if c.startswith("git clone")]
    assert clone and clone[0].endswith(f"https://github.com/hydrahive/hydralink.git {mac['hl']}")


def test_pulls_when_present(mac):
    (mac["hl"] / ".git").mkdir(parents=True)
    (mac["hl"] / "installer").mkdir()
    (mac["hl"] / "installer" / "install-mac.sh").write_text("#!/bin/bash\nexit 0\n")
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert any(c.startswith("git -C") and "pull --ff-only" in c for c in _calls(mac))
    assert not any(c.startswith("git clone") for c in _calls(mac))


def test_runs_mac_installer_with_core_ports(mac):
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "hl-install user=tester be=9000 fe=9001 uid=501" in _calls(mac)


def test_as_root_git_runs_as_service_user(mac):
    """Kern-Update läuft als root – git als root lehnt das fremde Repo ab („dubious ownership“)."""
    r = _run(mac, FAKE_UID="0")
    assert r.returncode == 0, r.stdout + r.stderr
    gits = [c for c in _calls(mac) if c.startswith("sudo") and " git " in f" {c} "]
    assert gits and all("-u tester" in c for c in gits)
    assert any(c.startswith("chown") and "tester" in c for c in _calls(mac))   # /opt/hydralink gehört dem Nutzer


def test_failure_is_reported(mac):
    (mac["tmp"] / "hl_fail").write_text("")
    r = _run(mac)
    assert r.returncode != 0


def test_can_be_skipped(mac):
    r = _run(mac, HH_INSTALL_AGENTLINK="no")
    assert r.returncode == 0
    assert _calls(mac) == []


# --- install-mac.sh / update-mac.sh ------------------------------------------------------------------

def _run_install(tmp_path: Path, **extra) -> list[str]:
    """install-mac.sh mit Schein-Modulen: protokolliert, welche Phasen in welcher Reihenfolge laufen."""
    inst = tmp_path / "installer"
    (inst / "modules-mac").mkdir(parents=True)
    (inst / "lib").mkdir()
    log = tmp_path / "phases.log"
    for name in [p.name for p in (INSTALLER / "modules-mac").glob("*.sh")]:
        (inst / "modules-mac" / name).write_text(f'#!/bin/bash\necho "{name}" >> "{log}"\n')
    (inst / "lib" / "mac-admin-password.sh").write_text("#!/bin/bash\necho pw\n")
    (inst / "install-mac.sh").write_text(INSTALL.read_text())
    bin_ = tmp_path / "ibin"
    bin_.mkdir()
    for name, body in (("uname", "echo Darwin"), ("brew", "exit 0"), ("ipconfig", "echo 10.0.0.2")):
        (bin_ / name).write_text(f"#!/bin/bash\n{body}\n")
        (bin_ / name).chmod(0o755)
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "HH_REPO_DIR": str(repo), **extra}
    r = subprocess.run(["bash", str(inst / "install-mac.sh")], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    return log.read_text().splitlines()


def test_install_has_agentlink_phase_before_nginx(tmp_path):
    phases = _run_install(tmp_path)
    assert "75-agentlink.sh" in phases
    assert phases.index("48-postgres.sh") < phases.index("75-agentlink.sh") < phases.index("60-nginx.sh")


def test_install_agentlink_can_be_skipped(tmp_path):
    assert "75-agentlink.sh" not in _run_install(tmp_path, HH_INSTALL_AGENTLINK="no")
    # ohne PostgreSQL keine AgentLink-Datenbank
    assert "75-agentlink.sh" not in _run_install(tmp_path / "b", HH_INSTALL_POSTGRES="no")


def test_update_runs_agentlink_and_reports_failure():
    text = UPDATE.read_text()
    assert "modules-mac/75-agentlink.sh" in text
    i = text.index("modules-mac/75-agentlink.sh")
    block = text[i - 400:i + 600]
    assert "FEHLGESCHLAGEN" in block          # deutlich melden …
    assert "exit 1" not in block              # … aber das Kern-Update nicht abbrechen


# --- Mac-nginx -----------------------------------------------------------------------------------------

def _nginx_conf(tmp_path: Path) -> str:
    bin_ = tmp_path / "nbin"
    bin_.mkdir()
    prefix = tmp_path / "brew"
    (bin_ / "brew").write_text(f'#!/bin/bash\ncase "$1" in --prefix) echo "{prefix}";; list) exit 0;; esac\n')
    for name in ("sudo",):
        (bin_ / name).write_text('#!/bin/bash\n"$@"\n')
    (bin_ / "launchctl").write_text("#!/bin/bash\nexit 0\n")
    (bin_ / "ipconfig").write_text("#!/bin/bash\necho 192.168.1.5\n")
    for f in bin_.iterdir():
        f.chmod(0o755)
    cfg = tmp_path / "cfg"
    (cfg / "tls").mkdir(parents=True)
    (cfg / "tls" / "server.crt").write_text("x")
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "HH_CONFIG_DIR": str(cfg),
           "HH_REPO_DIR": "/opt/hydrahive2", "HH_PORT": "8001", "HH_HOST": "127.0.0.1",
           "HH_NGINX_PLIST": str(tmp_path / "io.hydrahive.nginx.plist")}
    r = subprocess.run(["bash", str(NGINX_MAC)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    return (prefix / "etc" / "nginx" / "servers" / "hydrahive2.conf").read_text()


def _location(conf: str, head: str) -> str:
    start = conf.index(head)
    return conf[start:conf.index("\n    }", start)]


def test_nginx_proxies_agentlink_with_admin_check(tmp_path):
    conf = _nginx_conf(tmp_path)
    assert "proxy_pass http://127.0.0.1:8001/api/agentlink/dashboard-auth;" in _location(conf, "location = /_hh_agentlink_auth")
    for head, target in (("location /agentlink/ {", "127.0.0.1:9001/"),
                         ("location /agentlink/api/ {", "127.0.0.1:9000/"),
                         ("location /agentlink/ws {", "127.0.0.1:9000/ws")):
        block = _location(conf, head)
        assert "auth_request /_hh_agentlink_auth;" in block, head
        assert target in block, head


def test_nginx_peering_only_from_tailnet(tmp_path):
    block = _location(_nginx_conf(tmp_path), "location /api/peering/ {")
    assert "allow 100.64.0.0/10;" in block
    assert "allow fd7a:115c:a1e0::/48;" in block
    assert "deny all;" in block
    assert block.index("allow 100.64.0.0/10;") < block.index("deny all;")


def test_nginx_security_headers_like_linux(tmp_path):
    conf = _nginx_conf(tmp_path)
    active = [ln.strip() for ln in conf.splitlines() if not ln.strip().startswith("#")]
    for header in ("X-Frame-Options", "X-Content-Type-Options", "Referrer-Policy", "Strict-Transport-Security",
                   "Permissions-Policy", "Content-Security-Policy"):
        assert any(ln.startswith(f"add_header {header} ") for ln in active), header
    # Gleiche CSP wie Linux – sonst verhalten sich Chat, Diagramme usw. auf dem Mac anders.
    csp = [ln.strip() for ln in NGINX_LINUX.read_text().splitlines()
           if ln.strip().startswith('add_header Content-Security-Policy "default-src')][0]
    assert csp in conf


def test_nginx_module_sandbox_csp(tmp_path):
    block = _location(_nginx_conf(tmp_path), "location ~ ^/api/module-device/[a-z0-9-]+/sandbox/ {")
    assert "sandbox allow-scripts" in block
    assert "connect-src 'none'" in block


def test_nginx_markers_present(tmp_path):
    conf = _nginx_conf(tmp_path)
    for marker in ("hh_agentlink_auth", "hh_peering_tailnet", "hh_module_sandbox", "hh_security_headers"):
        assert marker in conf, marker


def test_update_rewrites_nginx_when_marker_missing():
    text = UPDATE.read_text()
    assert "modules-mac/60-nginx.sh" in text
    for marker in ("hh_agentlink_auth", "hh_peering_tailnet", "hh_module_sandbox", "hh_security_headers"):
        assert marker in text, marker


# --- Tailscale-CLI der macOS-App --------------------------------------------------------------------

def test_tailscale_bin_finds_macos_app(tmp_path, monkeypatch):
    from hydrahive.tailscale import _bin

    app = tmp_path / "Tailscale.app" / "Contents" / "MacOS" / "Tailscale"
    app.parent.mkdir(parents=True)
    app.write_text("#!/bin/sh\n")
    app.chmod(0o755)
    monkeypatch.setattr(_bin.shutil, "which", lambda name: None)
    monkeypatch.setattr(_bin, "MACOS_APP_CLI", str(app))
    assert _bin.tailscale_bin() == str(app)


def test_tailscale_bin_prefers_path(monkeypatch):
    from hydrahive.tailscale import _bin

    monkeypatch.setattr(_bin.shutil, "which", lambda name: "/opt/homebrew/bin/tailscale")
    assert _bin.tailscale_bin() == "/opt/homebrew/bin/tailscale"


def test_tailscale_bin_linux_fallback(tmp_path, monkeypatch):
    from hydrahive.tailscale import _bin

    monkeypatch.setattr(_bin.shutil, "which", lambda name: None)
    monkeypatch.setattr(_bin, "MACOS_APP_CLI", str(tmp_path / "fehlt"))
    assert _bin.tailscale_bin() == "/usr/bin/tailscale"


def test_tailscale_callers_use_shared_lookup():
    src = INSTALLER.parent / "core" / "src" / "hydrahive"
    for rel in ("tailscale/status.py", "tailscale/control.py", "api/routes/_dashboard_helpers.py",
                "system/addons_status.py"):
        text = (src / rel).read_text()
        assert 'shutil.which("tailscale")' not in text, rel


def test_nginx_as_root_finds_brew_by_full_path(tmp_path):
    """Befund 21.10. (Test-Mac): update-mac.sh läuft als root; `brew` liegt nicht im PATH → „brew: command not
    found“, nginx-Umbau scheiterte. 60-nginx.sh muss brew über den vollen Pfad finden (HH_BREW in Tests)."""
    bin_ = tmp_path / "nbin"
    bin_.mkdir()
    prefix = tmp_path / "brew"
    real = prefix / "bin" / "brew"
    real.parent.mkdir(parents=True)
    calls = tmp_path / "calls.log"
    real.write_text(f'#!/bin/bash\necho "brew $*" >> "{calls}"\ncase "$1" in --prefix) echo "{prefix}";; list) exit 0;; esac\n')
    real.chmod(0o755)
    (bin_ / "sudo").write_text(f'#!/bin/bash\necho "sudo $*" >> "{calls}"\n[ "$1" = "-u" ] && shift 2\n"$@"\n')
    (bin_ / "launchctl").write_text("#!/bin/bash\nexit 0\n")
    (bin_ / "ipconfig").write_text("#!/bin/bash\necho 192.168.1.5\n")
    (bin_ / "id").write_text('#!/bin/bash\nif [ "$#" -eq 1 ] && [ "$1" = "-u" ]; then echo 0; else exec /usr/bin/id "$@"; fi\n')
    for f in bin_.iterdir():
        f.chmod(0o755)
    cfg = tmp_path / "cfg"
    (cfg / "tls").mkdir(parents=True)
    (cfg / "tls" / "server.crt").write_text("x")
    env = {"PATH": f"{bin_}:/usr/bin:/bin", "HH_CONFIG_DIR": str(cfg), "HH_USER": "tester",
           "HH_REPO_DIR": "/opt/hydrahive2", "HH_PORT": "8001", "HH_BREW": str(real),
           "HH_NGINX_PLIST": str(tmp_path / "nginx.plist")}
    r = subprocess.run(["bash", str(NGINX_MAC)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (prefix / "etc" / "nginx" / "servers" / "hydrahive2.conf").exists()
    # als root: brew nur über den Dienstnutzer (Homebrew verweigert root)
    assert f"sudo -u tester {real} --prefix" in calls.read_text()
