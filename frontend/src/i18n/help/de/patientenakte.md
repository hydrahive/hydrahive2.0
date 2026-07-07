# Meine Akte — deine strukturierte Patientenakte

## Was ist das?

Die **Akte** ist deine persönliche, digitale **Gesundheitsakte**: Diagnosen,
Medikamente, Laborwerte, Allergien, Arztbesuche und Dokumente an einem Ort,
sauber strukturiert und durchsuchbar. Du kannst Daten selbst pflegen, aus offiziellen
Quellen **importieren** und Verläufe über die Zeit ansehen.

> **Wichtig:** Das ist ein persönliches Ablage- und Übersichts-Werkzeug, **kein
> medizinisches Diagnose-System**. Es ersetzt keine ärztliche Beratung.

## Die Bereiche (Navigation links)

**Meine Akte**
- **Übersicht** — Dashboard mit dem Wichtigsten auf einen Blick.
- **Zeitstrahl** — alle Ereignisse chronologisch.
- **Diagnosen**, **Medikamente**, **Laborwerte**, **Allergien**, **Ereignisse**,
  **Bildgebung**, **Ärzte**, **Dokumente**, **Notizen** — je eine Liste zum
  Pflegen und Nachschlagen. Laborwerte lassen sich als **Verlaufskurve** anzeigen.

**Import**
- **eGA / FHIR** — offizielle Gesundheitsdaten importieren (siehe unten).

**Tracking**
- **Apple Health** und **Schlaf** — Verlaufsdaten aus deinem Health-Tracking.

## Daten importieren (eGA / FHIR)

Du kannst deine Kassen-Gesundheitsakte importieren, statt alles abzutippen:

1. In der **TK-Safe App** deine elektronische Gesundheitsakte (eGA) **exportieren**
   → du erhältst eine **ZIP-Datei**.
2. Im Import-Bereich **TK-eGA-ZIP** hochladen (alternativ ein **FHIR-Bundle**).
3. HydraHive liest die Daten ein — du siehst, wie viele Einträge **neu** und wie
   viele **aktualisiert** wurden.

**Wichtig:** Importierte Daten sind **read-only** und bleiben **getrennt** von
deiner selbst gepflegten Akte. So vermischt sich Offizielles nicht mit eigenen
Einträgen. Der Import zeigt zusätzlich einen **Kosten-Überblick** (abgerechnete
Arztbesuche, Apothekenpreise, deine Zuzahlung) und einen eigenen Zeitstrahl.

## Verifizieren

Einträge können als **manuell verifiziert** markiert werden (Häkchen). Nicht
verifizierte Einträge (z.B. automatisch erkannte) sind entsprechend gekennzeichnet
und lassen sich per Klick bestätigen — so behältst du den Überblick, was du selbst
geprüft hast.

## Schritt-für-Schritt: Eintrag anlegen

1. Links den passenden Bereich wählen (z.B. **Medikamente**).
2. Einen neuen Eintrag hinzufügen und die Felder ausfüllen.
3. Speichern. Über die Aktionen kannst du Einträge später **bearbeiten**,
   **löschen** oder **verifizieren**.

## Typische Fragen

- **„Daten konnten nicht geladen werden"** — Verbindungsproblem; Seite neu laden.
- **„Wo kommt mein Import her?"** — TK-Safe App → Akte exportieren → ZIP hier
  hochladen. Ohne Export gibt es nichts zu importieren.
- **„Warum kann ich importierte Einträge nicht ändern?"** — Sie sind bewusst
  read-only (Originaltreue). Eigene Ergänzungen macht du in der eigenen Akte.

## Tipps

- **Erst importieren, dann ergänzen**: Der eGA-Import spart viel Tipparbeit; eigene
  Details fügst du danach hinzu.
- **Laborwerte als Verlauf** ansehen — Trends erkennt man in der Kurve leichter als
  in einer Tabelle.
- **Verifizieren nutzen**, um geprüfte von ungeprüften Einträgen zu unterscheiden.
