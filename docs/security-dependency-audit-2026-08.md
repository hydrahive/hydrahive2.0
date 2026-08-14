# Dependency-Audit — August 2026

> Anlass: LiteLLM-Supply-Chain-Angriff vom 24.03.2026 (Versionen 1.82.7/1.82.8
> mit Credential-Stealer, ~40 Minuten auf PyPI). Prüfung ob HydraHive betroffen
> war — und was der Anlass sonst noch zutage förderte.

## 1. LiteLLM-Vorfall: nicht betroffen

| Prüfung | Ergebnis |
|---|---|
| Installierte Version | **1.83.14** — kompromittiert waren nur 1.82.7 / 1.82.8 |
| Installationsdatum | 05.05.2026 (Angriff: 24.03.2026) |
| Repo-Beginn | 28.04.2026 — **0 Commits** im Angriffszeitraum |
| Hash-Verifikation gegen `RECORD` | **2.681 Dateien, 0 Abweichungen** |
| IOC-Suche (Sandclock / TeamPCP) | keine Treffer |
| `/etc/hosts`, cron-Persistenz | sauber |
| Exfiltrations-Repos im GitHub-Konto | keine |

Das Repo `hydrahive/hydrahive` wurde am 24.03.2026 erstellt — zufällige
Datumsgleichheit, es ist HydraHive 1 (Vorgängerprojekt), kein Datendump.

## 2. Ursache behoben: fehlende Versionsdeckel

`litellm>=1.40` war **ohne Obergrenze**. Ein Build im März hätte die
Schadversion gezogen — wir hatten nur Glück mit dem Zeitpunkt. Die CI baut
bei jedem Push frisch (`pip install -e core/`).

Deckel jetzt auf die jeweils nächste Major-Version gesetzt: Sicherheits-Patches
kommen weiter durch, ein unbemerkter Sprung über eine Bruchkante nicht.
Alle 21 direkten Abhängigkeiten geprüft — **0 Konflikte** mit dem Produktivstand.

## 3. Nebenbefund: 97 bekannte Schwachstellen in 18 Paketen

`pip-audit` über die Produktivumgebung (152 Pakete). **Nicht** Folge des
Angriffs — normale CVE-Alterung, aber bisher unbemerkt.

| Paket | installiert | Vulns | Fix ab |
|---|---|---:|---|
| pillow | 12.2.0 | 20 | 12.3.0 |
| gitpython | 3.1.50 | 15 | 3.1.58 |
| aiohttp | 3.13.4 | 14 | 3.14.3 |
| yt-dlp | 2026.3.17 | 8 | 2026.7.4 |
| **pyjwt** | 2.12.1 | 8 | 2.13.0 |
| **starlette** | 1.0.0 | 7 | 1.3.1 |
| **cryptography** | 48.0.0 | 4 | 50.0.0 |
| urllib3 | 2.6.3 | 3 | 2.7.0 |
| **python-multipart** | 0.0.27 | 3 | 0.0.31 |
| mcp | 1.27.0 | 3 | 1.28.1 |
| litellm | 1.83.14 | 3 | 1.84.0 |

**Fett = sicherheitsrelevanter Pfad:** `starlette` und `python-multipart`
sitzen am HTTP-Eingang (Request-Parsing, Uploads), `pyjwt` an der
Token-Prüfung, `cryptography` unter der gesamten TLS-/Krypto-Schicht.
Die Instanz ist öffentlich erreichbar.

### Wichtig: Die neuen Deckel blockieren diese Fixes nicht

Probelauf eines frischen Builds mit den gesetzten Grenzen zieht bereits:
`pillow 12.3.0`, `pyjwt 2.13.0`, `python-multipart 0.0.32`, `starlette 1.6.0`,
`cryptography 48.0.1`, `litellm 1.96.2`.

Das heißt: **Ein Update der Produktivumgebung schließt den Großteil der
97 Funde ohne jede Code-Änderung.** Bisher wurde nur nie aktualisiert.

## 4. CI-Erweiterung

`pytest.yml` führt jetzt `pip-audit` aus und schreibt das Ergebnis in die
Job-Summary — `continue-on-error: true`.

Bewusst nicht blockierend: Neue CVEs in transitiven Abhängigkeiten erscheinen
täglich. Ein harter Fail würde fremde PRs blockieren, ohne dass deren Autor
etwas dafür kann. Der Schritt soll sichtbar machen, nicht erziehen.

## 5. Offen

**Produktivumgebung aktualisieren** (`pip install -U -e core/` + Service-Neustart,
danach Testlauf). Nicht Teil dieser Änderung, weil es ein Deployment ist und
Till entscheidet, wann die Instanz neu startet.

Ein vollständiges Hash-Lockfile (`--require-hashes`) über alle 152 Pakete wäre
die härteste Absicherung, wurde hier aber **nicht** umgesetzt: Es müsste bei
jeder Abhängigkeitsänderung neu erzeugt werden. Deckel + Audit decken das
Angriffsszenario zu einem großen Teil ab, bei deutlich weniger Pflegeaufwand.
