# Live-Embedding-Katalog

## Was

Die Standardmodell-Auswahl für Embeddings verwendet denselben kanonischen Live-Modellkatalog wie die Agenten-Auswahl. Es erscheinen ausschließlich Embedding-Modelle von eingerichteten Providern, die der jeweilige Provider aktuell meldet. Lokales Ollama funktioniert über `api_base` ohne verpflichtenden API-Key.

## Warum

Die bisherige separate `EMBED_MODELS`-Liste zeigt veraltete NVIDIA-Modelle, begrenzt OpenRouter auf einen einzelnen Slug und schließt Ollama vollständig aus. Dadurch weicht das Embedding-Menü vom tatsächlichen Modellbestand ab und kann nicht funktionierende Modelle anbieten.

## Wie

1. Der Provider-Katalog liefert Live-Modelle mitsamt Modalitäten und bekannten Metadaten.
2. Die Registry klassifiziert Katalogmodelle als `embed`, wenn die Providerdaten eine Embedding-Modalität melden oder bekannte Metadaten das Modell als Embedding-Modell markieren.
3. Die Registry ergänzt keine separaten statischen Embedding-Einträge mehr.
4. Der Embedding-Client leitet Provider und API-Basis aus der kanonischen Modell-ID und der Provider-Konfiguration ab. Für Ollama ist der API-Key optional.
5. Die Vektordimension bleibt zwingend bekannt, bevor ein Modell als persistentes pgvector-Standardmodell verwendet wird. Bekannte Dimensionen stammen aus Metadaten; lokale Modelle können per Probe ermittelt werden.

## Akzeptanzkriterien

- Nicht eingerichtete Provider tragen keine Embedding-Modelle bei.
- Nicht mehr live gelistete NVIDIA-/OpenRouter-Modelle erscheinen nicht im Embedding-Picker.
- Installierte Ollama-Embedding-Modelle erscheinen; nicht installierte Modelle erscheinen nicht.
- Ollama funktioniert ohne API-Key.
- Chatmodelle werden nicht als reine Embedding-Modelle angeboten.
- Dynamische Modell-IDs werden mit dem korrekten Provider und ohne doppelten Provider-Präfix an dessen Embedding-Endpunkt gesendet.
- Die pgvector-Dimension ist für auswählbare Modelle bekannt und ein Modellwechsel nutzt weiterhin den bestehenden Rebuild-Pfad.

## Nicht enthalten

- Download oder Installation nicht vorhandener Ollama-Modelle aus dem Standardmodell-Picker.
- Automatische Auswahl eines neuen Standardmodells.
- Änderungen am Frontend-Picker; dieser nutzt bereits `/api/llm/models?modality=embed`.
