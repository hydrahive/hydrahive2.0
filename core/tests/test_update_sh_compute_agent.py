"""Regression guards for rolling compute-agent transport security to existing installs."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UPDATE = (ROOT / "installer" / "update.sh").read_text(encoding="utf-8")
SYSTEMD = (ROOT / "installer" / "modules" / "50-systemd.sh").read_text(encoding="utf-8")
NGINX = (ROOT / "installer" / "modules" / "60-nginx.sh").read_text(encoding="utf-8")


def test_update_rewrites_old_systemd_unit_for_compute_channel_security() -> None:
    assert "EnvironmentFile=$COMPUTE_PROXY_ENV" in SYSTEMD
    assert "--ws-max-size 65536" in SYSTEMD
    assert 'grep -Fq "EnvironmentFile=$HH_CONFIG_DIR/compute-proxy.env"' in UPDATE
    assert 'grep -q -- "--ws-max-size 65536"' in UPDATE


def test_update_rewrites_old_nginx_config_for_compute_mtls() -> None:
    assert "/api/compute/agent/connect" in NGINX
    assert "ssl_verify_client optional" in NGINX
    assert "hydrahive-compute-secret.conf" in NGINX
    assert 'grep -q "/api/compute/agent/connect"' in UPDATE
    assert 'grep -q "ssl_verify_client optional"' in UPDATE
    assert 'grep -q "hydrahive-compute-secret.conf"' in UPDATE


def test_update_passes_required_compute_paths_to_nginx_module() -> None:
    assert UPDATE.count('HH_USER="$HH_USER" HH_DATA_DIR="$HH_DATA_DIR" HH_CONFIG_DIR="$HH_CONFIG_DIR"') >= 3
