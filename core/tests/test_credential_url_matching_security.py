"""Regressionstests für Parser-Differenzen bei Credential-URLs."""
from hydrahive.credentials.models import matches_url


PATTERN = "https://api.example.com/*"


def test_matches_url_lehnt_backslash_userinfo_parserdifferenz_ab():
    assert matches_url(PATTERN, "https://evil.com\\@api.example.com/") is False


def test_matches_url_lehnt_userinfo_in_authority_ab():
    assert matches_url(PATTERN, "https://user:pass@api.example.com/v1") is False
