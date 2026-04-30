"""git_create_issue + git_add_comment — Phase 2: Stub.
Phase 4 verkabelt mit GitHub/Gitea-Token-Settings."""
from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ActionResult, ActionSpec, ParamSchema, register_action,
)
from hydrahive.butler.registry.actions._stub import stub_result
from hydrahive.butler.template import render


async def _exec_create(params: dict, event: TriggerEvent) -> ActionResult:
    rendered = {
        "provider": params.get("provider") or "github",
        "repo": render(params.get("repo") or "", event),
        "title": render(params.get("title") or "", event),
        "body": render(params.get("body") or "", event),
    }
    return stub_result("git_create_issue", rendered)


async def _exec_comment(params: dict, event: TriggerEvent) -> ActionResult:
    rendered = {
        "provider": params.get("provider") or "github",
        "repo": render(params.get("repo") or "", event),
        "issue_number": params.get("issue_number") or "",
        "body": render(params.get("body") or "", event),
    }
    return stub_result("git_add_comment", rendered)


_PROVIDER = ParamSchema(
    key="provider", label="Provider", kind="select",
    options=["github", "gitea"], default="github",
)
_REPO = ParamSchema(
    key="repo", label="Repo (owner/name)", kind="text", required=True,
    placeholder="hydrahive/hydrahive2.0",
)

register_action(ActionSpec(
    subtype="git_create_issue",
    label="Git-Issue erstellen",
    description="Legt ein Issue auf GitHub oder Gitea an",
    params=[
        _PROVIDER, _REPO,
        ParamSchema(key="title", label="Titel", kind="text", required=True),
        ParamSchema(key="body", label="Body (Jinja2)", kind="textarea"),
    ],
    execute=_exec_create,
))

register_action(ActionSpec(
    subtype="git_add_comment",
    label="Git-Kommentar hinzufügen",
    description="Kommentiert ein bestehendes Issue/PR",
    params=[
        _PROVIDER, _REPO,
        ParamSchema(key="issue_number", label="Issue-/PR-Nummer", kind="number",
                    required=True),
        ParamSchema(key="body", label="Body (Jinja2)", kind="textarea",
                    required=True),
    ],
    execute=_exec_comment,
))
