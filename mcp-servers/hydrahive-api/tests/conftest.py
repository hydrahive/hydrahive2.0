import pytest

@pytest.fixture
def base_url() -> str:
    return "https://hydrahive.example.test"

@pytest.fixture
def token() -> str:
    return "test-jwt-token"
