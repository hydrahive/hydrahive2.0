# Credentials — Zugangsdaten für Web-Zugriffe

## Was ist das?

Hier hinterlegst du **Zugangsdaten (Tokens, Passwörter, Schlüssel)**, die deine Agenten brauchen, um auf geschützte Webseiten oder Dienste zuzugreifen. Der Clou: Du speicherst einen Zugang **einmal** und legst per **URL-Muster** fest, wofür er gilt. Ruft ein Agent dann eine passende Adresse auf, wird der Zugang **automatisch eingehängt** — der Agent muss (und kann) das Token nicht selbst kennen.

**Sicherheit (wichtig):** Tokens tauchen **niemals** im KI-Kontext oder in Tool-Ergebnissen auf. Sie werden ausschließlich beim tatsächlichen Netzwerk-Aufruf serverseitig eingesetzt und verschlüsselt gespeichert. Das Modell „sieht" dein Passwort nie.

## Wozu brauche ich das?

Beispiele:
- Ein Agent soll ein **privates Forum** oder eine **API mit Token** abfragen.
- Ein Agent soll sich per **SSH** auf einen Server verbinden (z.B. um dort Befehle auszuführen).
- Eine Seite verlangt ein **Cookie** oder einen **Custom-Header**, um Inhalte auszuliefern.

Ohne passenden Credential bekäme der Agent nur „401 Unauthorized" oder eine Login-Seite zu sehen.

## Credential-Typen

| Typ | Wofür | Wie es gesendet wird |
|-----|-------|----------------------|
| **Bearer Token** | API-Token, moderne Web-APIs | `Authorization: Bearer <wert>` |
| **Basic Auth** | klassischer Benutzer/Passwort-Login | `Authorization: Basic <base64 von user:pass>` |
| **Cookie** | Seiten, die Session-Cookies erwarten | `Cookie: <wert>` (z.B. `session=abc123`) |
| **Custom Header** | eigene Header-Namen (z.B. `X-API-Key`) | dein Header-Name + Wert |
| **Query Parameter** | Token, das an die URL angehängt wird | `…?<param>=<wert>` |
| **SSH-Key** | SSH-Zugriff auf einen Server | privater Schlüssel + Host + User |

## Felder erklärt

- **Name** — frei wählbar (nur `a-z`, `0-9`, `_`, `-`), damit du den Zugang wiedererkennst.
- **Typ** — einer der oben genannten. Je nach Typ erscheinen passende Zusatzfelder.
- **Wert** — das eigentliche Geheimnis (Token, `user:passwort`, Cookie-String …).
- **URL-Pattern** — bestimmt, für welche Adressen der Zugang gilt. Ein **Glob-Muster**:
  - `*` = für **alle** URLs (mit Vorsicht nutzen!)
  - `https://forum.example.de/*` = nur für diesen Host und alles darunter
- **Header-Name** / **Query-Param-Name** — nur bei den Typen „Custom Header" bzw. „Query Parameter": wie das Feld heißen soll.
- **Beschreibung** — optionale Notiz für dich.

### Für SSH-Keys zusätzlich
- **Private Key (PEM)** — dein privater Schlüssel im OpenSSH- oder PEM-Format. Wird verschlüsselt gespeichert und **nie** an das Modell weitergegeben.
- **Hostname / IP** — der Server, auf den zugegriffen werden soll.
- **SSH-Username** — der Login-Name auf dem Server.

## Schritt-für-Schritt

### Ein API-Token hinterlegen (Bearer)

1. **Neuer Credential** klicken.
2. **Name** vergeben (z.B. `github-api`).
3. **Typ** = Bearer Token.
4. **Wert** = dein Token einfügen.
5. **URL-Pattern** = z.B. `https://api.github.com/*`.
6. Speichern. Ab jetzt hängt sich das Token bei Aufrufen dieser API automatisch ein.

### Einen SSH-Zugang anlegen

1. **Neuer Credential** → **Typ** = SSH-Key.
2. **Private Key** einfügen (PEM/OpenSSH), **Host** und **Username** setzen.
3. Speichern. Der Agent kann sich nun per SSH mit diesem Host verbinden, ohne den Schlüssel zu kennen.

## Typische Fehler

- **Agent bekommt weiter 401/Login-Seite** — Das **URL-Pattern** passt nicht auf die tatsächlich aufgerufene Adresse. Prüfe Schreibweise und `*`-Platzierung.
- **„Name ungültig"** — Nur `a-z`, `0-9`, `_`, `-`, maximal 50 Zeichen.
- **Zu weit gefasstes Pattern** — `*` schickt den Zugang an **jede** URL. Fasse es so eng wie möglich (nur den einen Host), damit ein Token nicht versehentlich an fremde Server geht.

## Tipps

- **So eng wie möglich**: Ein URL-Pattern sollte nur die Hosts abdecken, für die der Zugang wirklich gedacht ist.
- **Ein Zugang, viele Agenten**: Alle Agenten profitieren automatisch — du pflegst das Token nur an einer Stelle.
- **Trennung Credentials vs. LLM-Keys**: Hier geht es um Zugänge zu **externen Diensten**. Die Schlüssel für die KI-Modelle selbst liegen unter **LLM-Konfiguration**, nicht hier.
