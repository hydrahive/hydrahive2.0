# Plan: Service-Secrets aus den für alle lesbaren systemd-Units holen

Stand: 2026-09-27 · Task 20a30bba · Vorbild: hydralink#4 (AgentLink-DB-Passwort)

## Befund

| Wert | Wo heute | Rechte | Wer liest mit |
|---|---|---|---|
| `HH_SECRET_KEY` | `/etc/systemd/system/hydrahive2.service` (`Environment=`) | 0644 | jeder lokale Benutzer, `systemctl show hydrahive2` |
| `HH_PG_MIRROR_DSN` (mit DB-Passwort) | `/etc/systemd/system/hydrahive2.service.d/pg-mirror.conf` | 0644 | ebenso |

Geschrieben werden beide vom Installer: `50-systemd.sh` (Unit-Vorlage) und
`48-postgres.sh` (Drop-in). `update.sh` schreibt die Unit über 50-systemd.sh
neu, wenn eine Prüfbedingung fehlt.

## Wofür `HH_SECRET_KEY` benutzt wird (Folgen einer Rotation)

| Verwender | Folge beim Tausch |
|---|---|
| JWT (Login-Tokens, 24 h) | alle Browser-Sitzungen ungültig → neu anmelden |
| Teamchat: Matrix-Passwort = HMAC(Schlüssel, localpart) | bestehende Matrix-Konten könnten sich nicht mehr anmelden. **Live: 0 Identitäten**, also keine Folge |
| Compute-Enrollment-Token (HMAC, max. 1 h) | offene Einladungen ungültig. Live: keine offene |
| Compute-Console-Tickets (HMAC, max. 2 min) | laufende Tickets ungültig. Live: keines offen |
| API-Keys | **nicht betroffen** (bcrypt, unabhängig vom Schlüssel) |

## Lösung

Neue Datei `$HH_CONFIG_DIR/service-secrets.env` (root:root, 0600, atomar
geschrieben) mit `HH_SECRET_KEY=…` und, falls vorhanden, `HH_PG_MIRROR_DSN=…`.
systemd liest `EnvironmentFile=` als root, bevor es zum Dienstbenutzer wechselt.

- `50-systemd.sh`: Unit bekommt `EnvironmentFile=$HH_CONFIG_DIR/service-secrets.env`
  statt `Environment=HH_SECRET_KEY=…`. Die Datei baut die Funktion
  `write_service_secrets` (neu, `installer/lib/service-secrets.sh`) aus
  `secret_key` und `pg_mirror.dsn`.
- `48-postgres.sh`: schreibt keinen Drop-in mit DSN mehr, ruft ebenfalls
  `write_service_secrets` auf und entfernt ein altes `pg-mirror.conf`.
- `update.sh`: Wenn die Unit noch `Environment=HH_SECRET_KEY=` enthält oder
  `pg-mirror.conf` existiert → neu schreiben (NEEDS_REWRITE). Der **bestehende**
  Schlüssel aus `secret_key` wird übernommen, nicht neu erzeugt. Die
  pg-mirror-Prüfung nutzt statt des Drop-ins die Env-Datei.
- `secret_key` und `pg_mirror.dsn` bleiben als Quelle (Backup/Restore,
  Migration). Deren Rechte bleiben unverändert (hydrahive-Gruppe darf lesen,
  der Dienst braucht das nicht mehr, Restore schon).

## Rotation (nach Deploy, einmalig auf HydrahiveHome)

`secret_key` löschen → Update → 50-systemd.sh erzeugt einen neuen Schlüssel und
schreibt die Env-Datei → Dienst-Neustart → alle melden sich neu an.

## Tests

- Shell wirklich ausführen: `write_service_secrets` mit tmp-Config → Datei 0600,
  Inhalt korrekt, ohne DSN keine DSN-Zeile, `'`/`$` im Wert unverändert.
- Unit-Vorlage enthält weder `HH_SECRET_KEY=` noch DSN, aber `EnvironmentFile=`.
- 48-postgres.sh schreibt keinen DSN in einen Drop-in.
- update.sh: Migrationsbedingungen vorhanden, pg-mirror-Prüfung ohne Drop-in.
- Gegenprobe: jeweils rot am alten Stand.

## Nicht in diesem Plan

- macOS (`modules-mac/50-launchd.sh`, Plist-Rechte) → gesondert prüfen.
- Andere Drop-ins (`mediacenter.conf`, `agentlink.conf`) enthalten keine Secrets.
