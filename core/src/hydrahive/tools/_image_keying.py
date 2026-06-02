"""Green-Screen Chroma-Key.

OpenRouter liefert keine echte Transparenz — das Bildmodell malt das Motiv auf
reinem Grün (per `image_config.background_rgb_color` + Prompt). Dieser Key
entfernt das Grün anhand der *Grün-Dominanz* `g - max(r, b)`:

  reines Grün (0,255,0)   → Dominanz 255 → transparent
  Neon-Cyan  (0,200,255)  → Dominanz 0   → deckend (b ist genauso hoch)
  Gold/Weiß               → Dominanz 0   → deckend

Anti-Aliasing-Kanten bekommen Teil-Alpha (weicher Rand), und ein Despill zieht
den Grünstich an den Rändern raus.
"""
from __future__ import annotations

import io

from PIL import Image, ImageChops

# Grün-Dominanz <= _THRESHOLD bleibt voll deckend; ab _THRESHOLD+_SOFTNESS voll
# transparent; dazwischen linearer Übergang (weiche Kante).
_THRESHOLD = 40
_SOFTNESS = 60


def _alpha_from_dominance(value: int) -> int:
    if value <= _THRESHOLD:
        return 255
    if value >= _THRESHOLD + _SOFTNESS:
        return 0
    return round(255 * (1 - (value - _THRESHOLD) / _SOFTNESS))


def chroma_key_green(raw: bytes) -> bytes:
    """Entfernt den grünen Hintergrund aus rohen Bildbytes → transparentes PNG."""
    img = Image.open(io.BytesIO(raw)).convert("RGBA")
    r, g, b, a = img.split()

    rb_max = ImageChops.lighter(r, b)
    dominance = ImageChops.subtract(g, rb_max)  # max(0, g - max(r,b))

    keyed_alpha = dominance.point(_alpha_from_dominance)
    alpha = ImageChops.darker(keyed_alpha, a)  # bestehendes Alpha respektieren

    # Despill: Grün auf max(r,b) deckeln → Grünstich an den Kanten weg, Motiv bleibt
    g_clean = ImageChops.darker(g, rb_max)

    out = Image.merge("RGBA", (r, g_clean, b, alpha))
    buf = io.BytesIO()
    out.save(buf, "PNG")
    return buf.getvalue()
