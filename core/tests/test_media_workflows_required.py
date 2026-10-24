"""Task ef4e0e10 (docs/specs/comfyui-workflows-pflichtfelder.md): Jeder Knoten der
mitgelieferten ComfyUI-Abläufe hat alle Pflichtfelder seines Knotentyps.

Die Pflichtfelder stammen aus /object_info von ComfyUI 0.21.1 (fixtures/
comfyui_required_inputs.json). Vorher fehlte bei CLIPVisionEncode „crop“ →
ComfyUI lehnte wan21-flf2v.json mit 400 required_input_missing ab."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((REPO / "installer" / "media-workflows").glob("*.json"))
REQUIRED = json.loads((Path(__file__).parent / "fixtures" / "comfyui_required_inputs.json").read_text())["nodes"]


def _nodes(path: Path):
    graph = json.loads(path.read_text())["graph"]
    return [(nid, n) for nid, n in graph.items() if isinstance(n, dict) and "class_type" in n]


def test_es_gibt_mitgelieferte_ablaeufe() -> None:
    assert len(WORKFLOWS) >= 4


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_knotentypen_bekannt(path: Path) -> None:
    unknown = sorted({n["class_type"] for _, n in _nodes(path)} - REQUIRED.keys())
    assert unknown == [], f"Pflichtfelder für neue Knotentypen in die Fixture aufnehmen: {unknown}"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_pflichtfelder_vollstaendig(path: Path) -> None:
    lack = [
        f"{nid} {n['class_type']}: {f}"
        for nid, n in _nodes(path)
        for f in REQUIRED.get(n["class_type"], [])
        if f not in n.get("inputs", {})
    ]
    assert lack == []


def test_clip_vision_ohne_zuschnitt() -> None:
    graph = json.loads((REPO / "installer" / "media-workflows" / "wan21-flf2v.json").read_text())["graph"]
    crops = [n["inputs"].get("crop") for n in graph.values()
             if isinstance(n, dict) and n.get("class_type") == "CLIPVisionEncode"]
    assert crops == ["none", "none"]
