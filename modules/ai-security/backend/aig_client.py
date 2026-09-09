"""Kleiner AIG-HTTP-Client mit Timeout- und Response-Limits."""
from __future__ import annotations

import re
from typing import Any

import httpx

from hydrahive.settings import settings


class AigError(RuntimeError):
    """Stabil klassifizierter Fehler an der AIG-Grenze."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,200}$")


def _check_content_length(response: httpx.Response, maximum: int) -> None:
    raw = response.headers.get("content-length", "0") or "0"
    try:
        size = int(raw)
    except ValueError as exc:
        raise AigError("aig_invalid_content_length") from exc
    if size < 0 or size > maximum:
        raise AigError("aig_response_too_large")


class AigClient:
    def __init__(self) -> None:
        self.base_url = settings.ai_security_aig_url
        self.timeout = settings.ai_security_http_timeout
        self.max_bytes = settings.ai_security_max_result_bytes

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if not self.base_url:
            raise AigError("aig_not_configured")
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                follow_redirects=False,
            ) as client:
                async with client.stream(method, path, **kwargs) as response:
                    _check_content_length(response, self.max_bytes)
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > self.max_bytes:
                            raise AigError("aig_response_too_large")
                        chunks.append(chunk)
                    body = b"".join(chunks)
        except httpx.TimeoutException as exc:
            raise AigError("aig_timeout") from exc
        except httpx.HTTPError as exc:
            raise AigError("aig_unreachable") from exc
        if len(body) > self.max_bytes:
            raise AigError("aig_response_too_large")
        if response.status_code >= 400:
            raise AigError("aig_http_error")
        try:
            payload = response.json()
        except ValueError as exc:
            raise AigError("aig_invalid_json") from exc
        if not isinstance(payload, dict):
            raise AigError("aig_invalid_response")
        if payload.get("status") != 0:
            raise AigError("aig_operation_failed")
        data = payload.get("data")
        return data if isinstance(data, dict) else {}

    async def health(self) -> None:
        if not self.base_url:
            raise AigError("aig_not_configured")
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                follow_redirects=False,
            ) as client:
                async with client.stream("GET", "/") as response:
                    _check_content_length(response, self.max_bytes)
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > self.max_bytes:
                            raise AigError("aig_response_too_large")
        except httpx.TimeoutException as exc:
            raise AigError("aig_timeout") from exc
        except httpx.HTTPError as exc:
            raise AigError("aig_unreachable") from exc
        if response.status_code >= 400:
            raise AigError("aig_http_error")

    async def create_infra_scan(self, target_url: str) -> str:
        data = await self._request(
            "POST",
            "/api/v1/app/taskapi/tasks",
            json={
                "type": "ai_infra_scan",
                "content": {"target": [target_url]},
            },
        )
        session_id = data.get("session_id")
        if not isinstance(session_id, str) or not _SESSION_ID_RE.fullmatch(session_id):
            raise AigError("aig_missing_session_id")
        return session_id

    async def status(self, session_id: str) -> str:
        data = await self._request(
            "GET", f"/api/v1/app/taskapi/status/{session_id}"
        )
        status = data.get("status")
        if status not in {"pending", "running", "completed", "failed"}:
            raise AigError("aig_invalid_task_status")
        return status

    async def result(self, session_id: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"/api/v1/app/taskapi/result/{session_id}"
        )
