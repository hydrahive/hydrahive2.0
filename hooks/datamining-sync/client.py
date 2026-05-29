"""Dünner synchroner HydraHive-REST-Client für den Sync-Hook.

Auth: HH_API_KEY (Bearer) ODER HH_USER/HH_PASS (Login). Bewusst minimal —
Orchestrator-Tests injizieren einen Fake mit denselben Methoden.
"""
from __future__ import annotations

import httpx


class HiveClient:
    def __init__(self, base_url: str, api_key: str | None = None,
                 user: str | None = None, password: str | None = None,
                 verify_ssl: bool = False, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.user = user
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self._token: str | None = api_key

    def _login(self) -> None:
        r = httpx.post(f"{self.base_url}/api/auth/login",
                       json={"username": self.user, "password": self.password},
                       timeout=self.timeout, verify=self.verify_ssl)
        r.raise_for_status()
        self._token = r.json()["access_token"]

    def _headers(self) -> dict:
        if not self._token and self.user:
            self._login()
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    def ensure_session(self, agent_id: str, title: str) -> str:
        r = httpx.post(f"{self.base_url}/api/sessions",
                       json={"agent_id": agent_id, "title": title},
                       headers=self._headers(), timeout=self.timeout, verify=self.verify_ssl)
        r.raise_for_status()
        return r.json()["id"]

    def log(self, session_id: str, message_id: str, role: str,
            content, created_at: str | None) -> None:
        r = httpx.post(f"{self.base_url}/api/sessions/{session_id}/log",
                       json={"message_id": message_id, "role": role,
                             "content": content, "created_at": created_at},
                       headers=self._headers(), timeout=self.timeout, verify=self.verify_ssl)
        r.raise_for_status()
