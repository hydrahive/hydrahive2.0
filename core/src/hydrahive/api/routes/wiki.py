"""HydraWiki CRUD-Endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.wiki import index as wiki_index
from hydrahive.wiki import storage as wiki_storage
from hydrahive.wiki.models import WikiPage, make_slug

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


class PageIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=100_000)
    tags: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    source_url: str = Field(default="", max_length=500)
    slug: str | None = None


def _serialize(page: WikiPage, backlinks: list[str] | None = None) -> dict:
    return {
        "slug": page.slug,
        "title": page.title,
        "body": page.body,
        "tags": page.tags,
        "entities": page.entities,
        "source_url": page.source_url,
        "author": page.author,
        "created_at": page.created_at,
        "updated_at": page.updated_at,
        "backlinks": backlinks or [],
    }


@router.get("")
def list_pages(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    q: str | None = None,
) -> list[dict]:
    if q and q.strip():
        results = wiki_index.search(q.strip())
        return [{"slug": r["slug"], "title": r["title"], "tags": r["tags"],
                 "author": r["author"], "updated_at": r["updated_at"],
                 "snippet": r.get("snippet", ""), "body": "", "backlinks": []} for r in results]
    pages = wiki_storage.list_all()
    return [_serialize(p) for p in pages]


@router.get("/{slug}")
def get_page(
    slug: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    page = wiki_storage.load(slug)
    if not page:
        raise coded(status.HTTP_404_NOT_FOUND, "wiki_page_not_found", slug=slug)
    bl = wiki_index.backlinks_for(slug)
    return _serialize(page, bl)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_page(
    req: PageIn,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    slug = req.slug or make_slug(req.title)
    if not slug:
        raise coded(status.HTTP_400_BAD_REQUEST, "wiki_invalid_slug")
    if wiki_storage.slug_exists(slug):
        raise coded(status.HTTP_409_CONFLICT, "wiki_slug_exists", slug=slug)
    page = WikiPage(
        slug=slug, title=req.title, body=req.body,
        tags=req.tags, entities=req.entities,
        source_url=req.source_url, author=username,
    )
    page = wiki_storage.save(page)
    wiki_index.upsert(page)
    return _serialize(page)


@router.put("/{slug}")
def update_page(
    slug: str,
    req: PageIn,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    page = wiki_storage.load(slug)
    if not page:
        raise coded(status.HTTP_404_NOT_FOUND, "wiki_page_not_found", slug=slug)
    page.title = req.title
    page.body = req.body
    page.tags = req.tags
    page.entities = req.entities
    page.source_url = req.source_url
    page = wiki_storage.save(page)
    wiki_index.upsert(page)
    return _serialize(page)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_page(
    slug: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    if not wiki_storage.delete(slug):
        raise coded(status.HTTP_404_NOT_FOUND, "wiki_page_not_found", slug=slug)
    wiki_index.remove(slug)
