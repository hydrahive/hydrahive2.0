"""Green-Screen Chroma-Key fürs generate_image-Tool.

Das Motiv kommt vom Bildmodell auf reinem Grün (OpenRouter kann keine echte
Transparenz). Der Key entfernt das Grün → echtes transparentes PNG. Neon-Farben
(Cyan/Gold/Weiß) müssen erhalten bleiben — nur grün-dominante Pixel fallen weg.
"""
from __future__ import annotations

import io

from PIL import Image


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _open(raw: bytes) -> Image.Image:
    return Image.open(io.BytesIO(raw)).convert("RGBA")


def test_pure_green_becomes_transparent():
    # Arrange: 4x4 voll reines Grün
    from hydrahive.tools._image_keying import chroma_key_green
    src = _png_bytes(Image.new("RGB", (4, 4), (0, 255, 0)))

    # Act
    out = _open(chroma_key_green(src))

    # Assert: alle Pixel transparent
    alphas = [out.getpixel((x, y))[3] for y in range(4) for x in range(4)]
    assert max(alphas) == 0


def test_cyan_subject_stays_opaque_and_intact():
    # Arrange: linke Hälfte Grün, rechte Hälfte Neon-Cyan
    from hydrahive.tools._image_keying import chroma_key_green
    img = Image.new("RGB", (4, 2), (0, 255, 0))
    for y in range(2):
        img.putpixel((2, y), (0, 200, 255))
        img.putpixel((3, y), (0, 200, 255))
    out = _open(chroma_key_green(_png_bytes(img)))

    # Assert: Grün weg, Cyan deckend + Farbe erhalten
    assert out.getpixel((0, 0))[3] == 0
    cyan = out.getpixel((3, 0))
    assert cyan[3] == 255
    assert cyan[0] < 40 and cyan[2] > 200  # r niedrig, b hoch → Cyan erhalten


def test_gold_and_white_stay_opaque():
    # Gold (255,200,0) und Weiß (255,255,255) sind nicht grün-dominant → bleiben
    from hydrahive.tools._image_keying import chroma_key_green
    img = Image.new("RGB", (2, 1), (255, 200, 0))
    img.putpixel((1, 0), (255, 255, 255))
    out = _open(chroma_key_green(_png_bytes(img)))
    assert out.getpixel((0, 0))[3] == 255  # Gold
    assert out.getpixel((1, 0))[3] == 255  # Weiß


def test_output_is_rgba_png():
    from hydrahive.tools._image_keying import chroma_key_green
    out = _open(chroma_key_green(_png_bytes(Image.new("RGB", (2, 2), (0, 255, 0)))))
    assert out.mode == "RGBA"
