"""Agenten-Templates (Spec docs/specs/agent-templates.md Kap. 10).

Lesen: alle angemeldeten Nutzer. Ändern, Testen, Zurückholen, Löschen, Bindungen: nur Admins.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.agents import config as agent_config
from hydrahive.agents import templates as tpl
from hydrahive.agents.templates._health import bindings, health
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded

router = APIRouter(prefix="/api/agent-templates", tags=["agent-templates"])


def _known() -> set[str]:
    from hydrahive.llm import registry
    return set(registry.known_ids())


def _with_meta(t: dict, known: set[str], bound: dict[str, list[dict]]) -> dict:
    return {**t, "health": health(t, known), "bound_count": len(bound.get(t["id"], []))}


def _err(exc: tpl.TemplateError, code: int = status.HTTP_400_BAD_REQUEST):
    return coded(code, exc.code, field=exc.field) if exc.field else coded(code, exc.code)


class TemplateBody(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    group: str = "specialists"
    chain: list[str] = Field(default_factory=list, max_length=3)
    failover_on: list[str] | None = None
    budget: dict[str, Any] = Field(default_factory=dict)
    reply: dict[str, Any] = Field(default_factory=dict)
    on_demand: bool = False
    description: str = Field(default="", max_length=500)


class TestBody(BaseModel):
    prompt: str = Field(default="Reply with exactly one word: OK", max_length=200)


@router.get("")
def list_templates(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    known, bound = _known(), bindings(agent_config.list_all())
    return {"templates": [_with_meta(t, known, bound) for t in tpl.list_templates()],
            "groups": list(tpl.GROUPS)}


@router.get("/bindings", dependencies=[Depends(require_admin)])
def list_bindings() -> dict:
    return {"bindings": bindings(agent_config.list_all())}


@router.get("/{template_id}")
def get_template(template_id: str, _: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    t = tpl.get(template_id)
    if t is None:
        raise coded(status.HTTP_404_NOT_FOUND, "template_unknown")
    bound = bindings(agent_config.list_all())
    return {**_with_meta(t, _known(), bound), "bound": bound.get(template_id, []),
            "history": [{"revision": h["revision"], "updated_at": h.get("updated_at"),
                         "updated_by": h.get("updated_by")} for h in tpl.history(template_id)]}


@router.post("/{template_id}/preview", dependencies=[Depends(require_admin)])
def preview(template_id: str, body: TemplateBody) -> dict:
    try:
        tpl.check_id(template_id)
        new = tpl.normalize(body.model_dump(exclude_none=True))
    except tpl.TemplateError as exc:
        raise _err(exc)
    old = tpl.get(template_id) or {}
    changed = sorted(k for k in ("chain", "budget", "reply", "failover_on", "on_demand") if old.get(k) != new.get(k))
    return {"changed": changed, "affected": bindings(agent_config.list_all()).get(template_id, []),
            "health": health({**new, "id": template_id}, _known())}


@router.put("/{template_id}")
def put_template(template_id: str, body: TemplateBody,
                 auth: Annotated[tuple[str, str], Depends(require_admin)]) -> dict:
    try:
        saved = tpl.save(template_id, body.model_dump(exclude_none=True), by=auth[0])
    except tpl.TemplateError as exc:
        raise _err(exc)
    bound = bindings(agent_config.list_all())
    return {**_with_meta(saved, _known(), bound), "affected": bound.get(template_id, [])}


@router.post("/{template_id}/revert/{revision}")
def revert(template_id: str, revision: int, auth: Annotated[tuple[str, str], Depends(require_admin)]) -> dict:
    try:
        return tpl.revert(template_id, revision, by=auth[0])
    except tpl.TemplateError as exc:
        raise _err(exc, status.HTTP_404_NOT_FOUND)


@router.delete("/{template_id}", dependencies=[Depends(require_admin)])
def delete_template(template_id: str) -> dict:
    if bindings(agent_config.list_all()).get(template_id):
        raise coded(status.HTTP_409_CONFLICT, "template_in_use")
    try:
        tpl.delete(template_id)
    except tpl.TemplateError as exc:
        raise _err(exc, status.HTTP_404_NOT_FOUND)
    return {"deleted": template_id}


@router.post("/{template_id}/test", dependencies=[Depends(require_admin)])
async def test_chain(template_id: str, body: TestBody) -> dict:
    """Jede Stufe der Kette einzeln mit einer kurzen Frage prüfen."""
    from hydrahive.llm import client as llm_client
    t = tpl.get(template_id)
    if t is None:
        raise coded(status.HTTP_404_NOT_FOUND, "template_unknown")
    results = []
    for model in t["chain"]:
        try:
            answer = await llm_client.complete([{"role": "user", "content": body.prompt}], model=model, max_tokens=10)
            results.append({"model": model, "ok": True, "answer": (answer or "").strip()[:80]})
        except Exception as exc:  # Ergebnis je Stufe, nie ein 500
            from hydrahive.runner._failover import classify
            results.append({"model": model, "ok": False, "reason": classify(exc) or "error",
                            "message": str(exc)[:200]})
    return {"template": template_id, "results": results}
