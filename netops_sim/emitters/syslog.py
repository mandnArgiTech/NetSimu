"""Syslog emitter: writes RFC-5424-shaped lines to file or UDP."""
from __future__ import annotations

import socket
from datetime import datetime
from typing import Any

_SEVERITY_MAP = {
    "emergency": 0, "alert": 1, "critical": 2, "error": 3,
    "warning": 4, "notice": 5, "info": 6, "debug": 7,
}


def format_rfc5424(event: dict[str, Any]) -> str:
    sev = _SEVERITY_MAP.get(event.get("severity", "info"), 6)
    facility = 16  # local0
    pri = facility * 8 + sev
    ts = datetime.fromtimestamp(event.get("ts", 0)).isoformat()
    host = event.get("entity", "-")
    msg = event.get("msg", "")
    return f"<{pri}>1 {ts} {host} netsimu - - - {msg}"


class SyslogFileEmitter:
    def __init__(self, path: str) -> None:
        self.path = path
        self.fp = open(path, "a")

    def __call__(self, event: dict[str, Any]) -> None:
        if event.get("kind") != "syslog":
            return
        self.fp.write(format_rfc5424(event) + "\n")
        self.fp.flush()

    def close(self) -> None:
        self.fp.close()


class SyslogUDPEmitter:
    def __init__(self, host: str = "127.0.0.1", port: int = 5514) -> None:
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def __call__(self, event: dict[str, Any]) -> None:
        if event.get("kind") != "syslog":
            return
        line = format_rfc5424(event)
        self.sock.sendto(line.encode(), (self.host, self.port))

    def close(self) -> None:
        self.sock.close()
