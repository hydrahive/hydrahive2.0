"""Ausnahmeliste des Auth-Wächters (``api/auth_guard.py``, Task 589ff768).

Hier steht nur, was wirklich ohne Anmelde-Abhängigkeit erreichbar sein muss.
Jede Route prüft dann selbst (Secret, Signatur, Cookie, Token im Link) und gibt
ohne gültigen Nachweis nichts preis. Das belegt je Eintrag ein Test in
``tests/test_auth_guard_exceptions.py`` (außer Login und Health).

Neue Einträge nur mit Begründung und Test. Fällt eine Route weg oder bekommt sie
eine Auth-Abhängigkeit, muss der Eintrag raus (der Wächter meldet sonst
„veraltet“ bzw. „unnötig“).
"""
from __future__ import annotations

from hydrahive.api.auth_guard import WS, OpenRoute

_PEERING = ("Server-zu-Server (server-peering.md): kein Login, jede Anfrage muss mit dem "
            "Ed25519-Schlüssel eines aktiven Partners signiert sein (peer_protocol.verify_incoming); "
            "nginx lässt /api/peering/ nur aus dem Tailnet durch.")
_PEERING_404 = (_PEERING + " Nach außen antwortet die Route bei jedem Fehler mit demselben 404 "
                "(kein Hinweis, ob es den Eintrag oder den Partner gibt).")

OPEN_ROUTES: tuple[OpenRoute, ...] = (
    OpenRoute("POST", "/api/auth/login",
              "Anmeldung selbst: erzeugt erst das Token. Schutz durch Lockout und Rate-Limit."),
    OpenRoute("GET", "/api/health",
              "Lebenszeichen für Installer, Update und nginx: nur Status, Version, Commit, "
              "Update-Rückstand; keine Nutzerdaten."),
    OpenRoute("GET", "/api/files",
              "Dateien für <img>/<a>-Links: Browser senden dort keinen Authorization-Header. "
              "Prüft selbst Bearer-Header (get_current_user_optional) oder ?token= "
              "(resolve_credential), sonst 401; danach Leserechte (_files_access). "
              "?token= soll später ersetzt werden (Task 342bb5dd)."),
    OpenRoute("GET", "/api/agentlink/dashboard-auth",
              "Prüfstelle für nginx auth_request vor dem AgentLink-Dashboard: liest nur das "
              "signierte Admin-Cookie hh_agentlink, sonst 401; liefert keinen Inhalt (204)."),
    OpenRoute("POST", "/api/butler/webhooks/project/{project_id}",
              "Eingehender Projekt-Webhook von außen: prüft X-Webhook-Secret gegen das "
              "Projekt-Secret (compare_digest); unbekanntes Projekt 404, Antwort enthält "
              "nur die Anzahl ausgelöster Flows."),
    OpenRoute("POST", "/api/communication/whatsapp/incoming",
              "Eingang von der lokalen WhatsApp-Bridge: prüft X-HH-Bridge-Secret "
              "(verify_secret), sonst 401; Rate-Limit je IP."),
    OpenRoute("POST", "/api/compute/agent/enroll",
              "Erstanmeldung eines Compute-Agenten: hat noch kein Zertifikat, prüft ein "
              "einmaliges Enrollment-Token aus dem Body; Rate-Limit je IP und je Token, "
              "Größengrenze."),
    OpenRoute(WS, "/api/compute/agent/connect",
              "WebSocket des Compute-Agenten: prüft Node-ID, Client-Zertifikat und "
              "Proxy-Secret (channel.authenticate_node), sonst Abbruch 4403."),
    OpenRoute(WS, "/api/containers/{container_id}/console",
              "WebSocket-Konsole: Browser können am WebSocket keinen Header setzen; prüft "
              "?token= selbst (_authenticate), dann Capability und Besitz, sonst Abbruch "
              "4401/4403/4404."),
    OpenRoute("POST", "/api/peering/tasks", _PEERING),
    OpenRoute("POST", "/api/peering/replies", _PEERING),
    OpenRoute("POST", "/api/peering/catalog/push", _PEERING),
    OpenRoute("POST", "/api/peering/catalog/pull", _PEERING),
    OpenRoute("POST", "/api/peering/catalog/notify", _PEERING_404),
    OpenRoute("POST", "/api/peering/catalog/read", _PEERING_404),
    OpenRoute("POST", "/api/peering/catalog/fetch", _PEERING_404),
)
