from client import HiveClient


def test_tls_verification_on_by_default():
    c = HiveClient("https://example.invalid")
    assert c.verify_ssl is True


def test_api_key_used_as_initial_token():
    c = HiveClient("https://example.invalid", api_key="hhk_abc")
    assert c._headers() == {"Authorization": "Bearer hhk_abc"}
