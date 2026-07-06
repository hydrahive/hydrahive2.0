# Gedächtnis — was deine Agenten sich merken

## Was ist das?

Hier siehst du, woran sich ein Agent **über einzelne Gespräche hinaus** erinnert.
Ein normaler Chat ist nach dem Schließen „vergessen" — das Gedächtnis ist der
Ort, an dem wichtige Dinge dauerhaft bleiben: Notizen, gelernte Fakten und die
verdichtete Essenz vergangener Sitzungen.

Du wählst rechts einen **Agenten** aus und siehst dann seinen Erinnerungsstand in
drei Reitern.

## Die drei Reiter

### 1. Memory (Notizen)

Konkrete Merk-Einträge, die der Agent selbst anlegt oder die du ihm gibst. Jeder
Eintrag hat:

- **Schlüssel** — der Name/das Stichwort, unter dem die Notiz abgelegt ist
  (z.B. `projekt.deployment-weg`).
- **Inhalt** — der eigentliche Merktext.
- **Konfidenz** — wie verlässlich der Agent diese Notiz einschätzt (0–1). Wird ein
  Eintrag mehrfach bestätigt, steigt die Konfidenz; widersprüchliche neue Infos
  können alte Einträge als veraltet markieren.
- **Projekt** — zu welchem Projekt die Notiz gehört (oder global).
- **Aktualisiert** — wann zuletzt geändert.

### 2. Kristalle

Ein **Kristall** ist die automatisch verdichtete Essenz einer abgeschlossenen
Sitzung — das „Destillat", damit nicht jedes Detail, aber das Wesentliche erhalten
bleibt. Ein Kristall enthält typischerweise:

- **Key Outcomes** — was dabei herauskam.
- **Lessons Learned** — was gelernt wurde.
- **Betroffene Dateien** — womit gearbeitet wurde.

So bleibt der rote Faden über viele Sitzungen erhalten, ohne dass der Agent den
kompletten alten Chat mitschleppen muss.

### 3. Sessions

Die Liste der vergangenen **Sitzungen** dieses Agenten — mit dem ursprünglichen
Prompt und den festgehaltenen Beobachtungen. Nützlich, um nachzuvollziehen, was
wann passiert ist.

## Suchen und Filtern

- **Suche** — durchsucht **Schlüssel und Inhalt** der Einträge.
- **Projekt** — auf ein bestimmtes Projekt einschränken (Projekt-ID).
- **Abgelaufene anzeigen** — auch Einträge einblenden, die ein Ablaufdatum
  erreicht haben (normalerweise ausgeblendet).

## Schritt-für-Schritt: Erinnerungen ansehen

1. Rechts den **Agenten** wählen.
2. Reiter **Memory** öffnen — die aktiven Notizen erscheinen.
3. Über die **Suche** nach einem Stichwort filtern.
4. Nicht mehr gewünschte Einträge lassen sich einzeln **löschen**.

## Typische Fragen

- **„Warum weiß der Agent das noch?"** — Weil es als Memory-Eintrag oder Kristall
  gespeichert ist. Hier kannst du es einsehen und bei Bedarf löschen.
- **„Ein Eintrag ist veraltet/falsch"** — Löschen. Der Agent kann bei Bedarf eine
  neue, korrekte Notiz anlegen.
- **„Wo ist mein alter Chat?"** — Im Reiter **Sessions**; die verdichtete Fassung
  unter **Kristalle**.

## Tipps

- **Konfidenz als Hinweis lesen**: niedrige Konfidenz = der Agent ist sich unsicher.
- **Projekt-Filter nutzen**, wenn ein Agent in mehreren Projekten arbeitet — sonst
  vermischen sich die Notizen optisch.
- **Aufräumen erlaubt**: veraltete Einträge zu löschen hält den Agenten fokussiert.
