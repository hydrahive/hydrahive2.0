"""Butler: Der Trigger „Webhook empfangen“ passt auf jeden Projekt-Webhook.

Vorher verglich der Matcher den Parameter ``hook_id`` mit ``event.channel``
(``project:<id>``). Die Oberfläche ließ keinen Doppelpunkt zu, ein gesetztes
Feld passte also nie. Das Feld entfällt; alte Flows mit ``hook_id`` laufen
weiter, der Wert wird ignoriert.
"""
from __future__ import annotations

import pytest

from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry import TRIGGERS, load_builtins


@pytest.fixture(autouse=True)
def _registry():
    load_builtins()


def _spec():
    return TRIGGERS["webhook_received"]


def test_passt_auf_webhook_event_ohne_parameter():
    event = TriggerEvent(event_type="webhook", channel="project:p1", payload={"a": 1})
    assert _spec().matches({}, event) is True


def test_alter_hook_id_parameter_wird_ignoriert():
    event = TriggerEvent(event_type="webhook", channel="project:p1")
    assert _spec().matches({"hook_id": "my-hook"}, event) is True


def test_passt_nicht_auf_nachrichten_event():
    event = TriggerEvent(event_type="message", channel="whatsapp", message_text="x")
    assert _spec().matches({}, event) is False


def test_trigger_hat_keinen_hook_id_parameter_mehr():
    assert [p.key for p in _spec().params] == []


def test_beschreibung_nennt_die_echte_route():
    assert "/api/butler/webhooks/project/" in _spec().description
