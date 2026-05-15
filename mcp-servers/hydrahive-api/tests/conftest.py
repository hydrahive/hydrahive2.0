import pytest

@pytest.fixture
def base_url() -> str:
    return "https://192.168.3.22"

@pytest.fixture
def token() -> str:
    return "test-jwt-token"
