"""Nachtrag 19.10.2026 (docs/specs/local-video-backends.md): mehrere Vorlagen für ComfyUI-Bild-Workflows.

- VideoParams.references → Platzhalter reference_1..3 (LoadImage.inputs.image), Reihenfolge bleibt.
- Fehlt Vorlage N, entfernt der Adapter den Eingang reference_links.reference_N (Graph läuft ohne sie).
- Überzählige Vorlagen werden ignoriert, image_url bleibt wie bisher.
- Der mitgelieferte Workflow flux2-klein-image.json ist so verdrahtet.

Kein echter Netzverkehr: httpx.AsyncClient wird ersetzt.
"""
from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WF = REPO / "installer" / "media-workflows" / "flux2-klein-image.json"


def _uri(text: str) -> str:
    return "data:image/png;base64," + base64.b64encode(text.encode()).decode()


class _Resp:
    def __init__(self, payload=None, status=200):
        self._p, self.status_code, self.text, self.content = payload, status, "", b""

    def json(self):
        return self._p


class _Client:
    uploads: list[bytes] = []
    graph: dict = {}

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, files=None, **kw):
        if url.endswith("/upload/image"):
            _Client.uploads.append(files["image"][1])
            return _Resp({"name": f"up-{len(_Client.uploads)}.png", "subfolder": "", "type": "input"})
        _Client.graph = json["prompt"]
        return _Resp({"prompt_id": "pid"})


def _graph() -> dict:
    return {
        "t": {"class_type": "CLIPTextEncode", "inputs": {"text": "x"}},
        "i1": {"class_type": "LoadImage", "inputs": {"image": "a.png"}},
        "i2": {"class_type": "LoadImage", "inputs": {"image": "b.png"}},
        "i3": {"class_type": "LoadImage", "inputs": {"image": "c.png"}},
        "r1": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["t", 0], "latent": ["e1", 0]}},
        "r2": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["r1", 0], "latent": ["e2", 0]}},
        "r3": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["r2", 0], "latent": ["e3", 0]}},
    }


def _provider(links: bool = True) -> dict:
    wf = {"id": "edit", "category": "image", "output_node": "SaveImage", "graph": _graph(),
          "placeholders": {"prompt": "t.inputs.text", "reference_1": "i1.inputs.image",
                           "reference_2": "i2.inputs.image", "reference_3": "i3.inputs.image"}}
    if links:
        wf["reference_links"] = {"reference_1": "r1.inputs.latent", "reference_2": "r2.inputs.latent",
                                 "reference_3": "r3.inputs.latent"}
    return {"id": "wks", "type": "comfyui", "api_base": "http://wks:8189", "workflows": [wf]}


def _submit(monkeypatch, provider: dict, refs: list[str], **kw) -> dict:
    from hydrahive.llm.video_backends import _comfyui
    from hydrahive.llm.video_backends._base import VideoParams
    _Client.uploads, _Client.graph = [], {}
    monkeypatch.setattr(_comfyui.httpx, "AsyncClient", _Client)
    asyncio.run(_comfyui.ComfyUIVideoBackend().submit(
        provider, "local:wks/edit", VideoParams(prompt="Hydra im Wald", references=refs, **kw)))
    return _Client.graph


def test_params_have_empty_references_by_default() -> None:
    from hydrahive.llm.video_backends._base import VideoParams
    assert VideoParams(prompt="x").references == []


def test_all_three_references_uploaded_in_order(monkeypatch) -> None:
    g = _submit(monkeypatch, _provider(), [_uri("A"), _uri("B"), _uri("C")])
    assert _Client.uploads == [b"A", b"B", b"C"]
    assert [g["i1"]["inputs"]["image"], g["i2"]["inputs"]["image"], g["i3"]["inputs"]["image"]] == \
        ["up-1.png", "up-2.png", "up-3.png"]
    assert all("latent" in g[r]["inputs"] for r in ("r1", "r2", "r3"))
    assert g["t"]["inputs"]["text"] == "Hydra im Wald"


def test_missing_references_are_unlinked(monkeypatch) -> None:
    g = _submit(monkeypatch, _provider(), [_uri("A")])
    assert _Client.uploads == [b"A"]
    assert g["i1"]["inputs"]["image"] == "up-1.png" and "latent" in g["r1"]["inputs"]
    assert "latent" not in g["r2"]["inputs"] and "latent" not in g["r3"]["inputs"]
    assert g["r2"]["inputs"]["conditioning"] == ["r1", 0]                       # Rest der Kette bleibt


def test_no_references_unlinks_all(monkeypatch) -> None:
    g = _submit(monkeypatch, _provider(), [])
    assert _Client.uploads == []
    assert not any("latent" in g[r]["inputs"] for r in ("r1", "r2", "r3"))


def test_without_links_graph_stays_as_is(monkeypatch) -> None:
    g = _submit(monkeypatch, _provider(links=False), [_uri("A")])
    assert "latent" in g["r2"]["inputs"] and g["i2"]["inputs"]["image"] == "b.png"


def test_extra_references_are_ignored(monkeypatch) -> None:
    _submit(monkeypatch, _provider(), [_uri(c) for c in "ABCDE"])
    assert _Client.uploads == [b"A", b"B", b"C"]


def test_image_url_still_works_next_to_references(monkeypatch) -> None:
    p = _provider()
    p["workflows"][0]["graph"]["s"] = {"class_type": "LoadImage", "inputs": {"image": "s.png"}}
    p["workflows"][0]["placeholders"]["image_url"] = "s.inputs.image"
    g = _submit(monkeypatch, p, [_uri("A")], image_url=_uri("S"))
    assert _Client.uploads == [b"S", b"A"]
    assert g["s"]["inputs"]["image"] == "up-1.png" and g["i1"]["inputs"]["image"] == "up-2.png"


def test_bad_link_address_is_skipped(monkeypatch) -> None:
    p = _provider()
    p["workflows"][0]["reference_links"]["reference_2"] = "kaputt"
    g = _submit(monkeypatch, p, [_uri("A")])
    assert "latent" in g["r2"]["inputs"] and "latent" not in g["r3"]["inputs"]


def test_generate_image_local_passes_reference_as_references(monkeypatch, tmp_path) -> None:
    from hydrahive.tools import generate_image as gi
    seen = {}

    async def fake_run(backend, provider, model, params, dest, timeout):
        seen["params"] = params
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "x.png").write_bytes(b"png")
        return dest / "x.png"

    monkeypatch.setattr(gi, "resolve_local_workflow", lambda m, c, k: (object(), {}))
    monkeypatch.setattr(gi, "run_local_media", fake_run)
    monkeypatch.setattr(gi, "image_to_content_block", lambda p, workspace: {"image_url": {"url": _uri("R")}})
    ctx = type("C", (), {"workspace": tmp_path})()
    asyncio.run(gi._execute_local("local:wks/edit", {"prompt": "x", "reference_image_path": "r.png"}, ctx))
    assert seen["params"].image_url == _uri("R") and seen["params"].references == [_uri("R")]


# --- mitgelieferter Workflow ---------------------------------------------------

def test_shipped_flux2_workflow_is_wired() -> None:
    wf = json.loads(WF.read_text())
    assert wf["category"] == "image" and wf["output_node"] == "SaveImage"
    g, ph, links = wf["graph"], wf["placeholders"], wf["reference_links"]
    for key in ("prompt", "seed", "width", "height", "reference_1", "reference_2", "reference_3"):
        node, part, field = ph[key].split(".")
        assert part == "inputs" and field in g[node]["inputs"], key
    for n in (1, 2, 3):
        node, _, field = ph[f"reference_{n}"].split(".")
        assert g[node]["class_type"] == "LoadImage"
        lnode, _, lfield = links[f"reference_{n}"].split(".")
        assert g[lnode]["class_type"] == "ReferenceLatent" and isinstance(g[lnode]["inputs"][lfield], list)
    assert {g[n]["class_type"] for n in g} >= {"UNETLoader", "CLIPLoader", "VAELoader", "SamplerCustomAdvanced", "SaveImage"}
    loaders = {g[n]["class_type"]: g[n]["inputs"] for n in g}
    assert loaders["UNETLoader"]["unet_name"] == "flux-2-klein-4b.safetensors"
    assert loaders["CLIPLoader"] == {"clip_name": "qwen_3_4b.safetensors", "type": "flux2"}


def test_shipped_flux2_workflow_runs_without_references(monkeypatch) -> None:
    wf = json.loads(WF.read_text())
    p = {"id": "wks", "type": "comfyui", "api_base": "http://wks:8189", "workflows": [{**wf, "id": "edit"}]}
    g = _submit(monkeypatch, p, [], seed=7, width=1344, height=768)
    for n in (1, 2, 3):
        lnode, _, lfield = wf["reference_links"][f"reference_{n}"].split(".")
        assert lfield not in g[lnode]["inputs"]
    seed_node, _, seed_field = wf["placeholders"]["seed"].split(".")
    assert g[seed_node]["inputs"][seed_field] == 7
