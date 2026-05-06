"""Gemeinsame Test-Fixtures und Hilfsfunktionen für alle HydraHive2-Tests."""
import pytest
from httpx import Response


# ---------------------------------------------------------------------------
# FastAPI-Fehlerformat
# Alle API-Fehler haben die Form: {"detail": {"code": "...", "params": {}}}
# Zugriff: error_code(response) == "invalid_credentials"
# ---------------------------------------------------------------------------

def error_code(response: Response) -> str:
    """Gibt den code-String aus einer FastAPI-Fehlerantwort zurück."""
    return response.json()["detail"]["code"]


def error_params(response: Response) -> dict:
    """Gibt die params aus einer FastAPI-Fehlerantwort zurück."""
    return response.json()["detail"].get("params", {})


# ---------------------------------------------------------------------------
# Auth-Hilfsfunktion
# ---------------------------------------------------------------------------

def bearer(token: str) -> dict:
    """Gibt einen Authorization-Header zurück."""
    return {"Authorization": f"Bearer {token}"}
