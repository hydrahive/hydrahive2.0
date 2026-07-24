# Ollama als LLM-Provider

HydraHive kann lokale Modelle über [Ollama](https://ollama.com) nutzen. Ollama
spricht eine OpenAI-kompatible API und läuft über den bestehenden LiteLLM-Pfad.

## Einrichtung

1. Ollama starten (z.B. `ollama serve`, Default-Port `11434`) und mindestens ein
   Modell ziehen, z.B. `ollama pull llama3.1`.

2. In der Provider-Konfiguration (`llm.json` bzw. Provider-Maske) einen Provider
   anlegen:

   ```json
   {
     "id": "ollama",
     "name": "Ollama (lokal)",
     "api_base": "http://localhost:11434",
     "api_key": ""
   }
   ```

   - `api_base` ist **Pflicht** — hierüber routet HydraHive die Anfragen.
     Sie ist **frei wählbar**: auch ein Remote-Ollama auf einem anderen Host geht
     (`http://192.168.x.y:11434`).
   - `api_key` bleibt **leer** für lokale Instanzen. Nur Ollama-Cloud oder eine
     geschützte Instanz braucht einen Key (wird als Bearer-Token gesendet).

3. Modelle erscheinen automatisch im Catalog — sie werden **live** vom Endpoint
   (`{api_base}/v1/models`) geladen. Es gibt keine fest eingebaute Modell-Liste;
   jeder sieht genau seine installierten Modelle. Im Modell-Dropdown erscheinen
   sie mit dem Prefix `ollama/`, z.B. `ollama/llama3.1`.

## Tool-Use (Agenten-Aktionen)

Ob ein Agent auf einem Ollama-Modell **Tools** aufrufen kann, hängt vom Modell ab:

- **Modelle mit nativem Function-Calling** (z.B. `llama3.1`, `mistral-nemo`,
  `qwen2.5`, `firefunction-v2`) funktionieren direkt — sie liefern strukturierte
  Tool-Calls, die HydraHive ausführt.
- **Modelle ohne Function-Calling** (viele kleine Modelle wie `llama3.2:3b`)
  geben Tool-Calls u.U. als reinen **Text/JSON** aus. Das wird **nicht** als
  echter Tool-Call interpretiert (bewusste Sicherheitsentscheidung — sonst könnte
  legitimes JSON fälschlich als z.B. `shell_exec` ausgeführt werden). Solche
  Modelle sind praktisch **chat-only**.

**Symptom bei fehlendem Function-Calling:** Der Agent gibt einen Tool-Call als
rohen JSON-Text im Chat aus, statt ihn auszuführen. Dann ein Modell mit nativem
Tool-Support wählen.

## Sicherheitshinweis

Die `api_base` ist frei wählbar. Ein Admin, der einen Ollama-Provider anlegt,
kann HydraHive damit HTTP-Requests an beliebige (auch interne) URLs schicken
lassen (SSRF-Fläche). Das liegt in der Verantwortung des Provider-Admins, der
ohnehin privilegierten Zugriff hat.

## Kein Streaming

Ollama läuft über den non-streaming LiteLLM-Pfad. Der Chat aktualisiert erst,
wenn die Antwort vollständig ist (kein Token-für-Token-Streaming wie bei Claude).
