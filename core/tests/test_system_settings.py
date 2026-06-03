"""GUI-Settings-Route: Schema lesen, Override schreiben, Secrets maskiert, Admin-only."""
from __future__ import annotations


def test_get_settings_listet_registry_admin(client, admin_headers):
    r = client.get("/api/system/settings", headers=admin_headers)
    assert r.status_code == 200
    items = r.json()["settings"]
    keys = {s["key"] for s in items}
    assert "searxng_url" in keys
    assert {"Websuche", "Mail", "Discord", "AgentLink", "Health", "System"} <= {s["group"] for s in items}
    pw = next(s for s in items if s["key"] == "mail_smtp_password")
    assert pw["type"] == "secret" and pw["value"] == ""  # nie roh


def test_mail_defaults_effective_no_password(client, admin_headers, monkeypatch, tmp_path):
    # Platzhalter-Quelle fürs per-Buddy-Postfach: effektive globale Mail-Config,
    # IMAP-Host aus SMTP abgeleitet, niemals das Passwort. Admin-only (Infra-Config).
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("HH_MAIL_SMTP_HOST", "w0.kasserver.com")
    monkeypatch.setenv("HH_MAIL_SMTP_USER", "m07")
    monkeypatch.delenv("HH_MAIL_IMAP_HOST", raising=False)

    r = client.get("/api/system/mail-defaults", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["smtp"]["host"] == "w0.kasserver.com"
    assert body["smtp"]["user"] == "m07"
    assert body["imap"]["host"] == "w0.kasserver.com"   # aus SMTP abgeleitet
    assert "password" not in body["smtp"]
    assert "password" not in body["imap"]


def test_mail_defaults_non_admin_forbidden(client, auth_headers):
    # Nicht-Admin darf die globale Infra-Config nicht sehen (kein Privilege-Downgrade).
    r = client.get("/api/system/mail-defaults", headers=auth_headers)
    assert r.status_code == 403


def test_put_setzt_override_und_get_spiegelt(client, admin_headers, monkeypatch, tmp_path):
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    r = client.put("/api/system/settings/searxng_url", headers=admin_headers,
                   json={"value": "https://searx.test"})
    assert r.status_code == 200
    assert r.json()["value"] == "https://searx.test"
    assert r.json()["overridden"] is True

    items = client.get("/api/system/settings", headers=admin_headers).json()["settings"]
    sx = next(s for s in items if s["key"] == "searxng_url")
    assert sx["value"] == "https://searx.test"


def test_put_leer_loescht_override(client, admin_headers, monkeypatch, tmp_path):
    monkeypatch.setenv("HH_CONFIG_DIR", str(tmp_path))
    client.put("/api/system/settings/searxng_url", headers=admin_headers, json={"value": "https://x"})
    r = client.put("/api/system/settings/searxng_url", headers=admin_headers, json={"value": ""})
    assert r.status_code == 200
    assert r.json()["overridden"] is False


def test_put_unbekannter_key_404(client, admin_headers):
    r = client.put("/api/system/settings/HH_SECRET_KEY", headers=admin_headers, json={"value": "hack"})
    assert r.status_code == 404


def test_settings_admin_only(client):
    assert client.get("/api/system/settings").status_code in (401, 403)
