# Lokale ComfyUI- und Cloud-Medienmodelle gezielt auswählen

## Ziel

Bild- und Videogenerierung muss für Nutzer verständlich zwischen Cloud-Modellen
(OpenRouter) und lokal auf der GPU ausgeführten ComfyUI-Workflows umschaltbar
sein. Die Wahl eines lokalen Modells muss sowohl als globaler Standard als auch
pro Atelier-Generierung funktionieren und darf nicht versehentlich einen
Cloud-Aufruf auslösen.

## Bestand

- Der Core erkennt `local:<backend>/<workflow>` bereits in `generate_image`
  und `generate_video`; explizite lokale IDs und lokale Defaults laufen über
  die gemeinsame Backend-Registry.
- `GET /api/llm/media-models?category=image|video` liefert Cloud- und lokale
  Modelle; lokale Einträge tragen `local: true` und einen Provider-Namen.
- Atelier reicht lokale IDs für Bild und Video bereits an die Registry durch.
- Die globale Default-Modelle-Ansicht lädt ihre Optionen bisher ausschließlich
  aus dem allgemeinen LLM-Registry-Katalog. Lokale ComfyUI-Workflows sind dort
  nicht auswählbar.
- Der Video-Dialog gruppiert bereits Cloud und lokale Modelle. Der Bilddialog
  zeigt beide Quellen dagegen als ununterscheidbare Liste.

## UX-Entscheidung

Für **Bild** und **Video** gibt es jeweils zwei klar getrennte Quellen:

1. **Cloud / OpenRouter** – externe, kostenpflichtige Modelle.
2. **Diese WKS / ComfyUI** – lokal ausgeführte Workflows, mit Backend-Namen.

Die Quelle ist keine zweite Konfiguration: gespeichert wird weiterhin nur die
kanonische Modell-ID. Cloud-IDs bleiben unverändert, lokale IDs beginnen mit
`local:`. So ist der gewählte Wert zugleich die vollständige Routing-Entscheidung.

### Globale Standardauswahl

Im Bereich *LLM → Standardmodelle* werden Bild und Video über einen eigenen
Media-Picker gewählt. Er lädt `GET /api/llm/media-models` statt des allgemeinen
LLM-Katalogs, gruppiert die Optionen sichtbar nach Cloud und WKS/ComfyUI und
speichert die unveränderte ID in `media_models.image` bzw. `.video`.

Chat, Embeddings, Musik, Sprache und Transkription bleiben im bestehenden
Registry-Picker; sie können nicht versehentlich auf einen Bild-/Video-Workflow
zeigen.

### Atelier

Die Bild- und Video-Modelldropdowns zeigen dieselbe Gruppierung. Lokale Modelle
werden mit einer verständlichen Kennzeichnung wie `Lokal · Lokale GPU (ComfyUI)`
und ohne Cloud-Kostenhinweis angezeigt. Modell-spezifische Beschränkungen
(Dauer, Seitenverhältnis, Start-/Endbild) bleiben serverseitig maßgeblich.

## Routing- und Sicherheitsregeln

- `local:` darf nur gegen einen in `llm.json.media_backends` konfigurierten
  Workflow aufgelöst werden.
- Bildaufrufe akzeptieren nur lokale Workflows mit `category: image`; Video
  entsprechend nur `category: video`. Ein Kategorienfehler liefert eine klare
  Fehlermeldung, nie einen Cloud-Fallback.
- Lokale Modelle umgehen die OpenRouter-Key-Prüfung; nichtlokale Modelle nehmen
  ausschließlich den bestehenden Cloud-Pfad.
- Backend-/Workflow-Konfiguration bleibt admin-only. Nicht-Admins können nur
  die freigegebenen Modell-IDs auswählen.
- Ergebnisdownloads bleiben auf den bereits konfigurierten Backend-Pfad
  beschränkt; keine von Backends gelieferte beliebige Folge-URL wird akzeptiert.

## Akzeptanzkriterien

- [ ] Admin kann SDXL oder Wan als globalen Bild-/Videostandard auswählen.
- [ ] Das Default-Modell wird nach Reload korrekt angezeigt und gespeichert.
- [ ] Ein Core-Bild-/Videoaufruf mit lokalem Default erreicht ComfyUI, ohne
      OpenRouter-Key zu benötigen.
- [ ] Falsche lokale Kategorie (Bildmodell bei Video bzw. umgekehrt) wird
      verständlich abgelehnt.
- [ ] Atelier gruppiert Bild und Video jeweils sichtbar in Cloud und lokal.
- [ ] Auswahl eines lokalen Atelier-Modells erzeugt lokal ein Ergebnis; Auswahl
      eines Cloud-Modells behält den bisherigen OpenRouter-Pfad.
- [ ] Relevante Core-, Atelier- und Frontendtests sind grün.

## Nicht enthalten

- Automatisches GPU-VRAM-Scheduling oder Unterbrechen paralleler Ollama-Jobs.
- Neue ComfyUI-Modelle/Workflows über SDXL und Wan hinaus.
- Lokale Musik-, TTS- oder Transkriptionsmodelle.
