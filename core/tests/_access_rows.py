"""Gemeinsames Aufräumen für die Access-Tests.

Freigaben und Gruppen aus einem Test dürfen den nächsten nicht beeinflussen
(ein übriggebliebenes 'everyone' würde Ablehnungs-Tests grün lügen). Aufgeräumt
wird nur über only_own_rows: Zeilen, die vor dem Test schon da waren, bleiben.
"""
from __future__ import annotations

import pytest

from tests._own_rows import only_own_rows

ACCESS_TABLES = (
    "access_capability_grants", "access_group_members", "access_groups", "access_audit",
    "access_seen_capabilities",
)


@pytest.fixture(autouse=True)
def _own_access_rows(client):
    with only_own_rows(*ACCESS_TABLES):
        yield
