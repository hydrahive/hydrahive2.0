---
name: writing-plans
description: Umsetzungsplan aus einer Spec – Entscheidungen statt Code-Abschrift, kleine Aufgaben mit eigenem Test, Schnittstellen zwischen Aufgaben, Review-Fokus für ungetestete Fälle, Selbstprüfung, Freigabe vor dem Bauen.
when_to_use: Wenn eine Spec oder klare Anforderungen für eine mehrteilige Aufgabe vorliegen, bevor Code angefasst wird – Features mit mehr als 3 Dateien, Refactorings, neue API-Endpunkte, Migrationen, Aufträge an Projekt-Agenten.
tools_required: [file_write, file_read]
---

# Umsetzungsplan schreiben

> Nach „writing-plans“ aus Superpowers v7.0.2 (github.com/obra/superpowers, MIT, © Jesse Vincent), für HydraHive übersetzt und angepasst.

## Für wen der Plan ist

Schreib für eine fähige Entwicklerin, die diese Codebasis und diese Spec nicht kennt. Sie schreibt sauberen Code, sobald sie die genaue Schnittstelle und den genauen Test kennt, und trifft überall dort eine vernünftige Wahl, wo der Plan etwas offen lässt. **Was sie nicht wissen kann, ist, was du entschieden hast:** welche Dateien, welche Namen und Signaturen, welche Werte aus der Spec, welche Tests jede Aufgabe beweisen. Genau das steht im Plan. Kleine Aufgaben, DRY, YAGNI, Test zuerst, häufige Commits.

Sag zu Beginn: „Ich schreibe den Umsetzungsplan.“

**Ablage:** `docs/plans/<JJJJ-MM-TT>-<thema>.md` im Repo, das geändert wird (Vorgabe des Nutzers geht vor). Bei Aufträgen an einen Projekt-Agenten geht der Plan zusammen mit dem Zieldokument mit (`ziel_doc`).

## Umfang prüfen

Deckt die Spec mehrere unabhängige Teilsysteme ab, schlag getrennte Pläne vor – einen je Teilsystem. Jeder Plan liefert für sich lauffähige, testbare Software.

**HydraHive-Grenze:** Ein Projekt-Agent bricht nach 20 Minuten ab. Schneide den Plan so, dass jede Aufgabe (oder jede Gruppe, die an einen Agenten geht) darin fertig wird, mit Commit und Push nach jedem Teilstück.

## Dateistruktur zuerst

Bevor du Aufgaben festlegst: Welche Dateien entstehen oder ändern sich, und wofür ist jede zuständig? Hier fallen die Schnitt-Entscheidungen.

- Einheiten mit klaren Grenzen und Schnittstellen; jede Datei hat eine Aufgabe.
- Kleinere, fokussierte Dateien sind leichter zu überblicken und sicherer zu ändern.
- Was sich gemeinsam ändert, liegt zusammen – nach Zuständigkeit schneiden, nicht nach technischer Schicht.
- In bestehendem Code den vorhandenen Mustern folgen. Ist eine Datei, die du änderst, unhandlich geworden, darf eine Aufteilung in den Plan.

## Aufgaben richtig zuschneiden

Eine Aufgabe ist die kleinste Einheit mit eigenem Testzyklus, die eine eigene Prüfung wert ist. Setup, Konfiguration, Gerüst und Doku gehören in die Aufgabe, deren Ergebnis sie braucht. Trenne nur dort, wo ein Reviewer die eine Aufgabe ablehnen und die Nachbarin annehmen könnte. Jede Aufgabe endet mit einem eigenständig prüfbaren Ergebnis.

**Ein Schritt ist eine Handlung mit prüfbarem Ergebnis:** „Test schreiben“ – „Test laufen lassen, er muss rot sein“ – „minimal umsetzen“ – „Test grün“ – „Commit“.

## Kopf des Plans (Pflicht)

```markdown
# Umsetzungsplan: [Thema]

**Ziel:** [ein Satz, was danach existiert]
**Ansatz:** [2–3 Sätze]
**Technik:** [wichtige Sprachen/Bibliotheken]
**Spec:** [Pfad zur Spec bzw. zum Zieldokument – der Plan argumentiert aus der Spec, beide gehören zusammen]

## Globale Vorgaben
[Projektweite Anforderungen der Spec – Versionsgrenzen, Abhängigkeits-Obergrenzen (core/pyproject.toml),
Benennungs- und Textregeln, Sprache (Oberfläche und Meldungen Deutsch), Plattform (Linux und Mac) –
je eine Zeile, Werte wörtlich aus der Spec. Gilt für jede Aufgabe mit.]

## Review-Fokus
[Die bis zu fünf Eingaben oder Fehlerfälle, die die Spec nahelegt, die aber kein Test einer Aufgabe abdeckt
und die einen Menschen am ehesten treffen – je eine Zeile: Eingabe/Lage und das Verhalten, das ein
vernünftiger Mensch erwartet, das Wahrscheinlichste zuerst. Die Spec sagt, was die Software können muss,
nicht alles, was ihr begegnet – ihr Schweigen ist keine Erlaubnis, dabei kaputtzugehen.
Für jede Zeile den passenden Test in die Aufgabe eintragen, der der Code gehört.]
```

## Aufbau einer Aufgabe

````markdown
### Aufgabe N: [Baustein]

**Dateien:**
- Neu: `genauer/pfad/datei.py`
- Ändern: `genauer/pfad/bestehend.py:123-145`
- Test: `core/tests/test_genau.py`

**Schnittstellen:**
- Nutzt: [was diese Aufgabe aus früheren Aufgaben verwendet – genaue Signaturen]
- Liefert: [worauf spätere Aufgaben bauen – genaue Namen, Parameter- und Rückgabetypen.
  Wer die Aufgabe umsetzt, sieht nur sie; hier steht, wie die Nachbarn heißen.]

- [ ] **Schritt 1: Test schreiben, der scheitert**

```python
def test_genaues_verhalten():
    assert funktion(eingabe) == erwartet
```

- [ ] **Schritt 2: Test laufen lassen – muss rot sein**
  `cd core && PYTHONPATH=src pytest tests/test_genau.py::test_genaues_verhalten -q`
  Erwartet: FAIL mit „funktion not defined“

- [ ] **Schritt 3: `funktion(eingabe: Typ) -> Ergebnis` in `genauer/pfad/datei.py` umsetzen**
  Eine Zeile zum Weg, wenn Signatur und Test eine Wahl lassen; ein Code-Block nur für einen Algorithmus,
  den beide nicht festlegen.

- [ ] **Schritt 4: Test grün**  – gleicher Befehl, Erwartet: PASS

- [ ] **Schritt 5: Commit und Push**
  `git add … && git commit -m "feat(bereich): …" && git push`
````

## Was ein Schritt enthält

Ein Schritt ist fertig, wenn genau eine vernünftige Umsetzung daraus folgt – eindeutig, nicht vollständig. Jede Art Schritt trägt nur, was sie eindeutig macht:

- **Test-Schritt:** Name des Tests und seine Zusicherungen, als Code, mit den genauen Werten der Spec.
- **Code-Schritt:** genaue Signatur (Name, Parameter, Rückgabetyp), die Datei und die Werte, die die Spec festlegt. Den Rumpf schreibt die Umsetzerin. Ein Rumpf steht nur da für einen Algorithmus, den Signatur und Tests nicht bestimmen, oder für wörtlich festgelegten Text.
- **Prüf-Schritt:** der Befehl und die Ausgabe, die „bestanden“ bedeutet.
- **Verweis auf eine andere Aufgabe:** über deren Schnittstellen-Block, ohne deren Code zu wiederholen.

**Ein Plan ist die Menge der Entscheidungen, die die Umsetzerin nicht allein treffen kann.** Ein Plan, der länger ist als der Code, den er beschreibt, hat den Code geschrieben statt ihn zu planen. Zeilen, die nichts entscheiden („TBD“, „Randfälle behandeln“, „passende Validierung“, „Tests für das Obige“, ein Typ oder eine Funktion, die keine Aufgabe definiert), sind der umgekehrte Fehler. Die Selbstprüfung fängt beides.

## HydraHive-Besonderheiten

- **Tests:** lokal nur gezielte Tests (die Platte ist langsam). „Grün“ heißt am Ende: die CI des PRs ist komplett grün. Bei Fixes zuerst der rote Test (Fix-Test-Guard).
- **System-Skills, i18n, Migrationen:** Änderst du `skills/system_defaults/*.md`, gehört `python3 scripts/update_skill_history.py` in den Plan; neue Oberflächentexte de/en; neue Migrationen ohne eigenes BEGIN/COMMIT schreiben.
- **Echte Proben** (Installer, Update, Geräte) als eigene Aufgabe: erst hydratest, Hauptserver nur mit Tills OK.
- **Review:** jeder PR durch hydrahive-reviewer; bei Auth, Root, Verteilung oder Schreibzugriffen zusätzlich hydrahive-security-reviewer. Merge per Merge-Commit erst bei grüner CI.
- **Aufträge an Agenten:** Abnahme-Punkte im Zieldokument (Format Buchstaben+Ziffern, z. B. `P3`), je Auftrag nur so viele Aufgaben, wie in 20 Minuten fertig werden.

## Selbstprüfung

Nach dem kompletten Plan die Spec mit frischem Blick daneben legen. Das ist eine Liste, die du selbst abarbeitest – kein Auftrag an einen anderen Agenten.

1. **Abdeckung:** Jeder Abschnitt, jede Anforderung der Spec – auf welche Aufgabe kannst du zeigen? Lücken auflisten und als Aufgabe ergänzen.
2. **Schritt-Durchsicht:** Jeder Schritt erlaubt genau eine vernünftige Umsetzung und trägt nicht mehr. Eine Zeile, die nichts entscheidet, ist eine Lücke; ein Rumpf, den Signatur und Tests schon festlegen, ist eine Abschrift. Beides beheben.
3. **Typ-Konsistenz:** Passen Typen, Signaturen und Namen in späteren Aufgaben zu denen aus früheren? `clearLayers()` in Aufgabe 3 und `clearFullLayers()` in Aufgabe 7 ist ein Fehler.
4. **Review-Fokus:** Für jede Eingabeklasse und jeden Fehlerfall, den die Spec nahelegt – gibt es eine Aufgabe, deren Tests ihn prüfen? Die fünf ungedeckten, die am ehesten treffen, stehen im Review-Fokus, jeder mit Test in seiner Aufgabe. Ein leerer Abschnitt heißt „geprüft, nichts gefunden“, nicht „übersprungen“.
5. **Verhältnis:** Vergleiche die Länge des Plans mit der Spec. Ist er ein Vielfaches davon oder bestehen die meisten Zeilen aus Code-Blöcken, ist er eine Abschrift: Rümpfe durch Signaturen, Testnamen und Zusicherungen ersetzen und prüfen, ob jeder Schritt eindeutig bleibt.

Gefundenes direkt im Plan beheben, ohne neue Prüfrunde.

## Übergabe und Freigabe

Nach dem Speichern und der Selbstprüfung: Pfad nennen und den Nutzer den **gespeicherten Plan** prüfen lassen. Zustimmung zu einer Idee oder zum Umfang ist **keine** Freigabe eines Plans, den er noch nicht gesehen hat. Gebaut wird erst nach seiner Freigabe.

Dabei die Umsetzung vorschlagen, mit Empfehlung und einem Satz Begründung aus dem Plan (wie stark die Aufgaben voneinander abhängen, wie viele es sind, was ein Fehler kosten würde):

- **Selbst umsetzen** – günstig und schnell; am Ende ein frisches Review des ganzen Branches.
- **An den Projekt-Agenten** (`ask_agent` mit `ziel_doc` und Abnahme-Punkten) – je Auftrag eine kleine Gruppe Aufgaben, danach Commits, CI und PR selbst gegenprüfen.

Hat der Nutzer die Art der Umsetzung schon festgelegt, nur fragen: „Plan liegt unter `<pfad>`. Bildet er ab, was du willst?“
