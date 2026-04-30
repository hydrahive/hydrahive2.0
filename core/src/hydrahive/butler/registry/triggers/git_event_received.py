from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import (
    ParamSchema, TriggerSpec, register_trigger,
)


def _matches(params: dict, event: TriggerEvent) -> bool:
    if event.event_type != "git":
        return False
    want_event = (params.get("git_event") or "").lower()
    actual_event = (event.payload.get("git_event") or "").lower()
    if want_event and want_event != actual_event:
        return False
    want_provider = (params.get("provider") or "any").lower()
    if want_provider != "any":
        if (event.payload.get("provider") or "").lower() != want_provider:
            return False
    want_repo = (params.get("repo") or "").strip()
    if want_repo:
        if (event.payload.get("repo") or "") != want_repo:
            return False
    return True


register_trigger(TriggerSpec(
    subtype="git_event_received",
    label="Git-Event",
    description="Push / PR / Issue von GitHub oder Gitea",
    params=[
        ParamSchema(
            key="provider", label="Provider", kind="select",
            options=["any", "github", "gitea"], default="any",
        ),
        ParamSchema(
            key="git_event", label="Event-Typ", kind="select",
            options=["push", "pull_request", "issues", "issue_comment"],
        ),
        ParamSchema(
            key="repo", label="Repo (owner/name)", kind="text",
            placeholder="hydrahive/hydrahive2.0",
        ),
    ],
    matches=_matches,
))
