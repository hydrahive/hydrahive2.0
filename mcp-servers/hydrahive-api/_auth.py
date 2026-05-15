from __future__ import annotations
import os
import httpx


class Auth:
    def __init__(
        self,
        base_url: str = "",
        user: str = "",
        password: str = "",
        api_key: str = "",
        verify_ssl: bool = False,
    ):
        self.base_url = base_url or os.environ.get("HH_BASE_URL", "").rstrip("/")
        self.user = user or os.environ.get("HH_USER", "")
        self.password = password or os.environ.get("HH_PASS", "")
        self.api_key = api_key or os.environ.get("HH_API_KEY", "")
        self.verify_ssl = verify_ssl or os.environ.get("HH_VERIFY_SSL", "0") not in ("0", "false", "no")
        self.token: str = self.api_key

    async def ensure_token(self) -> None:
        if self.token:
            return
        if not self.user:
            raise RuntimeError("Kein HH_API_KEY und kein HH_USER/HH_PASS gesetzt")
        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            try:
                r = await client.post(
                    f"{self.base_url}/api/auth/login",
                    json={"username": self.user, "password": self.password},
                    timeout=10,
                )
                r.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(
                    f"Login fehlgeschlagen: HTTP {exc.response.status_code}"
                ) from None
            except httpx.TransportError as exc:
                raise RuntimeError(f"Login Netzwerkfehler: {type(exc).__name__}") from exc
            data = r.json()
            if "access_token" not in data:
                raise RuntimeError(
                    f"Login-Antwort enthält kein 'access_token'; Keys: {list(data.keys())}"
                )
            self.token = data["access_token"]
            self.password = ""  # Credential nach Login nicht mehr benötigt

    async def refresh(self) -> None:
        self.token = ""
        await self.ensure_token()

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
