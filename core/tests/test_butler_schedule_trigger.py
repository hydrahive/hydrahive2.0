from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.registry.triggers.schedule_fired import _matches


def _event(schedule_id: str) -> TriggerEvent:
    return TriggerEvent(event_type="schedule", payload={"schedule_id": schedule_id})


def test_heartbeat_task_id_filter_passt():
    params = {"task_id": "task-1"}
    assert _matches(params, _event("task-1")) is True
    assert _matches(params, _event("anderer-task")) is False


def test_heartbeat_task_id_filter_passt_nicht():
    assert _matches({"task_id": "task-1"}, _event("task-2")) is False


def test_schedule_id_hat_vorrang_vor_task_id():
    params = {"schedule_id": "neu", "task_id": "alt"}
    assert _matches(params, _event("neu")) is True
    assert _matches(params, _event("alt")) is False
