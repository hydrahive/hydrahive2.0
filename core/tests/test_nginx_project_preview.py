"""nginx-Block der Testseite (ziele/projekt-testumgebung.md §4, Etappe E1b): installer/lib/nginx-project-preview.sh.

Die Testpfade für Zertifikat und Schlüssel tragen bewusst keine üblichen Endungen (Schutz vor Geheimnis-Zugriffen).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "installer/lib/nginx-project-preview.sh"


def _block(tmp: Path) -> str:
    script = f'source "{LIB}"; hh_project_preview_block "$1" "$2" "$3" "$4"'
    args = ["bash", "-c", script, "_", str(tmp / "zert"), str(tmp / "schluessel"), "127.0.0.1:8001", str(tmp / "cache")]
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def _location(conf: str, head: str) -> str:
    start = conf.index(head)
    return conf[start:conf.index("\n    }\n", start)]


def test_eigener_port_8445_mit_tls(tmp_path):
    conf = _block(tmp_path)
    assert "listen 8445 ssl;" in conf and "listen [::]:8445 ssl;" in conf
    assert f"ssl_certificate     {tmp_path / 'zert'};" in conf
    assert f"ssl_certificate_key {tmp_path / 'schluessel'};" in conf
    assert "hh_project_preview_auth" in conf                       # Merkmal für update.sh / update-mac.sh


def test_nur_heimnetz_tailscale_und_lokal(tmp_path):
    conf = _block(tmp_path)
    for net in ("127.0.0.1", "::1", "192.168.0.0/16", "10.0.0.0/8", "100.64.0.0/10", "fd7a:115c:a1e0::/48"):
        assert f"    allow {net};\n" in conf
    assert "    deny all;\n" in conf
    assert conf.index("deny all;") > conf.rindex("allow ")
    assert "access_log off;" in conf


def test_jede_anfrage_per_auth_request_und_port_aus_der_antwort(tmp_path):
    root = _location(_block(tmp_path), "location / {")
    assert "auth_request /__hh_preview_auth;" in root
    assert "auth_request_set $hh_preview_port $upstream_http_x_preview_port;" in root
    assert "proxy_pass http://127.0.0.1:$hh_preview_port;" in root
    assert "error_page 401 = @hh_preview_login;" in root


def test_keine_cookies_zur_testseite_kein_set_cookie_zurueck(tmp_path):
    root = _location(_block(tmp_path), "location / {")
    assert 'proxy_set_header Cookie "";' in root
    assert "proxy_hide_header Set-Cookie;" in root


def test_websocket_wird_durchgereicht(tmp_path):
    conf = _block(tmp_path)
    root = _location(conf, "location / {")
    assert "proxy_set_header Upgrade $http_upgrade;" in root and "proxy_set_header Connection $hh_preview_conn;" in root
    assert "map $http_upgrade $hh_preview_conn {" in conf


def test_pruefstelle_intern_mit_cookie_und_20s_cache(tmp_path):
    auth = _location(_block(tmp_path), "location = /__hh_preview_auth {")
    assert "internal;" in auth
    assert "proxy_pass http://127.0.0.1:8001/api/project-preview/auth;" in auth
    assert "proxy_set_header Cookie $http_cookie;" in auth
    assert "proxy_cache_key $cookie_hh_project_preview;" in auth and "proxy_cache_valid 200 20s;" in auth


def test_login_geht_an_das_backend_und_hinweis_bei_401(tmp_path):
    conf = _block(tmp_path)
    assert "proxy_pass http://127.0.0.1:8001/api/project-preview/login;" in _location(conf, "location = /__hh_preview_login {")
    hint = _location(conf, "location @hh_preview_login {")
    assert "return 401" in hint and "Testseite öffnen" in hint and "Open test page" in hint


def test_hauptblock_csp_unveraendert():
    for rel in ("installer/modules/60-nginx.sh", "installer/modules-mac/60-nginx.sh"):
        assert "frame-src 'self' https://*:8444;" in (ROOT / rel).read_text()


NGINX = shutil.which("nginx") or ("/usr/sbin/nginx" if Path("/usr/sbin/nginx").exists() else None)


@pytest.mark.skipif(NGINX is None, reason="nginx nicht vorhanden (wird nicht installiert)")
def test_nginx_t_akzeptiert_den_block(tmp_path):
    crypto = pytest.importorskip("cryptography")
    del crypto
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    priv = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
    now = datetime.datetime.now(datetime.UTC)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(priv.public_key())
            .serial_number(1).not_valid_before(now).not_valid_after(now + datetime.timedelta(days=1))
            .sign(priv, hashes.SHA256()))
    (tmp_path / "zert").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (tmp_path / "schluessel").write_bytes(priv.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    (tmp_path / "cache").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "site.conf").write_text(_block(tmp_path))
    (tmp_path / "nginx.conf").write_text(
        f"pid {tmp_path}/nginx.pid;\nerror_log {tmp_path}/logs/error.log;\nevents {{}}\n"
        f"http {{\n  client_body_temp_path {tmp_path}/b; proxy_temp_path {tmp_path}/p;\n"
        f"  fastcgi_temp_path {tmp_path}/f; uwsgi_temp_path {tmp_path}/u; scgi_temp_path {tmp_path}/s;\n"
        f"  access_log off;\n  include {tmp_path}/site.conf;\n}}\n")
    r = subprocess.run([NGINX, "-t", "-p", str(tmp_path), "-e", str(tmp_path / "logs/error.log"),
                        "-c", str(tmp_path / "nginx.conf")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "syntax is ok" in r.stderr and "test is successful" in r.stderr
