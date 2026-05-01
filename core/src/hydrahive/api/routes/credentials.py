"""Credentials-CRUD pro User. Tokens kommen NIE im LLM-Kontext oder in
tool_results vor — fetch_url-Tool injecten transparent in Header."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.credentials import (
    Credential, delete_credential, get_credential, list_credentials, save_credential,
)
from hydrahive.credentials.models import ALL_TYPES, is_valid_name

router = APIRouter(prefix="/api/credentials", tags=["credentials"])


class CredentialBody(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    type: Literal["bearer", "basic", "cookie", "header", "query"]
    value: str
    url_pattern: str = "*"
    description: str = ""
    header_name: str = ""
    query_param: str = ""


def _serialize(c: Credential, *, mask: bool = True) -> dict:
    """Bei mask=True wird der value weggelassen — fürs Listing/UI."""
    return {
        "name": c.name, "type": c.type,
        "value": "" if mask else c.value,
        "value_set": bool(c.value),
        "url_pattern": c.url_pattern,
        "description": c.description,
        "header_name": c.header_name,
        "query_param": c.query_param,
    }


@router.get("")
def list_endpoint(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    username, _ = auth
    return [_serialize(c, mask=True) for c in list_credentials(username)]


@router.get("/{name}")
def get_endpoint(
    name: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    reveal: bool = False,
) -> dict:
    username, _ = auth
    c = get_credential(username, name)
    if not c:
        raise coded(status.HTTP_404_NOT_FOUND, "credential_not_found", name=name)
    return _serialize(c, mask=not reveal)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_or_update(
    req: CredentialBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    if not is_valid_name(req.name):
        raise coded(status.HTTP_400_BAD_REQUEST, "credential_name_invalid", name=req.name)
    if req.type not in ALL_TYPES:
        raise coded(status.HTTP_400_BAD_REQUEST, "credential_type_invalid", type=req.type)
    cred = Credential(
        name=req.name, type=req.type, value=req.value,  # type: ignore[arg-type]
        url_pattern=req.url_pattern or "*",
        description=req.description,
        header_name=req.header_name,
        query_param=req.query_param,
    )
    ok, err = save_credential(username, cred)
    if not ok:
        raise coded(status.HTTP_400_BAD_REQUEST, err or "credential_save_failed")
    return _serialize(cred, mask=True)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_endpoint(
    name: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    username, _ = auth
    if not delete_credential(username, name):
        raise coded(status.HTTP_404_NOT_FOUND, "credential_not_found", name=name)
