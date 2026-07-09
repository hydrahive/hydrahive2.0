# Buddy — dein persönlicher Assistent

## Was ist das?

Buddy ist die **Startseite** von HydraHive und dein persönlicher KI-Assistent. Anders als die **Werkstatt** (wo du gezielt mit spezialisierten Agenten arbeitest) ist Buddy dein ständiger Begleiter für alles Alltägliche: Fragen stellen, Dinge notieren lassen, Aufgaben anstoßen, den Überblick behalten.

Buddy hat eine **eigene, durchgehende Konversation** (eine Session), die erhalten bleibt — du kannst also jederzeit weiterreden, wo ihr aufgehört habt. Das animierte **Hydra-Maskottchen** links zeigt dir seinen Zustand: ruhig (wartet), arbeitend (denkt/nutzt Werkzeuge) oder sprechend (Sprachausgabe läuft).

Buddy ist ein vollwertiger Agent: Er kann **Werkzeuge benutzen** (Dateien lesen, im Web suchen, E-Mails senden, Bilder generieren …) — welche genau, legst du in den Einstellungen fest.

## Was kann ich hier tun?

- **Einfach lostippen** — stell eine Frage oder gib einen Auftrag, Enter drücken. Die Antwort erscheint live.
- **Befehle nutzen** — Nachrichten, die mit `/` beginnen, sind Kurzbefehle (siehe unten).
- **Modell wählen** — oben der Modell-Auswähler: welches KI-Modell Buddy gerade benutzt.
- **Projekt-Kontext setzen** — mit dem Projekt-Auswähler bindest du Buddy an ein Projekt; dann arbeiten seine Datei-Werkzeuge im Projekt-Ordner.
- **Denk-Tiefe steuern** — die „Reasoning Effort"-Pille bestimmt, wie gründlich das Modell nachdenkt (mehr Tiefe = langsamer, aber durchdachter; nur bei Modellen, die das können).
- **Cockpit-Slots steuern** — Musik, Extensions sowie Spiele & Widgets liegen rechts in einer Cockpit-Rail. Du kannst Slots einklappen oder ausblenden; gespeichert wird serverseitig pro Buddy, nicht im Browser-LocalStorage.
- **Verbrauch sehen** — der Usage-Chip zeigt Provider, Token des letzten Turns und — wenn Preisdaten bekannt sind — eine grobe Kostenschätzung. Ist kein Preis/Quota bekannt, steht dort ehrlich „Preis n/a“.
- **Buddy anpassen** — über das Zahnrad kommst du zu den Buddy-Einstellungen (Name, Charakter, Werkzeuge …).

## Wichtige Begriffe

- **Buddy-Session** — die eine, fortlaufende Konversation mit deinem Assistenten. Sie bleibt gespeichert, bis du sie mit `/clear` frisch startest.
- **Werkzeuge (Tools)** — Fähigkeiten, die Buddy über reines Reden hinaus hat (Web-Suche, Dateizugriff, Mail, Medien erzeugen …).
- **Compaction** — ältere Nachrichten werden zu einer Zusammenfassung verdichtet, damit die Konversation nicht zu lang (und teuer) wird.
- **Reasoning Effort** — Denk-Aufwand des Modells pro Antwort (minimal/niedrig/mittel/hoch).
- **Soul / Charakter** — Buddys Persönlichkeit: Name, Ton (locker/professionell/knapp) und ein frei formulierbarer Charaktertext.

## Kurzbefehle (Slash-Commands)

Tippe einen dieser Befehle als Nachricht:

| Befehl | Wirkung |
|--------|---------|
| `/help` | Zeigt diese Befehlsliste im Chat |
| `/clear` (oder `/reset`) | Startet einen frischen Chat — die alte Session bleibt im Verlauf erhalten |
| `/remember [name]` | Speichert den aktuellen Verlauf als dauerhafte Notiz (Memory) |
| `/model [name]` | Zeigt das aktuelle Buddy-Modell oder wechselt es |
| `/character` | Würfelt Buddy einen neuen Charakter |
| `/compact` | Verdichtet die aktuelle Session manuell (spart Tokens) |
| `/tokens` | Zeigt Token-Stand und wie voll das Kontextfenster ist |
| `/title <text>` | Benennt die Buddy-Session um |
| `/system` | Zeigt den aktuellen System-Prompt |
| `/tools` | Listet die im Backend verfügbaren Werkzeuge |
| `/agent` | Zeigt Infos zum Buddy-Agenten |
| `/soul` | Zeigt die Bausteine von Buddys Persönlichkeit |
| `/export` | Gibt den Verlauf als Markdown aus |

## Schritt-für-Schritt

### Das erste Gespräch

1. Buddy ist beim Öffnen von HydraHive schon da (Startseite `/`).
2. Tippe unten deine Nachricht — z.B. *„Fasse mir zusammen, was HydraHive kann"* — und drücke **Enter**.
3. Beobachte, wie die Antwort live erscheint. Nutzt Buddy dabei ein Werkzeug (z.B. Web-Suche), siehst du das im Verlauf.

### Buddy an ein Projekt binden

1. Oben den **Projekt-Auswähler** öffnen.
2. Ein Projekt wählen — ab jetzt arbeiten Buddys Datei-Werkzeuge im Ordner dieses Projekts.
3. Zum Lösen der Bindung wieder auf „kein Projekt" stellen.

### Buddys Persönlichkeit & Werkzeuge einstellen

1. Oben rechts auf das **Zahnrad** (Buddy-Einstellungen).
2. Tabs:
   - **Identität** — Name, Charaktertext, Sprache (de/en/automatisch), Ton (locker/professionell/knapp).
   - **Kontext** — was Buddy dauerhaft über dich/deine Umgebung wissen soll.
   - **Werkzeuge** — welche Tools Buddy nutzen darf (nur aktivieren, was du wirklich brauchst).
   - **Mail** — erscheint nur, wenn die Mail-Werkzeuge aktiv sind (Postfach-Zugang).
   - **Compaction** — ab wann automatisch verdichtet wird.
3. **Speichern**. Änderst du Grundlegendes an der Identität, startet Buddy ggf. eine frische Session.

### Einen langen Verlauf aufräumen

- Wird die Konversation sehr lang, tippe `/compact` — ältere Teile werden zusammengefasst, der rote Faden bleibt.
- Willst du komplett neu anfangen: `/clear`. Der alte Verlauf geht nicht verloren, er rückt nur in den Hintergrund.

## Typische Fragen

- **„Buddy oder Werkstatt — was nehme ich?"** Buddy = dein persönlicher Alltags-Assistent (eine durchgehende Unterhaltung). Werkstatt = gezieltes Arbeiten mit mehreren spezialisierten Agenten in getrennten Sessions.
- **„Buddy antwortet nicht / lädt ewig"** — Prüfe, ob unter **LLM-Konfiguration** ein Modell eingerichtet und ein gültiger Schlüssel hinterlegt ist. Ohne konfiguriertes Modell kann Buddy nicht denken.
- **„Buddy kann X nicht (z.B. keine Mail senden)"** — Das Werkzeug ist wahrscheinlich nicht aktiviert. Zahnrad → **Werkzeuge** → passendes Tool einschalten.
- **„Wie merkt sich Buddy etwas dauerhaft?"** — Mit `/remember` oder indem du es im Tab **Kontext** hinterlegst.

## Tipps

- **Werkzeuge sparsam aktivieren**: Je weniger, desto treffsicherer wählt Buddy das richtige. Aktiviere nur, was du regelmäßig brauchst.
- **Reasoning Effort dosieren**: Für schnelle Fragen niedrig lassen, für knifflige Aufgaben hochdrehen.
- **Kontext pflegen**: Was Buddy dauerhaft wissen soll (dein Name, Vorlieben, Projektumfeld), gehört in den **Kontext**-Tab — dann musst du es nicht in jeder Nachricht wiederholen.
