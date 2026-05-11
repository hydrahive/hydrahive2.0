"""Defensiv-Test: HH2 darf niemals Telemetry-Frameworks einbinden.

Wenn dieser Test fehlschlägt, hat jemand Sentry/PostHog/Mixpanel/Analytics-Code
in den Source eingebracht. Das verletzt das HH2-Versprechen "No Telemetry"
(siehe docs/ARCHITECTURE.md und Research-Note 06).

Geprüft wird statisch:
  1. Keine Telemetry-Bibliotheken sind installiert (importlib).
  2. Keine Source-Datei importiert eines dieser Module.

Beide Checks zusammen verhindern auch "lazy imports" innerhalb von
Funktionen — der String-Scan greift auch wenn der Import nicht ausgeführt
wird.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

# Liste der verbotenen Module. Diese sind klassische SaaS-Telemetry/Analytics:
# - sentry_sdk: Error-Tracking, sendet Stacktraces an sentry.io
# - posthog: Product-Analytics, sendet Events an posthog.com
# - mixpanel: User-Analytics
# - segment, analytics: User-Behavior-Tracking
# - amplitude: User-Analytics
# - datadog, ddtrace: APM, sendet Traces an datadoghq.com
# - newrelic: APM
# - rollbar: Error-Tracking
# - bugsnag: Error-Tracking
# - opentelemetry: Distributed Tracing (auch oft phone-home)
FORBIDDEN_MODULES = [
    "sentry_sdk",
    "posthog",
    "mixpanel",
    "segment",
    "analytics",  # Segment ships "analytics-python" as `analytics`
    "amplitude",
    "datadog",
    "ddtrace",
    "newrelic",
    "rollbar",
    "bugsnag",
    "opentelemetry",
]

# Wir scannen den Source — nicht installierte Module reichen nicht aus
# (jemand könnte versehentlich nur den Import + Aufruf adden ohne dep-Eintrag).
_HYDRAHIVE_SRC = Path(__file__).resolve().parents[1] / "src" / "hydrahive"


def test_telemetry_modules_not_installed() -> None:
    """Keines der verbotenen Telemetry-Module darf als Python-Package
    installiert sein. Falls eines dieser Module gebraucht würde (es gibt
    keinen legitimen Grund), müsste der Test bewusst angepasst werden —
    das ist genau die Hürde die wir wollen."""
    found = []
    for mod in FORBIDDEN_MODULES:
        if importlib.util.find_spec(mod) is not None:
            found.append(mod)
    if found:
        pytest.fail(
            "Verbotene Telemetry-Module installiert: "
            + ", ".join(found)
            + "\nHH2 sendet keine Telemetrie — siehe docs/ARCHITECTURE.md."
        )


def test_no_telemetry_imports_in_source() -> None:
    """Statischer Scan: keine Datei unter ``core/src/hydrahive/`` darf
    ein verbotenes Modul importieren. Erfasst auch ``import x as y``
    und ``from x import …`` sowie lazy imports innerhalb von Funktionen."""
    assert _HYDRAHIVE_SRC.is_dir(), f"Source-Verzeichnis fehlt: {_HYDRAHIVE_SRC}"

    # Regex matched: 'import X', 'import X.Y', 'from X import …', 'from X.Y import …'
    patterns = [
        re.compile(rf"^\s*import\s+{re.escape(mod)}(?:\.|$|\s)", re.MULTILINE)
        for mod in FORBIDDEN_MODULES
    ] + [
        re.compile(rf"^\s*from\s+{re.escape(mod)}(?:\.|\s)", re.MULTILINE)
        for mod in FORBIDDEN_MODULES
    ]

    offenders: list[tuple[Path, str]] = []
    for py_file in _HYDRAHIVE_SRC.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for pat in patterns:
            for match in pat.finditer(text):
                offenders.append((py_file, match.group(0).strip()))

    if offenders:
        lines = [f"  {p.relative_to(_HYDRAHIVE_SRC.parents[2])}: {imp}" for p, imp in offenders]
        pytest.fail(
            "Telemetry-Imports im Source gefunden:\n"
            + "\n".join(lines)
            + "\nHH2 sendet keine Telemetrie — siehe docs/ARCHITECTURE.md."
        )


def test_no_litellm_callbacks_configured() -> None:
    """LiteLLM erlaubt globale Callbacks via ``litellm.success_callback``
    etc., die Telemetry exfiltrieren könnten. Diese dürfen im HH2-Code
    nicht gesetzt werden."""
    forbidden_assignments = [
        re.compile(r"litellm\.success_callback\s*=", re.MULTILINE),
        re.compile(r"litellm\.failure_callback\s*=", re.MULTILINE),
        re.compile(r"litellm\.callbacks\s*=", re.MULTILINE),
        re.compile(r"litellm\.set_verbose\s*=\s*True", re.MULTILINE),
    ]
    offenders: list[tuple[Path, str]] = []
    for py_file in _HYDRAHIVE_SRC.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for pat in forbidden_assignments:
            for match in pat.finditer(text):
                offenders.append((py_file, match.group(0).strip()))

    if offenders:
        lines = [f"  {p.relative_to(_HYDRAHIVE_SRC.parents[2])}: {imp}" for p, imp in offenders]
        pytest.fail(
            "LiteLLM-Callback-Konfiguration gefunden (potenzielle Telemetry-Quelle):\n"
            + "\n".join(lines)
        )
