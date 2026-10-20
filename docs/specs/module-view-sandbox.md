# Modul-Ansichten im Chat (abgeschottet) – Spec

Status: **FREIGEGEBEN** durch Till (20.10.2026). Anlass: Modul **Diagramme** (hydrahive2-modules `diagramme/SPEC.md`)
soll interaktive Diagramme (Archify, HTML mit Inline-Skripten) **direkt im Chat bedienbar** zeigen.

## 1. Problem

- Die App-CSP (`installer/modules/60-nginx.sh`, Server-Ebene) erlaubt keine Inline-Skripte.
- Gemessen 20.10. (Chromium): App-CSP **und** eine eigene CSP auf derselben Antwort → Inline-Skript blockiert
  (beide CSPs gelten, die strengere gewinnt). Nur die eigene Sandbox-CSP → Skript läuft.
- Der Chat zeigt aus Werkzeug-Ergebnissen nur Bild, Ton, Video, PDF und EPUB (`runner/_media.py`, `MediaPreview.tsx`).

## 2. Lösung (allgemein für alle Module)

### 2.1 nginx: Sandbox-Ausnahme

- Neue Stelle `location ~ ^/api/module-device/[a-z0-9-]+/sandbox/` (Marker `hh_module_sandbox`) mit
  `add_header` auf Location-Ebene. Damit erbt sie die Server-Kopfzeilen **nicht** (nginx-Regel) und setzt **fest**:
  - `Content-Security-Policy: sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox; default-src 'none';
    script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none';
    form-action 'none'; base-uri 'none'; frame-ancestors 'self'`
  - `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: SAMEORIGIN`,
    `Strict-Transport-Security: max-age=31536000`, `Cache-Control: no-store`.
- Weiterleitung wie `/api/` (gleiche proxy-Kopfzeilen), `client_max_body_size 64k` (nur GET).
- Die Abschottung hängt damit nicht vom Modul ab: Ein Modul kann sie über eigene Kopfzeilen nur verschärfen.
- `update.sh`: `grep -q "hh_module_sandbox"` → sonst Konfig neu schreiben (wie andere Marker).
- Mac (`modules-mac/60-nginx.sh`) setzt keine App-CSP → keine Ausnahme nötig.
- Zugang: Die Route liegt unter den **Geräte-Routen** (`register_device_router`, ohne Login, Rate-Limit, Modul-`auth`
  Pflicht). Ein `<iframe>` kann keinen Anmelde-Kopf senden; das Modul prüft eine signierte Kurzzeit-Adresse
  (z. B. HMAC, 10 min). Kein Anmelde-Token in der Adresse.

### 2.2 Werkzeug-Ergebnis `module_view`

- Ein Modul-Werkzeug liefert `ToolResult.ok(text, result_type="module_view", module=<id>, view_id=<id>, title=<text>)`.
- `runner/dispatcher.to_tool_result_block` macht daraus
  `block["media"] = [{"kind": "module_view", "module": …, "view_id": …, "title": …}]` – nur wenn
  - `module` nach `^[a-z0-9][a-z0-9-]*$` und als **geladenes** Modul bekannt,
  - `view_id` nach `^[A-Za-z0-9_-]{1,64}$`,
  - `title` Text, auf 200 Zeichen gekürzt (fehlt → leer).
  Sonst kein Media-Eintrag (der Text bleibt).
- Bei Fehlschlag (`success=False`) nie.

### 2.3 Chat-Anzeige

- `ToolMedia.kind` um `"module_view"` erweitert (Felder `module`, `view_id`, `title`).
- Neue Komponente `ModuleViewFrame`:
  - holt mit Login `GET /api/modules/<module>/view-link/<view_id>` → `{url}`; nur relative Adressen, die mit
    `/api/module-device/<module>/sandbox/` beginnen, werden genutzt (sonst Hinweis).
  - lädt erst, wenn der Rahmen ins Bild scrollt (`IntersectionObserver`).
  - `<iframe sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox" referrerpolicy="no-referrer">`,
    **ohne** `allow-same-origin`, `allow-top-navigation`, `allow-forms`. Höhe 480 px.
  - Kopfzeile mit Titel und „Groß öffnen“ (eigenes Vollbild-Fenster, gleicher Rahmen, holt einen frischen Link).
  - Fehler (404, Modul fehlt, Netz): Karte mit Titel und kurzem Hinweis, Knopf „Neu laden“ (holt neuen Link).
- Texte de/en im Namespace `chat`, ohne Fachwörter.

## 3. Tests

- nginx: Ausnahme genau einmal, Muster und feste CSP exakt, setzt `sandbox`, **nicht** `'self'`-Skripte; Marker in
  `update.sh`; Ausnahme steht **vor** `location /api/` (Regex vor Präfix – nginx nimmt bei Präfix-Treffer `/api/`
  trotzdem die Regex, solange `/api/` nicht `^~` ist) → Test prüft, dass `/api/` kein `^~` hat.
- Dispatcher: gültiges `module_view` → Eintrag; unbekanntes Modul, falsche ID, Fehler-Ergebnis → kein Eintrag;
  Titel gekürzt.
- Frontend (vitest): `mediaFromBlocks` reicht `module_view` durch; `ModuleViewFrame` nutzt nur passende Adressen,
  setzt exakt die sandbox-Rechte, lädt erst bei Sichtbarkeit, zeigt Hinweis bei Fehler.
