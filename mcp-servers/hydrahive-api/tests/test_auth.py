import pytest
import respx
import httpx
from _auth import Auth

@pytest.mark.asyncio
async def test_login_setzt_token(base_url):
    with respx.mock:
        respx.post(f"{base_url}/api/auth/login").mock(
            return_value=httpx.Response(200, json={"access_token": "jwt-abc", "token_type": "bearer"})
        )
        auth = Auth(base_url=base_url, user="admin", password="secret")
        await auth.ensure_token()
        assert auth.token == "jwt-abc"

@pytest.mark.asyncio
async def test_api_key_braucht_kein_login(base_url):
    auth = Auth(base_url=base_url, api_key="hhk_test123")
    await auth.ensure_token()   # kein HTTP-Call
    assert auth.token == "hhk_test123"

@pytest.mark.asyncio
async def test_headers_enthalten_bearer(base_url):
    auth = Auth(base_url=base_url, api_key="hhk_abc")
    await auth.ensure_token()
    assert auth.headers() == {"Authorization": "Bearer hhk_abc"}

@pytest.mark.asyncio
async def test_refresh_loescht_token_und_loginiert_neu(base_url):
    with respx.mock:
        respx.post(f"{base_url}/api/auth/login").mock(
            return_value=httpx.Response(200, json={"access_token": "new-token", "token_type": "bearer"})
        )
        auth = Auth(base_url=base_url, user="admin", password="secret")
        auth.token = "old-token"
        await auth.refresh()
        assert auth.token == "new-token"
