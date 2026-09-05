"""Der Modul-SSE-Abschluss muss vor dem Prozess-Restart ausgeliefert werden."""
from unittest.mock import MagicMock, patch


def test_request_restart_is_delayed_and_daemon():
    from hydrahive.modules import installer

    timer = MagicMock()
    with patch("hydrahive.modules.installer.threading.Timer", return_value=timer) as factory:
        installer._request_restart()

    factory.assert_called_once()
    assert factory.call_args.args[0] == 2.0
    assert timer.daemon is True
    timer.start.assert_called_once_with()
