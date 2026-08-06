"""Shared test-only helpers for real, isolated FastMCP HTTP servers over
loopback.

Recovery context: two integration tests in ``test_game_runner_http.py`` used
to both read the SAME hardcoded ``my_port`` (8901) out of the real, shared
``config/police/game.toml`` to start their own "police" server, and raced for
that one port whenever both ran in the same pytest session. Every test that
needs a live server must instead get its own dynamically allocated free
port and its own throwaway copy of the config directory, so tests never
collide with each other, a leftover server from a previous run, or an
unrelated process on the machine.
"""

from __future__ import annotations

import re
import socket
from pathlib import Path

from fastmcp import FastMCP

from police_peer.infrastructure.server_lifecycle import ManagedServer

HOST = "127.0.0.1"


def free_tcp_port(host: str = HOST) -> int:
    """Return a currently-unused local TCP port, assigned by the OS.

    Binds a throwaway socket to port 0 so the kernel picks a free ephemeral
    port, reads it back, then releases the socket immediately so the real
    server can bind it a moment later.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind((host, 0))
        return probe.getsockname()[1]


def is_port_free(port: int, host: str = HOST) -> bool:
    """True if ``port`` can be bound right now the same way a real server
    would bind it (i.e. with ``SO_REUSEADDR``, matching asyncio/uvicorn's own
    default on POSIX) -- not stricter than that, or a socket sitting in
    TIME_WAIT from an already-closed client connection would read as
    "occupied" even though a real server can still rebind the port.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def isolated_police_config_dir(
    real_config_dir: Path, dest_dir: Path, *, my_port: int, opponent_port: int
) -> Path:
    """A private copy of the real police config with test-only, dynamically
    allocated ports substituted in. Everything else (strategy, scoring,
    board, etc.) stays byte-identical to production so the runner under test
    exercises the real configuration shape, not a stripped-down fixture.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "game.json").write_bytes((real_config_dir / "game.json").read_bytes())
    toml_text = (real_config_dir / "game.toml").read_text()
    toml_text = re.sub(r"(?m)^my_port = \d+.*$", f"my_port = {my_port}", toml_text)
    toml_text = re.sub(
        r'(?m)^opponent_url = ".*"$',
        f'opponent_url = "http://{HOST}:{opponent_port}/mcp"',
        toml_text,
    )
    (dest_dir / "game.toml").write_text(toml_text)
    return dest_dir


async def start_test_server(
    mcp: FastMCP, port: int, host: str = HOST, *, middleware=None
) -> ManagedServer:
    """Start ``mcp``'s real HTTP ASGI app via the same production-grade
    :class:`~police_peer.infrastructure.server_lifecycle.ManagedServer` used
    by ``server_lifecycle.py`` itself -- see its module docstring for why
    task-cancellation-based shutdown does not reliably close the listening
    socket, and why this replaced it everywhere (production and tests
    alike). ``middleware``, when given, is forwarded unchanged (Gate A1
    auth/rate-limit middleware under real HTTP).
    """
    server = ManagedServer(mcp, host, port, middleware=middleware)
    await server.start()
    return server


async def stop_test_server(server: ManagedServer) -> None:
    """Stop a server started with :func:`start_test_server`, waiting for a
    genuinely graceful shutdown before returning."""
    await server.stop()
