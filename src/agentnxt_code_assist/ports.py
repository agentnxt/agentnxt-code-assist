"""Port selection helpers for local services."""

from __future__ import annotations

import socket


def find_available_port(host: str, preferred_port: int, *, max_attempts: int = 100) -> int:
    """Return preferred_port when available, otherwise the next available port.

    This is intended for local operator/dev service startup. It checks sequentially
    from the preferred port and returns the first port that can be bound.
    """

    if preferred_port < 1 or preferred_port > 65535:
        raise ValueError("preferred_port must be between 1 and 65535")
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")

    for port in range(preferred_port, min(65535, preferred_port + max_attempts - 1) + 1):
        if is_port_available(host, port):
            return port
    raise RuntimeError(
        f"no available port found from {preferred_port} to "
        f"{min(65535, preferred_port + max_attempts - 1)}"
    )


def is_port_available(host: str, port: int) -> bool:
    bind_host = _bind_check_host(host)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((bind_host, port))
        except OSError:
            return False
    return True


def _bind_check_host(host: str) -> str:
    # 0.0.0.0 means all IPv4 interfaces. Binding to it is the strictest local
    # availability check and catches conflicts on localhost as well.
    if host in {"", "::"}:
        return "0.0.0.0"
    return host
