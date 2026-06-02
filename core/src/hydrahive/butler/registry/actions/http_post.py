"""http_post — echter HTTP-Call mit Jinja2-Template-Body."""
import json
import logging

from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ActionResult, ActionSpec, ParamSchema, register_action,
)
from hydrahive.butler.template import render
from hydrahive.net.ssrf import SsrfBlocked, safe_async_client, validate_outbound_url

logger = logging.getLogger(__name__)


async def _execute(params: dict, event: TriggerEvent) -> ActionResult:
    url = render(params.get("url") or "", event).strip()
    if not url:
        return ActionResult(ok=False, detail="url_missing")
    # SSRF-Schutz (#187): nur http/https, keine internen Hosts/IPs/Metadata.
    blocked = validate_outbound_url(url)
    if blocked:
        logger.warning("http_post: URL geblockt (%s): %s", blocked, url)
        return ActionResult(ok=False, detail=f"url_blocked: {blocked}")
    body_raw = render(params.get("body") or "", event)
    headers_raw = params.get("headers") or "{}"
    try:
        headers = json.loads(headers_raw) if isinstance(headers_raw, str) else dict(headers_raw)
    except json.JSONDecodeError:
        headers = {}
    headers.setdefault("Content-Type", "application/json")
    try:
        # safe_async_client: nur http/https, pinnt den Connect an eine vorab
        # validierte IP (DNS-Rebinding-sicher, #206) und hält follow_redirects=False
        # (ein 30x auf eine interne URL würde den Check sonst umgehen).
        async with safe_async_client(url, timeout=15.0) as cli:
            r = await cli.post(url, content=body_raw.encode("utf-8"), headers=headers)
        return ActionResult(ok=r.is_success, detail=f"HTTP {r.status_code}")
    except SsrfBlocked as e:
        logger.warning("http_post: URL geblockt (%s): %s", e, url)
        return ActionResult(ok=False, detail=f"url_blocked: {e}")
    except Exception as e:
        logger.warning("http_post failed: %s", e)
        return ActionResult(ok=False, detail=f"error: {e}")


register_action(ActionSpec(
    subtype="http_post",
    label="HTTP-POST",
    description="POST mit Jinja2-Template-Body. Default-Header Content-Type=JSON.",
    params=[
        ParamSchema(key="url", label="URL", kind="text", required=True,
                    placeholder="https://example.com/webhook"),
        ParamSchema(key="body", label="Body (Jinja2-Template)", kind="textarea",
                    placeholder='{"text": "{{ event.message_text }}"}'),
        ParamSchema(key="headers", label="Headers (JSON)", kind="textarea",
                    placeholder='{"X-API-Key": "..."}'),
    ],
    execute=_execute,
))
