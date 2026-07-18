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

import asyncio
import contextlib
import re
import socket
from pathlib import Path

import uvicorn
from fastmcp import FastMCP

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
    mcp: FastMCP, port: int, host: str = HOST
) -> tuple[asyncio.Task, uvicorn.Server]:
    """Start ``mcp``'s real HTTP ASGI app under a directly-owned
    ``uvicorn.Server`` -- the same app object ``FastMCP.run_http_async``
    itself would serve, just assembled here instead of inside that helper --
    so this code keeps a handle to ``server`` and can request a genuinely
    graceful shutdown afterwards.

    This deliberately does NOT go through ``run_http_async`` + task
    cancellation (the pattern used elsewhere in this suite and by
    ``police_peer.infrastructure.server_lifecycle.stop_server``, and even by
    FastMCP's own official ``fastmcp.utilities.tests.run_server_async``
    helper). Verified by direct experiment during the Batch-2 port-collision
    recovery: uvicorn's ``Server._serve()`` only calls ``Server.shutdown()``
    (which actually closes the listening socket) when its polling
    ``main_loop()`` returns normally after observing ``should_exit``; a raw
    ``Task.cancel()`` interrupts ``_serve()`` mid-``main_loop()`` and skips
    ``shutdown()`` entirely -- there is no ``try/finally`` around it -- which
    permanently leaks the listening socket for the rest of the process, not
    just a transient race. Owning the ``uvicorn.Server`` instance lets this
    helper set ``should_exit = True`` instead, which *is* observed by
    ``main_loop()`` and reaches the real socket-closing ``shutdown()`` path.
    """
    app = mcp.http_app(transport="http")
    config = uvicorn.Config(
        app, host=host, port=port, log_level="warning", lifespan="on", ws="websockets-sansio"
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.01)
    return task, server


async def stop_test_server(task: asyncio.Task, server: uvicorn.Server) -> None:
    """Request a graceful shutdown of a server started with
    :func:`start_test_server` and wait for it, so the listening socket is
    genuinely closed (not just no-longer-cancelled) before this returns.

    Tolerates the task already being cancelled: production's
    ``server_lifecycle.stop_server`` (used internally by
    ``run_subgame_headless``/``run_series_headless`` for this peer's own
    server) drains "every other task still pending on the loop" as part of
    its own teardown, which -- when a test runs a second real server
    concurrently on the same loop, e.g. an opponent stand-in -- reaches this
    task too. Either way the caller's intent (this server should be stopped)
    is satisfied.
    """
    server.should_exit = True
    with contextlib.suppress(asyncio.CancelledError):
        await task
