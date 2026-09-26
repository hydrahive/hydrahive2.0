"""E2: ComfyUIVideoBackend — submit/poll/fetch + Platzhalter-Ersetzung.

Gegen einen Mock-ComfyUI (httpx.AsyncClient gepatcht). Sichert:
- Platzhalter werden korrekt in den Graph gesetzt ("6.inputs.text" etc.)
- submit ruft POST /prompt und liefert prompt_id als JobRef
- poll mappt history-Zustände (running/done/error)
- Output-Dateien werden aus outputs.images/gifs gesammelt
- Resolver mappt local:<comfy>/<wf> auf den comfyui-Adapter

Importe lazy, httpx gemockt — kein echter Netzverkehr.
"""
from __future__ import annotations

import asyncio


# --- Platzhalter-Ersetzung (reine Logik) -------------------------------------

def test_apply_placeholders_sets_graph_fields():
    from hydrahive.llm.video_backends._comfyui import _apply_placeholders
    from hydrahive.llm.video_backends._base import VideoParams

    graph = {
        "3": {"class_type": "KSampler", "inputs": {"seed": 0, "steps": 20}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "OLD"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512}},
    }
    placeholders = {
        "prompt": "6.inputs.text",
        "seed": "3.inputs.seed",
        "width": "5.inputs.width",
        "height": "5.inputs.height",
    }
    params = VideoParams(prompt="a red fox", seed=42, width=768, height=432)
    out = _apply_placeholders(graph, placeholders, params)

    assert out["6"]["inputs"]["text"] == "a red fox"
    assert out["3"]["inputs"]["seed"] == 42
    assert out["5"]["inputs"]["width"] == 768
    assert out["5"]["inputs"]["height"] == 432
    # Original unverändert (deepcopy)
    assert graph["6"]["inputs"]["text"] == "OLD"


def test_apply_placeholders_skips_missing():
    from hydrahive.llm.video_backends._comfyui import _apply_placeholders
    from hydrahive.llm.video_backends._base import VideoParams
    graph = {"6": {"class_type": "X", "inputs": {"text": "OLD"}}}
    # seed adressiert eine nicht existierende Node → wird still übersprungen
    out = _apply_placeholders(graph, {"prompt": "6.inputs.text", "seed": "99.inputs.seed"},
                              VideoParams(prompt="hi", seed=7))
    assert out["6"]["inputs"]["text"] == "hi"


# --- list_models aus workflows ------------------------------------------------

def test_list_models_from_workflows():
    from hydrahive.llm.video_backends._comfyui import ComfyUIVideoBackend
    provider = {
        "id": "muskeln1", "type": "comfyui", "api_base": "http://muskeln1:8189",
        "workflows": [
            {"id": "ltx-t2v", "label": "LTX T2V", "category": "video",
             "durations": [5, 10], "graph": {"1": {}}},
            {"id": "sdxl", "label": "SDXL Bild", "category": "image", "graph": {"1": {}}},
        ],
    }
    models = asyncio.run(ComfyUIVideoBackend().list_models(provider))
    by_id = {m.id: m for m in models}
    assert "local:muskeln1/ltx-t2v" in by_id
    assert by_id["local:muskeln1/ltx-t2v"].category == "video"
    assert by_id["local:muskeln1/sdxl"].category == "image"


# --- Mock-httpx ---------------------------------------------------------------

class _Resp:
    def __init__(self, payload=None, content=b"", status=200):
        self._p = payload
        self.content = content
        self.status_code = status
        self.text = ""

    def json(self):
        return self._p


class _MockClient:
    """Simuliert POST /prompt, GET /history/{id}, GET /view."""
    scenario = {}  # gefüllt vom Test

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, **kw):
        if url.endswith("/upload/image"):
            label = "end" if "end" in str(kw.get("files")) else "start"
            return _Resp({"name": f"hydrahive-{label}.png", "subfolder": "", "type": "input"})
        _MockClient.scenario["submitted_graph"] = json["prompt"]
        return _Resp({"prompt_id": "pid-1"})

    async def get(self, url, params=None, **kw):
        if "/history/" in url:
            return _Resp(_MockClient.scenario["history"])
        if "/view" in url:
            return _Resp(content=b"FAKEWEBPDATA")
        return _Resp({}, status=404)


def test_submit_posts_prompt_and_returns_jobref(monkeypatch):
    from hydrahive.llm.video_backends import _comfyui
    from hydrahive.llm.video_backends._comfyui import ComfyUIVideoBackend
    from hydrahive.llm.video_backends._base import VideoParams

    _MockClient.scenario = {}
    monkeypatch.setattr(_comfyui.httpx, "AsyncClient", _MockClient)

    provider = {
        "id": "muskeln1", "type": "comfyui", "api_base": "http://muskeln1:8189",
        "workflows": [{"id": "ltx-t2v", "category": "video",
                       "output_node": "SaveAnimatedWEBP",
                       "graph": {"6": {"class_type": "CLIPTextEncode", "inputs": {"text": "x"}}},
                       "placeholders": {"prompt": "6.inputs.text"}}],
    }
    ref = asyncio.run(ComfyUIVideoBackend().submit(
        provider, "local:muskeln1/ltx-t2v", VideoParams(prompt="a cat")))
    assert ref.native_id == "pid-1"
    assert ref.extra["category"] == "video"
    # Prompt wurde in den gesendeten Graph gesetzt
    assert _MockClient.scenario["submitted_graph"]["6"]["inputs"]["text"] == "a cat"


def test_submit_uploads_start_and_end_images(monkeypatch):
    from hydrahive.llm.video_backends import _comfyui
    from hydrahive.llm.video_backends._comfyui import ComfyUIVideoBackend
    from hydrahive.llm.video_backends._base import VideoParams

    _MockClient.scenario = {}
    monkeypatch.setattr(_comfyui.httpx, "AsyncClient", _MockClient)
    provider = {
        "id": "wks", "type": "comfyui", "api_base": "http://wks:8188",
        "workflows": [{
            "id": "flf2v", "category": "video", "output_node": "SaveVideo",
            "graph": {
                "5": {"class_type": "WanFirstLastFrameToVideo", "inputs": {
                    "start_image": "old-start", "end_image": "old-end",
                }},
            },
            "placeholders": {
                "image_url": "5.inputs.start_image",
                "end_image_url": "5.inputs.end_image",
            },
        }],
    }
    ref = asyncio.run(ComfyUIVideoBackend().submit(
        provider, "local:wks/flf2v", VideoParams(
            prompt="transition",
            image_url="data:image/png;base64,QUJD",
            end_image_url="data:image/png;base64,REVG",
        )))
    assert ref.native_id == "pid-1"
    graph = _MockClient.scenario["submitted_graph"]
    assert graph["5"]["inputs"]["start_image"] == "hydrahive-start.png"
    assert graph["5"]["inputs"]["end_image"] == "hydrahive-end.png"


def test_poll_running_then_done(monkeypatch):
    from hydrahive.llm.video_backends import _comfyui
    from hydrahive.llm.video_backends._comfyui import ComfyUIVideoBackend
    from hydrahive.llm.video_backends._base import JobRef

    monkeypatch.setattr(_comfyui.httpx, "AsyncClient", _MockClient)
    ref = JobRef(native_id="pid-1", extra={"category": "video"})

    # noch nicht in History → running
    _MockClient.scenario = {"history": {}}
    st = asyncio.run(ComfyUIVideoBackend().poll({"api_base": "http://m:8189"}, ref))
    assert st.state == "running"

    # fertig mit output → done + files gesammelt
    _MockClient.scenario = {"history": {"pid-1": {
        "status": {"completed": True},
        "outputs": {"9": {"gifs": [{"filename": "out.webp", "subfolder": "", "type": "output"}]}},
    }}}
    st = asyncio.run(ComfyUIVideoBackend().poll({"api_base": "http://m:8189"}, ref))
    assert st.state == "done"
    assert st.raw["files"][0]["filename"] == "out.webp"


def test_collect_output_files_supports_native_video():
    from hydrahive.llm.video_backends._comfyui import _collect_output_files

    files = _collect_output_files({"11": {"videos": [
        {"filename": "hydrahive/video.mp4", "subfolder": "", "type": "output"}
    ]}})
    assert files[0]["filename"] == "hydrahive/video.mp4"


def test_poll_error(monkeypatch):
    from hydrahive.llm.video_backends import _comfyui
    from hydrahive.llm.video_backends._comfyui import ComfyUIVideoBackend
    from hydrahive.llm.video_backends._base import JobRef

    monkeypatch.setattr(_comfyui.httpx, "AsyncClient", _MockClient)
    _MockClient.scenario = {"history": {"pid-1": {
        "status": {"status_str": "error", "messages": ["OOM"]}, "outputs": {}}}}
    st = asyncio.run(ComfyUIVideoBackend().poll(
        {"api_base": "http://m:8189"}, JobRef(native_id="pid-1")))
    assert st.state == "error"
    assert "OOM" in (st.error or "")


# --- Resolver mappt comfyui --------------------------------------------------

def test_resolver_maps_comfyui():
    from hydrahive.llm.video_backends import resolve_backend
    cfg = {"media_backends": [{"id": "muskeln1", "type": "comfyui",
                               "api_base": "http://m:8189"}]}
    backend, provider = resolve_backend("local:muskeln1/ltx-t2v", cfg)
    assert backend.type == "comfyui"
    assert provider["api_base"] == "http://m:8189"
