"""Override-Store für GUI-editierbare Settings.

Persistiert GUI-Änderungen in `config_dir/overrides.json`. Auflösung:
**Override → Env-Var → Default**. Ohne Override identisch zu `os.environ.get`
(env_var, default) → null Regression für bestehende Deployments.

Der Pfad wird DIREKT aus `HH_CONFIG_DIR` gelesen — NICHT über das gecachte
`settings.config_dir`. Sonst würde ein Setting-Read zur Import-Zeit die
`@cached_property` einfrieren (bevor das Test-Env `HH_CONFIG_DIR` setzt) und die
ganze Session vergiften. Default identisch zu `_paths.config_dir`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from hydrahive.settings.editable import BY_KEY

_CONFIG_DIR_DEFAULT = "/etc/hydrahive2"


def _path() -> Path:
    return Path(os.environ.get("HH_CONFIG_DIR", _CONFIG_DIR_DEFAULT)) / "overrides.json"


def get_overrides() -> dict[str, str]:
    p = _path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text("utf-8"))
        return {k: str(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _write(data: dict[str, str]) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    tmp.replace(p)


def set_override(key: str, value: str) -> None:
    if key not in BY_KEY:
        raise KeyError(f"{key!r} ist kein editierbares Setting")
    data = get_overrides()
    data[key] = str(value)
    _write(data)


def clear_override(key: str) -> None:
    data = get_overrides()
    if key in data:
        del data[key]
        _write(data)


def env_or_override(key: str, env_var: str, default: str = "") -> str:
    """Drop-in für os.environ.get(env_var, default), aber Override gewinnt.

    Damit liest ein Settings-Mixin den GUI-Wert, fällt aber sonst exakt auf das
    bisherige Env/Default zurück.
    """
    ov = get_overrides().get(key)
    if ov is not None:
        return ov
    return os.environ.get(env_var, default)


def resolve(key: str) -> str:
    """Aktueller Wert eines registrierten Settings (Override → Env → Default)."""
    s = BY_KEY.get(key)
    if s is None:
        return ""
    return env_or_override(key, s.env_var, s.default)
