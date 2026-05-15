import pytest
import respx
import httpx
from _auth import Auth
from _rest import RestClient


@pytest.mark.asyncio
async def test_get_ruft_korrekte_url(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/health").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        auth = Auth(base_url=base_url, api_key=token)
        client = RestClient(auth)
        result = await client.get("/api/health")
        assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_401_triggert_refresh_und_retry(base_url):
    with respx.mock:
        respx.post(f"{base_url}/api/auth/login").mock(
            return_value=httpx.Response(200, json={"access_token": "new-token", "token_type": "bearer"})
        )
        call_count = 0

        def side_effect(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(401)
            return httpx.Response(200, json={"ok": True})

        respx.get(f"{base_url}/api/health").mock(side_effect=side_effect)

        auth = Auth(base_url=base_url, user="admin", password="secret")
        auth.token = "old-expired-token"
        client = RestClient(auth)
        result = await client.get("/api/health")
        assert result["ok"] is True
        assert auth.token == "new-token"


@pytest.mark.asyncio
async def test_post_leere_antwort_gibt_dict(base_url, token):
    with respx.mock:
        respx.post(f"{base_url}/api/test").mock(
            return_value=httpx.Response(204, content=b"")
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await RestClient(auth).post("/api/test")
        assert result == {}
