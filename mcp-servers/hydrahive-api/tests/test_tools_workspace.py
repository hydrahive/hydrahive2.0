import pytest
import respx
import httpx
from _auth import Auth
from _rest import RestClient
from tools.workspace import list_projects, list_files, read_file


@pytest.mark.asyncio
async def test_list_projects(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/projects").mock(
            return_value=httpx.Response(200, json=[{"id": "p1", "name": "HydraHive2"}])
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await list_projects(RestClient(auth))
        assert result[0]["name"] == "HydraHive2"


@pytest.mark.asyncio
async def test_list_files(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/projects/p1/files").mock(
            return_value=httpx.Response(200, json={"entries": [{"name": "README.md"}]})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await list_files(RestClient(auth), "p1")
        assert result["entries"][0]["name"] == "README.md"


@pytest.mark.asyncio
async def test_read_file(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/projects/p1/files/read").mock(
            return_value=httpx.Response(200, json={"content": "# Hello", "path": "README.md"})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await read_file(RestClient(auth), "p1", "README.md")
        assert result["content"] == "# Hello"
