"""Shared fixtures for the MCP integration test suite (work item 3.2).

The integration tier exercises the wired chain end-to-end through real
stdio against a production-shape MCP server subprocess:

    pytest test
        → ClientSession (stdio)
        → swc_workload_mcp subprocess (FastMCP + tools + bridge)
        → real swc-workload CLI subprocess
        → per-test temp workload folder

A single server subprocess is spawned per pytest session and shared
across all integration tests. Per-test isolation is achieved via
``tmp_path`` — each test operates against a fresh workload folder.
Workload state never crosses test boundaries because each tool call
includes the per-test folder path; the server itself holds no
per-test state.

The real ``swc-workload`` CLI is required at test time (no silent skips
per REQ-07); the suite fails loudly if the binary is missing.

Fixtures
--------
``anyio_backend`` (session)
    Forces anyio's pytest plugin to use the ``asyncio`` backend, scoped
    to session so the session-scoped async session fixture below can
    live across tests.

``_mcp_session`` (session)
    Spawns the MCP server subprocess once via ``stdio_client``, runs
    the MCP handshake, and yields the connected :class:`ClientSession`.

``workload_folder`` / ``workload_json`` / ``seed`` (function)
    Per-test workload state. ``workload_folder`` is a fresh subfolder
    under pytest's ``tmp_path``; ``workload.json`` is NOT pre-created.

``mcpw`` (function)
    Composes the shared session with the per-test workload paths and
    returns ``(call_tool, workload_folder, workload_json, seed)``.
    Mirrors the CLI suite's ``swcw``.

``mcpw_ready`` (function, async)
    Like ``mcpw`` but with the ``init`` tool already invoked. Mirrors
    the CLI suite's ``swcw_ready``.

``call_tool(name, **kwargs)``
    Coroutine. Calls ``session.call_tool(name, kwargs)`` against the
    shared session and returns a :class:`ToolCallResult` with two
    fields:

    - ``payload`` — parsed JSON from the tool's text content on
      success, or ``None`` if the call errored.
    - ``error`` — the error message string from the tool's error
      content on failure, or ``None`` on success.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable

import pytest

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


# Captured at module import — used by the session fixture both to fail
# loudly if the CLI is missing and to pin the server subprocess's
# environment so binary resolution inside it is deterministic.
_REAL_CLI_PATH = shutil.which("swc-workload")


# ---------------------------------------------------------------------------
# Async backend selection — session scope so the session-scoped MCP
# session fixture below shares an event loop with the per-test async
# fixtures and tests.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Force anyio's pytest plugin to use asyncio (session-wide loop)."""
    return "asyncio"


# ---------------------------------------------------------------------------
# Result type returned by the call_tool helper
# ---------------------------------------------------------------------------


@dataclass
class ToolCallResult:
    """Outcome of a single tool call through the stdio client.

    ``payload`` is the parsed JSON on success; ``error`` is the error
    message string on failure. Exactly one of the two is populated for
    a given call.
    """

    payload: Any = None
    error: str | None = None


def _extract_text(content_items: list[Any]) -> str:
    """Concatenate the ``.text`` of every ``TextContent`` in a content list."""
    pieces: list[str] = []
    for item in content_items:
        text = getattr(item, "text", None)
        if text is not None:
            pieces.append(text)
    return "".join(pieces)


# ---------------------------------------------------------------------------
# Session-scoped MCP session — one server subprocess for the whole run
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
async def _mcp_session() -> AsyncIterator[ClientSession]:
    """Spawn the MCP server subprocess once and yield a connected ClientSession.

    Session-scoped: one subprocess for the entire pytest run. All
    integration tests share this session. Per-test isolation is via
    per-test workload folders (``tmp_path``), not per-test session —
    the server holds no per-test state, and every tool call passes the
    folder path explicitly.

    Per REQ-07 the suite fails loudly if the real CLI isn't installed;
    no silent ``pytest.skip``.
    """
    if _REAL_CLI_PATH is None:
        pytest.fail(
            "swc-workload CLI must be installed to run the MCP "
            "integration suite (REQ-07): the server's startup check "
            "and the bridge both require it."
        )

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "swc_workload_mcp"],
        # Inherit os.environ then override SWC_WORKLOAD_BIN so binary
        # resolution inside the server process is deterministic
        # regardless of the developer's PATH.
        env={**os.environ, "SWC_WORKLOAD_BIN": _REAL_CLI_PATH},
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


# ---------------------------------------------------------------------------
# Per-test workload fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workload_folder(tmp_path: Path) -> Path:
    """The per-test workload folder. Already exists; empty contents."""
    folder = tmp_path / "workload"
    folder.mkdir()
    return folder


@pytest.fixture
def workload_json(workload_folder: Path) -> Path:
    """The expected ``workload.json`` path inside the workload folder.

    The file is NOT pre-created — each test calls ``init`` (or seeds
    the file directly via :func:`seed`) as required.
    """
    return workload_folder / "workload.json"


@pytest.fixture
def seed(workload_json: Path) -> Callable[[Any], None]:
    """Write ``workload.json`` directly, bypassing the ``init`` tool.

    Accepts ``str | bytes | dict``. Used only by tests that exercise the
    file-load error paths (malformed shape, top-level non-dict, JSON
    decode failures). Tests that use this helper SHOULD say so in their
    docstring; the default workflow remains "call ``init`` and let the
    CLI write the file".
    """

    def _seed(content: Any) -> None:
        if isinstance(content, (dict, list)):
            workload_json.write_text(json.dumps(content, indent=2))
        elif isinstance(content, bytes):
            workload_json.write_bytes(content)
        else:
            workload_json.write_text(str(content))

    return _seed


# ---------------------------------------------------------------------------
# mcpw / mcpw_ready — per-test composition of the shared session
# ---------------------------------------------------------------------------


@pytest.fixture
def mcpw(
    _mcp_session: ClientSession,
    workload_folder: Path,
    workload_json: Path,
    seed: Callable[[Any], None],
) -> tuple[
    Callable[..., Awaitable[ToolCallResult]],
    Path,
    Path,
    Callable[[Any], None],
]:
    """Yield ``(call_tool, workload_folder, workload_json, seed)``.

    ``call_tool(name, **kwargs)`` invokes the named MCP tool with the
    given kwargs through the shared stdio session and returns a
    :class:`ToolCallResult`. ``--workload`` is NOT auto-injected — each
    test passes ``workload=str(workload_folder)`` explicitly so the
    call site reads like the tool's public signature.

    The session is session-scoped (one server subprocess for the entire
    pytest run). Workload state is isolated via the per-test folder.
    """

    async def call_tool(name: str, **kwargs: Any) -> ToolCallResult:
        raw = await _mcp_session.call_tool(name, kwargs)
        text = _extract_text(raw.content)
        if raw.isError:
            return ToolCallResult(payload=None, error=text)
        try:
            payload = json.loads(text) if text else None
        except json.JSONDecodeError:
            # The tool returned non-JSON text on a success path
            # (shouldn't happen for our 12 tools but the helper should
            # not lose the data). Treat the raw text as the payload so
            # the test can assert on it directly.
            payload = text
        return ToolCallResult(payload=payload, error=None)

    return call_tool, workload_folder, workload_json, seed


@pytest.fixture
async def mcpw_ready(
    mcpw: tuple[
        Callable[..., Awaitable[ToolCallResult]],
        Path,
        Path,
        Callable[[Any], None],
    ],
) -> tuple[
    Callable[..., Awaitable[ToolCallResult]],
    Path,
    Path,
    Callable[[Any], None],
]:
    """Like ``mcpw`` but with ``init`` already invoked.

    Mirrors the CLI suite's ``swcw_ready``. Fails the test (not skip)
    if ``init`` errors — that's a fixture invariant.
    """
    call_tool, workload_folder, workload_json, seed_fn = mcpw
    result = await call_tool("init", workload=str(workload_folder))
    if result.error is not None:
        pytest.fail(f"mcpw_ready fixture: init tool returned error: {result.error}")
    return call_tool, workload_folder, workload_json, seed_fn
