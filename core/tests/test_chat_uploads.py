"""Chat-Anhänge: Limits, Streaming und session-korrekter Workspace."""
from __future__ import annotations

import asyncio
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from hydrahive.api.routes import _files
from hydrahive.api.routes import _session_msg_helpers as helpers
from hydrahive.api.routes import sessions_messages
from hydrahive.api.middleware.upload_limit import ChatUploadLimitMiddleware


def _run(coro):
    return asyncio.run(coro)


def _upload(
    data: bytes,
    name: str = "sample.apk",
    content_type: str = "application/octet-stream",
    *,
    declared_size: int | None = None,
) -> UploadFile:
    return UploadFile(
        BytesIO(data),
        size=len(data) if declared_size is None else declared_size,
        filename=name,
        headers=Headers({"content-type": content_type}),
    )


class _TrackingBytesIO(BytesIO):
    def __init__(self, data: bytes):
        super().__init__(data)
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return super().read(size)


def test_binary_upload_is_streamed_to_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(_files, "MAX_FILE_BYTES", 8, raising=False)
    monkeypatch.setattr(_files, "STREAM_CHUNK_BYTES", 3, raising=False)
    source = _TrackingBytesIO(b"12345678")
    upload = UploadFile(
        source,
        size=8,
        filename="sample.apk",
        headers=Headers({"content-type": "application/vnd.android.package-archive"}),
    )

    blocks = _run(_files.process_upload(upload, tmp_path))

    assert (tmp_path / "sample.apk").read_bytes() == b"12345678"
    assert blocks == [{"type": "text", "text": f"[Datei hochgeladen: {tmp_path / 'sample.apk'}]"}]
    assert -1 not in source.read_sizes
    assert max(source.read_sizes) <= 3


def test_binary_upload_over_limit_is_rejected_and_partial_file_removed(tmp_path, monkeypatch):
    monkeypatch.setattr(_files, "MAX_FILE_BYTES", 8, raising=False)
    monkeypatch.setattr(_files, "STREAM_CHUNK_BYTES", 3, raising=False)
    upload = _upload(b"123456789", declared_size=8)

    with pytest.raises(_files.UploadTooLarge):
        _run(_files.process_upload(upload, tmp_path))

    assert not (tmp_path / "sample.apk").exists()
    assert not list(tmp_path.glob("*.upload-*"))


def test_validate_upload_sizes_rejects_single_file_over_limit(monkeypatch):
    monkeypatch.setattr(_files, "MAX_FILE_BYTES", 8, raising=False)
    monkeypatch.setattr(_files, "MAX_MESSAGE_UPLOAD_BYTES", 12, raising=False)

    with pytest.raises(_files.UploadTooLarge) as exc:
        _files.validate_upload_sizes([_upload(b"123456789")])

    assert exc.value.scope == "file"


def test_validate_upload_sizes_rejects_total_over_limit(monkeypatch):
    monkeypatch.setattr(_files, "MAX_FILE_BYTES", 8, raising=False)
    monkeypatch.setattr(_files, "MAX_MESSAGE_UPLOAD_BYTES", 12, raising=False)

    with pytest.raises(_files.UploadTooLarge) as exc:
        _files.validate_upload_sizes([_upload(b"1234567", "a.apk"), _upload(b"1234567", "b.exe")])

    assert exc.value.scope == "message"


def test_validate_upload_sizes_rejects_unknown_size():
    upload = UploadFile(BytesIO(b"abc"), size=None, filename="unknown.bin")

    with pytest.raises(_files.UploadSizeUnknown):
        _files.validate_upload_sizes([upload])


def test_validate_upload_sizes_rejects_more_than_five_files():
    uploads = [_upload(b"x", f"{index}.bin") for index in range(6)]

    with pytest.raises(_files.UploadTooManyFiles):
        _files.validate_upload_sizes(uploads)


def test_small_text_upload_stays_inline():
    upload = _upload(b"hello", "notes.txt", "text/plain")

    blocks = _run(_files.process_upload(upload, None))

    assert blocks == [{"type": "text", "text": "[notes.txt]\nhello"}]


def test_small_image_upload_stays_inline_and_is_saved(tmp_path):
    upload = _upload(b"fake-png", "image.png", "image/png")

    blocks = _run(_files.process_upload(upload, tmp_path))

    assert blocks[0]["type"] == "image"
    assert blocks[0]["source"]["media_type"] == "image/png"
    assert blocks[1] == {"type": "text", "text": f"[Bild gespeichert: {tmp_path / 'image.png'}]"}
    assert (tmp_path / "image.png").read_bytes() == b"fake-png"


def test_path_traversal_filename_is_rejected(tmp_path):
    upload = _upload(b"payload", "../escape.exe")

    blocks = _run(_files.process_upload(upload, tmp_path))

    assert blocks == [{"type": "text", "text": "[Anhang abgelehnt: ungültiger Dateiname]"}]
    assert not (tmp_path.parent / "escape.exe").exists()


def test_build_user_content_uses_resolved_project_workspace(tmp_path, monkeypatch):
    session = SimpleNamespace(agent_id="agent-1", project_id="project-1")
    agent = {"id": "agent-1", "name": "Agent"}
    monkeypatch.setattr(helpers.agent_config, "get", lambda _agent_id: agent)
    monkeypatch.setattr(
        helpers,
        "resolve_run_context",
        lambda actual_session, actual_agent: (tmp_path, "project-1"),
        raising=False,
    )
    upload = _upload(b"apk-data", "security-check.apk")

    blocks = _run(helpers.build_user_content(session, "Bitte prüfen", [upload]))

    saved = list((tmp_path / ".hydrahive" / "uploads").glob("*/security-check.apk"))
    assert len(saved) == 1
    assert saved[0].read_bytes() == b"apk-data"
    assert blocks[-1] == {"type": "text", "text": "Bitte prüfen"}


def test_build_user_content_does_not_overwrite_existing_project_file(tmp_path, monkeypatch):
    existing = tmp_path / "security-check.apk"
    existing.write_bytes(b"project-data")
    session = SimpleNamespace(agent_id="agent-1", project_id="project-1")
    monkeypatch.setattr(helpers.agent_config, "get", lambda _agent_id: {"id": "agent-1"})
    monkeypatch.setattr(helpers, "resolve_run_context", lambda _s, _a: (tmp_path, "project-1"))

    _run(helpers.build_user_content(session, "check", [_upload(b"upload-data", existing.name)]))

    assert existing.read_bytes() == b"project-data"
    saved = list((tmp_path / ".hydrahive" / "uploads").glob("*/security-check.apk"))
    assert len(saved) == 1
    assert saved[0].read_bytes() == b"upload-data"


def test_build_user_content_keeps_duplicate_names_separate(tmp_path, monkeypatch):
    session = SimpleNamespace(agent_id="agent-1", project_id="project-1")
    monkeypatch.setattr(helpers.agent_config, "get", lambda _agent_id: {"id": "agent-1"})
    monkeypatch.setattr(helpers, "resolve_run_context", lambda _s, _a: (tmp_path, "project-1"))

    _run(helpers.build_user_content(
        session, "check", [_upload(b"first", "same.apk"), _upload(b"second", "same.apk")],
    ))

    batch_dirs = list((tmp_path / ".hydrahive" / "uploads").iterdir())
    assert len(batch_dirs) == 1
    assert sorted(path.read_bytes() for path in batch_dirs[0].iterdir()) == [b"first", b"second"]


def test_build_user_content_cleans_batch_when_later_file_fails(tmp_path, monkeypatch):
    session = SimpleNamespace(agent_id="agent-1", project_id="project-1")
    monkeypatch.setattr(helpers.agent_config, "get", lambda _agent_id: {"id": "agent-1"})
    monkeypatch.setattr(helpers, "resolve_run_context", lambda _s, _a: (tmp_path, "project-1"))
    monkeypatch.setattr(_files, "MAX_FILE_BYTES", 8)
    monkeypatch.setattr(_files, "MAX_MESSAGE_UPLOAD_BYTES", 12)
    first = _upload(b"ok", "first.apk")
    second = _upload(b"123456789", "second.apk", declared_size=8)

    with pytest.raises(HTTPException):
        _run(helpers.build_user_content(session, "check", [first, second]))

    uploads = tmp_path / ".hydrahive" / "uploads"
    assert not uploads.exists() or not list(uploads.iterdir())
    assert not list(tmp_path.rglob("first.apk"))


def test_build_user_content_uses_agent_workspace_without_project(tmp_path, monkeypatch):
    session = SimpleNamespace(agent_id="agent-1", project_id=None)
    monkeypatch.setattr(helpers.agent_config, "get", lambda _agent_id: {"id": "agent-1"})
    monkeypatch.setattr(helpers, "resolve_run_context", lambda _s, _a: (tmp_path, None))

    _run(helpers.build_user_content(session, "check", [_upload(b"data", "sample.exe")]))

    saved = list((tmp_path / ".hydrahive" / "uploads").glob("*/sample.exe"))
    assert len(saved) == 1


def test_dot_filename_is_rejected(tmp_path):
    blocks = _run(_files.process_upload(_upload(b"payload", "."), tmp_path))

    assert blocks == [{"type": "text", "text": "[Anhang abgelehnt: ungültiger Dateiname]"}]


def test_build_user_content_maps_file_limit_to_http_413(tmp_path, monkeypatch):
    session = SimpleNamespace(agent_id="agent-1", project_id="project-1")
    monkeypatch.setattr(helpers.agent_config, "get", lambda _agent_id: {"id": "agent-1"})
    monkeypatch.setattr(
        helpers,
        "resolve_run_context",
        lambda _session, _agent: (tmp_path, "project-1"),
        raising=False,
    )
    monkeypatch.setattr(_files, "MAX_FILE_BYTES", 8, raising=False)
    monkeypatch.setattr(_files, "MAX_MESSAGE_UPLOAD_BYTES", 12, raising=False)

    with pytest.raises(Exception) as exc:
        _run(helpers.build_user_content(session, "Bitte prüfen", [_upload(b"123456789")]))

    assert getattr(exc.value, "status_code", None) == 413
    assert exc.value.detail["code"] == "upload_file_too_large"


def test_resend_validates_upload_before_deleting_history(monkeypatch):
    session = SimpleNamespace(id="session-1", agent_id="agent-1")
    target = SimpleNamespace(id="message-1", session_id="session-1", role="user")
    deleted: list[tuple[str, str]] = []
    monkeypatch.setattr(sessions_messages.sessions_db, "get", lambda _sid: session)
    monkeypatch.setattr(sessions_messages, "check_owner", lambda *_args: None)
    monkeypatch.setattr(sessions_messages.messages_db, "get", lambda _mid: target)
    monkeypatch.setattr(
        sessions_messages.messages_db,
        "delete_from",
        lambda sid, mid: deleted.append((sid, mid)),
    )

    async def reject_upload(*_args, **_kwargs):
        raise HTTPException(status_code=413, detail={"code": "upload_file_too_large"})

    monkeypatch.setattr(sessions_messages, "build_user_content", reject_upload)

    with pytest.raises(HTTPException):
        _run(sessions_messages.resend_message(
            session_id="session-1",
            message_id="message-1",
            auth=("user", "user"),
            text="replacement",
            files=[_upload(b"payload")],
        ))

    assert deleted == []


def test_nginx_limits_chat_message_bodies_before_fastapi():
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    linux = (root / "installer/modules/60-nginx.sh").read_text()
    mac = (root / "installer/modules-mac/60-nginx.sh").read_text()
    updater = (root / "installer/update.sh").read_text()

    for config in (linux, mac):
        assert "chat-upload-limit" in config
        assert "client_max_body_size 205M" in config
        assert "upload_request_too_large" in config
    assert 'grep -q "chat-upload-limit"' in updater


def test_chat_upload_middleware_rejects_large_content_length_before_app():
    called = False
    sent: list[dict] = []

    async def app(_scope, _receive, _send):
        nonlocal called
        called = True

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    async def run():
        middleware = ChatUploadLimitMiddleware(app, max_bytes=8)
        await middleware(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/sessions/session-1/messages",
                "headers": [(b"content-length", b"9")],
            },
            receive,
            send,
        )

    _run(run())

    assert called is False
    assert sent[0]["status"] == 413
    assert b"upload_request_too_large" in sent[1]["body"]


def test_chat_upload_middleware_counts_chunked_body():
    sent: list[dict] = []
    chunks = iter([
        {"type": "http.request", "body": b"12345", "more_body": True},
        {"type": "http.request", "body": b"6789", "more_body": False},
    ])

    async def app(_scope, receive, _send):
        while (await receive()).get("more_body"):
            pass

    async def receive():
        return next(chunks)

    async def send(message):
        sent.append(message)

    async def run():
        middleware = ChatUploadLimitMiddleware(app, max_bytes=8)
        await middleware(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/sessions/session-1/messages/message-1/resend",
                "headers": [],
            },
            receive,
            send,
        )

    _run(run())

    assert sent[0]["status"] == 413
    assert b"upload_request_too_large" in sent[1]["body"]
