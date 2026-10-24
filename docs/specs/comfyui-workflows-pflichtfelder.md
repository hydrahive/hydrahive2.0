# Mitgelieferte ComfyUI-Abläufe: Pflichtfelder vollständig

Task ef4e0e10. `installer/media-workflows/wan21-flf2v.json` (Video aus Start- und Endbild) wird von
ComfyUI 0.21.1 mit 400 `required_input_missing` abgelehnt. Die Knoten 15 und 16 (`CLIPVisionEncode`) haben kein
Pflichtfeld `crop` (Auswahl `center` oder `none`). Das betrifft jeden, der Lokale Medien mit diesem Ablauf nutzt.

Gemessen am 24.10. über `/object_info` der Workstation, nur gelesen: Alle vier mitgelieferten Abläufe gegen die
Pflichtfelder geprüft. Nur diese beiden Stellen fehlen.

## Änderung

- Knoten 15 und 16 bekommen `"crop": "none"`. Ohne Zuschnitt bleibt das Bild ganz, das ist das bisherige Verhalten
  älterer ComfyUI-Versionen.
- Ein neuer Test prüft jeden Knoten aller mitgelieferten Abläufe gegen die Pflichtfelder. Die stehen als Datei in
  `core/tests/fixtures/comfyui_required_inputs.json` (Stand ComfyUI 0.21.1). Kommt ein neuer Knotentyp dazu,
  meldet der Test das, damit die Datei nachgezogen wird.
- Ein echter Videolauf ist nicht Teil der Prüfung (17 min auf der Workstation, Task 1d608284).
