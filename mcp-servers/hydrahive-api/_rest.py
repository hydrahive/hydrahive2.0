from __future__ import annotations
from typing import Any
import httpx
from _auth import Auth


class RestClient:
    def __init__(self, auth: Auth):
        self.auth = auth

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(verify=self.auth.verify_ssl, timeout=15.0)

    async def get(self, path: str, params: dict | None = None) -> Any:
        await self.auth.ensure_token()
        url = self.auth.base_url + path
        async with self._client() as c:
            r = await c.get(url, params=params, headers=self.auth.headers())
            if r.status_code == 401:
                await self.auth.refresh()
                r = await c.get(url, params=params, headers=self.auth.headers())
            r.raise_for_status()
            return r.json()

    async def post(self, path: str, body: dict | None = None) -> Any:
        await self.auth.ensure_token()
        url = self.auth.base_url + path
        async with self._client() as c:
            r = await c.post(url, json=body, headers=self.auth.headers())
            if r.status_code == 401:
                await self.auth.refresh()
                r = await c.post(url, json=body, headers=self.auth.headers())
            r.raise_for_status()
            return r.json() if r.content else {}

    async def patch(self, path: str, body: dict) -> Any:
        await self.auth.ensure_token()
        url = self.auth.base_url + path
        async with self._client() as c:
            r = await c.patch(url, json=body, headers=self.auth.headers())
            if r.status_code == 401:
                await self.auth.refresh()
                r = await c.patch(url, json=body, headers=self.auth.headers())
            r.raise_for_status()
            return r.json()
