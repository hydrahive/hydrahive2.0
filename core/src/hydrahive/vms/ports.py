"""VNC-Port-Allocator: 5900–5999 mit DB-Lookup + Realtime-Probe."""
from __future__ import annotations

import socket

from hydrahive.vms.db import used_vnc_ports

VNC_PORT_RANGE = range(5900, 6000)  # 100 Slots


def _port_in_use(port: int) -> bool:
    """Prüft ob TCP-Port von irgendeinem Prozess gehalten wird."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.2)
    try:
        s.bind(("127.0.0.1", port))
        return False
    except OSError:
        return True
    finally:
        s.close()


def allocate_vnc_port() -> int | None:
    """Erster freier Port aus der Range — DB-known + System-frei.

    Returns None wenn alle 100 belegt.
    """
    db_used = used_vnc_ports()
    for port in VNC_PORT_RANGE:
        if port in db_used:
            continue
        if _port_in_use(port):
            continue
        return port
    return None
