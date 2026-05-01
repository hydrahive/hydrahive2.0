"""Per-User Credential-Store für HTTP-Auth (Bearer, Basic, Cookie, Header, Query).

Datei pro User: $HH_DATA_DIR/credentials/<username>.json (chmod 600).
Tokens kommen nie in den LLM-Kontext oder tool_result — sie werden vom
fetch_url-Tool transparent in HTTP-Header injected anhand URL-Pattern-Match.

Skills referenzieren Credentials per Profile-Name in ihrem Frontmatter
`sources: - {url, auth: <profile_name>}`.
"""
from hydrahive.credentials.models import Credential, CredentialType
from hydrahive.credentials.store import (
    delete_credential,
    get_credential,
    list_credentials,
    match_credential,
    save_credential,
)

__all__ = [
    "Credential", "CredentialType",
    "delete_credential", "get_credential", "list_credentials",
    "match_credential", "save_credential",
]
