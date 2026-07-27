"""E4: SwitchHttpVideoBackend — Adapter gegen den node-lokalen Switch-Wrapper.

Der Wrapper (Muskeln2) kapselt den VRAM-Konflikt Ollama <-> sd-server. HydraHive
spricht NUR den API-Vertrag aus docs/specs/local-video-backends.md:

  GET  /health            -> {"status":"ok","mode":"ollama|sd|switching"}
  GET  /models            -> [{"id","name","category":"image|video"}]
  POST /generate          -> {"job_id"}
  GET  /status/{job_id}   -> {"state":"pending|running|done|error","message?"}
  GET  /result/{job_id}   -> binaer ODER {"url"}
  POST /release           -> {"ok":true}   (optional)

Das interne sd-server-Schema kennt NUR der Wrapper — der Adapter darf davon
nichts wissen. Diese Tests laufen gegen einen Mock des Vertrags und blockieren
damit nicht auf Mias echten Wrapper.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

PROVIDER = {"id": "muskeln2", "type": "switch-http", "api_base": "http://muskeln2:9700"}


# --- Fake-HTTP gegen den Vertrag --------------------------------------------

class _Resp:
    def __init__(self, payload=None, status=200, content=b"", headers=None):
        self._payload = payload
        self.status_code = status
        self.content = content
        self.headers = headers or {}
        self.text = str(payload or "")

    def json(self):
        if self._payload is None:
            raise ValueError("keine JSON-Antwort")
        return self._payload


class _FakeClient:
    """Minimaler httpx.AsyncClient-Ersatz. `routes` mappt (method, path) -> _Resp."""

    def __init__(self, routes: dict, log: list | None = None, **kwargs):
        self._routes = routes
        self._log = log if log is not None else []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def _lookup(self, method: str, url: str, **kwargs):
        path = url.split("9700", 1)[1] if "9700" in url else url
        self._log.append((method, path, kwargs.get("json")))
        for (m, p), resp in self._routes.items():
            if m == method and p == path:
                return resp
        return _Resp({"error": "not found"}, status=404)

    async def get(self, url, **kwargs):
        return self._lookup("GET", url, **kwargs)

    async def post(self, url, **kwargs):
        return self._lookup("POST", url, **kwargs)


def _patch_http(monkeypatch, routes: dict, log: list | None = None):
    from hydrahive.llm.video_backends import _switch_http

    def factory(*a, **kw):
        return _FakeClient(routes, log)

    monkeypatch.setattr(_switch_http.httpx, "AsyncClient", factory)


# --- 1. Registry-Verdrahtung ------------------------------------------------

def test_registry_kennt_switch_http_typ():
    """E4 muss den Adapter in _ADAPTERS registrieren, sonst ist er unerreichbar."""
    from hydrahive.llm.video_backends._registry import resolve_backend

    cfg = {"media_backends": [PROVIDER]}
    backend, provider = resolve_backend("local:muskeln2/realvisxl-image", cfg)
    assert backend.type == "switch-http"
    assert provider["api_base"] == "http://muskeln2:9700"


def test_adapter_erfuellt_das_videobackend_protocol():
    from hydrahive.llm.video_backends._base import VideoBackend
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    assert isinstance(SwitchHttpVideoBackend(), VideoBackend)


# --- 2. list_models ---------------------------------------------------------

def test_list_models_praefixt_ids_mit_local_provider(monkeypatch):
    """Der Picker braucht 'local:<provider>/<model>', damit resolve_backend
    spaeter zurueckfindet. Der Wrapper liefert nur die nackte ID."""
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {
        ("GET", "/models"): _Resp([
            {"id": "realvisxl-image", "name": "RealVisXL", "category": "image"},
            {"id": "ltx-video", "name": "LTX Video", "category": "video"},
        ]),
    })
    models = asyncio.run(SwitchHttpVideoBackend().list_models(PROVIDER))
    assert [m.id for m in models] == ["local:muskeln2/realvisxl-image", "local:muskeln2/ltx-video"]
    assert [m.category for m in models] == ["image", "video"]
    assert models[0].name == "RealVisXL"


def test_list_models_ist_bei_fehler_leer_statt_zu_werfen(monkeypatch):
    """Ein nicht erreichbarer Node darf den Modell-Picker nicht sprengen."""
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {("GET", "/models"): _Resp(status=500)})
    assert asyncio.run(SwitchHttpVideoBackend().list_models(PROVIDER)) == []


def test_list_models_ohne_api_base_ist_leer():
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    assert asyncio.run(SwitchHttpVideoBackend().list_models({"id": "x", "type": "switch-http"})) == []


# --- 3. submit --------------------------------------------------------------

def test_submit_schickt_vertrags_payload_und_liefert_job_id(monkeypatch):
    from hydrahive.llm.video_backends._base import VideoParams
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    log: list = []
    _patch_http(monkeypatch, {("POST", "/generate"): _Resp({"job_id": "job-42"})}, log)

    params = VideoParams(prompt="ein fuchs", width=768, height=432, seed=123, frames=121)
    job = asyncio.run(SwitchHttpVideoBackend().submit(
        PROVIDER, "local:muskeln2/ltx-video", params))

    assert job.native_id == "job-42"
    _, path, payload = log[0]
    assert path == "/generate"
    # Modell-ID muss OHNE local:-Prefix rausgehen — der Wrapper kennt nur seine IDs
    assert payload["model"] == "ltx-video"
    assert payload["prompt"] == "ein fuchs"
    assert payload["width"] == 768 and payload["height"] == 432
    assert payload["seed"] == 123 and payload["frames"] == 121


def test_submit_ohne_job_id_wirft(monkeypatch):
    from hydrahive.llm.video_backends._base import VideoParams
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {("POST", "/generate"): _Resp({"ok": True})})
    with pytest.raises(RuntimeError, match="job_id"):
        asyncio.run(SwitchHttpVideoBackend().submit(
            PROVIDER, "local:muskeln2/x", VideoParams(prompt="p")))


def test_submit_bei_http_fehler_wirft(monkeypatch):
    from hydrahive.llm.video_backends._base import VideoParams
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {("POST", "/generate"): _Resp({"detail": "busy"}, status=503)})
    with pytest.raises(RuntimeError):
        asyncio.run(SwitchHttpVideoBackend().submit(
            PROVIDER, "local:muskeln2/x", VideoParams(prompt="p")))


# --- 4. poll ----------------------------------------------------------------

@pytest.mark.parametrize("state", ["pending", "running", "done", "error"])
def test_poll_reicht_alle_vertrags_states_durch(monkeypatch, state):
    from hydrahive.llm.video_backends._base import JobRef
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {("GET", "/status/j1"): _Resp({"state": state})})
    st = asyncio.run(SwitchHttpVideoBackend().poll(PROVIDER, JobRef(native_id="j1")))
    assert st.state == state


def test_poll_uebernimmt_message_fuer_die_ui(monkeypatch):
    """Der Switch kann Minuten dauern — die UI zeigt den Wrapper-Fortschritt."""
    from hydrahive.llm.video_backends._base import JobRef
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {
        ("GET", "/status/j1"): _Resp({"state": "running", "message": "schalte um …"}),
    })
    st = asyncio.run(SwitchHttpVideoBackend().poll(PROVIDER, JobRef(native_id="j1")))
    assert st.message == "schalte um …"


def test_poll_fuellt_error_bei_state_error(monkeypatch):
    from hydrahive.llm.video_backends._base import JobRef
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {
        ("GET", "/status/j1"): _Resp({"state": "error", "message": "OOM"}),
    })
    st = asyncio.run(SwitchHttpVideoBackend().poll(PROVIDER, JobRef(native_id="j1")))
    assert st.state == "error"
    assert "OOM" in (st.error or "")


def test_poll_bei_unbekanntem_state_ist_running_nicht_done(monkeypatch):
    """Fail-safe: ein unbekannter State darf NIE als 'done' gelten, sonst
    versucht der Caller ein Ergebnis zu holen, das es nicht gibt."""
    from hydrahive.llm.video_backends._base import JobRef
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {("GET", "/status/j1"): _Resp({"state": "wat"})})
    st = asyncio.run(SwitchHttpVideoBackend().poll(PROVIDER, JobRef(native_id="j1")))
    assert st.state == "running"


# --- 5. fetch_output (binaer ODER url — beide Vertragsvarianten) ------------

def test_fetch_output_speichert_binaerantwort(monkeypatch, tmp_path):
    from hydrahive.llm.video_backends._base import JobRef
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {
        ("GET", "/result/j1"): _Resp(content=b"\x00\x01MP4",
                                     headers={"content-type": "video/mp4"}),
    })
    out = asyncio.run(SwitchHttpVideoBackend().fetch_output(
        PROVIDER, JobRef(native_id="j1"), tmp_path))
    assert out.exists()
    assert out.read_bytes() == b"\x00\x01MP4"
    assert out.suffix == ".mp4"


def test_fetch_output_erkennt_bild_an_content_type(monkeypatch, tmp_path):
    from hydrahive.llm.video_backends._base import JobRef
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {
        ("GET", "/result/j1"): _Resp(content=b"\x89PNG",
                                     headers={"content-type": "image/png"}),
    })
    out = asyncio.run(SwitchHttpVideoBackend().fetch_output(
        PROVIDER, JobRef(native_id="j1"), tmp_path))
    assert out.suffix == ".png"


def test_fetch_output_folgt_url_variante(monkeypatch, tmp_path):
    """Zweite Vertragsvariante: {"url": ...} statt Bytes."""
    from hydrahive.llm.video_backends._base import JobRef
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {
        ("GET", "/result/j1"): _Resp({"url": "http://muskeln2:9700/files/out.mp4"},
                                     headers={"content-type": "application/json"}),
        ("GET", "/files/out.mp4"): _Resp(content=b"MP4DATA",
                                         headers={"content-type": "video/mp4"}),
    })
    out = asyncio.run(SwitchHttpVideoBackend().fetch_output(
        PROVIDER, JobRef(native_id="j1"), tmp_path))
    assert out.read_bytes() == b"MP4DATA"


def test_fetch_output_bei_leerem_ergebnis_wirft(monkeypatch, tmp_path):
    from hydrahive.llm.video_backends._base import JobRef
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {
        ("GET", "/result/j1"): _Resp(content=b"", headers={"content-type": "video/mp4"}),
    })
    with pytest.raises(RuntimeError):
        asyncio.run(SwitchHttpVideoBackend().fetch_output(
            PROVIDER, JobRef(native_id="j1"), tmp_path))


def test_fetch_output_legt_zielverzeichnis_an(monkeypatch, tmp_path):
    from hydrahive.llm.video_backends._base import JobRef
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    dest = tmp_path / "tief" / "verschachtelt"
    _patch_http(monkeypatch, {
        ("GET", "/result/j1"): _Resp(content=b"X", headers={"content-type": "video/mp4"}),
    })
    out = asyncio.run(SwitchHttpVideoBackend().fetch_output(
        PROVIDER, JobRef(native_id="j1"), dest))
    assert out.parent == dest


# --- 6. health / release ----------------------------------------------------

def test_health_liefert_status_und_modus(monkeypatch):
    """'Verbindung testen' in der GUI — zeigt auch den aktuellen Wrapper-Modus."""
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {("GET", "/health"): _Resp({"status": "ok", "mode": "ollama"})})
    ok, info = asyncio.run(SwitchHttpVideoBackend().health(PROVIDER))
    assert ok is True
    assert info["mode"] == "ollama"


def test_health_ist_false_wenn_node_weg(monkeypatch):
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {("GET", "/health"): _Resp(status=502)})
    ok, _ = asyncio.run(SwitchHttpVideoBackend().health(PROVIDER))
    assert ok is False


def test_release_ist_best_effort_und_wirft_nie(monkeypatch):
    """/release ist laut Vertrag optional — ein 404 darf nichts kaputtmachen."""
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {("POST", "/release"): _Resp(status=404)})
    assert asyncio.run(SwitchHttpVideoBackend().release(PROVIDER)) is False


def test_release_ok(monkeypatch):
    from hydrahive.llm.video_backends._switch_http import SwitchHttpVideoBackend

    _patch_http(monkeypatch, {("POST", "/release"): _Resp({"ok": True})})
    assert asyncio.run(SwitchHttpVideoBackend().release(PROVIDER)) is True


# --- 7. Isolation: kein sd-server-Wissen im Adapter -------------------------

def test_adapter_kennt_keine_sd_server_internals():
    """Vertragsgrenze: das sd-server-Payload-Schema kennt NUR der Wrapper.
    Taucht hier ein sd-Flag auf, ist die Abstraktion undicht."""
    src = Path(__file__).resolve().parents[1] / "src/hydrahive/llm/video_backends/_switch_http.py"
    text = src.read_text()
    for leak in ("--max-vram", "vae-tiling", "offload-to-cpu", "sd-server", ":8080"):
        assert leak not in text, f"sd-server-Interna im Adapter geleakt: {leak}"
