# System-Skills aktualisieren, Admin-Änderungen schützen

Task 9cc6be08 (Skill medical-akte) und der Befund dahinter. Ablauf mit Till abgestimmt am 30.09.2026.

## Befund (30.09.2026)

- `install_system_defaults()` kopiert die mitgelieferten Skills nach `$HH_DATA_DIR/skills/system/`,
  aber **nur wenn die Datei fehlt**. Einmal installiert, wird ein System-Skill nie aktualisiert.
- Live veraltet: 7 von 22 (code-graph, code-review, debugging, generate-music, generate-speech,
  hh-review, medical-akte). Alle 7 sind byte-gleich mit einer älteren Repo-Fassung, also nicht vom
  Admin geändert.
- medical-akte ist live vom 30.05. (Pfade `/api/health/patientenakte/patients`, seit dem Umbau 404).
  Die korrigierte Fassung vom 04.06. kam nie an. Auch sie nennt Port 8000 (Server läuft auf 8001)
  und verlangt den API-Key des Nutzers im Klartext.

## Regel

Beim Start je mitgeliefertem Skill:
1. Live-Datei fehlt → kopieren (wie bisher).
2. Live-Datei = aktuelle Fassung → nichts tun.
3. Live-Datei = eine **frühere mitgelieferte** Fassung (SHA-256 steht in `system_defaults/_history.json`)
   → durch die aktuelle ersetzen, Log-Eintrag „System-Skill aktualisiert“.
4. Sonst (Admin hat geändert) → nicht anfassen, Log-Warnung „weicht ab, nicht aktualisiert“.

Das Schreiben passiert atomar (temporäre Datei + `os.replace`).

`_history.json`: `{ "<name>.md": ["<sha256>", …] }`, alle früheren Fassungen aus der Git-Geschichte.
Ein Test prüft, dass die **aktuelle** Fassung jeder Datei ebenfalls in der Liste steht. Wer einen
Skill ändert, muss also `scripts/update_skill_history.py` laufen lassen, sonst wird der Test rot.
So wird die nächste Änderung wieder automatisch ausgerollt.

## medical-akte

- Port nicht mehr hart: Der Skill nennt `http://127.0.0.1:<HH_PORT>` (Standard 8001) und sagt,
  wie der Agent den Port ermittelt (Umgebung/Einstellungen), statt 8000.
- Zugriff über ein **Credential-Profil** (fetch_url setzt den Key ein, Agent sieht ihn nie),
  nicht mehr Key im Klartext im Tool-Aufruf.
- Test: Jeder im Skill genannte Pfad unter `/api/modules/patientenakte/` existiert als Route im
  Modul (aus `hydrahive2-modules/patientenakte` gelesen, wenn vorhanden, sonst übersprungen).

## Nicht Teil davon

- Modul-Skills (liegen in den Modulen, eigener Mechanismus).
- Ein UI-Knopf „auf Auslieferung zurücksetzen“.
