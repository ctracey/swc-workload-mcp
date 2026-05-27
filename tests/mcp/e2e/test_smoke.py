"""End-to-end smoke test for the FastMCP server (REQ-09 from work item 2.4).

Goes through the SDK's in-memory client/server harness against the real
``swc-workload`` CLI. Per solution.md, this test FAILS LOUDLY (does not
skip) if the CLI isn't installed — the test exists precisely to verify
the wired-up chain works against the real CLI.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest


# Captured at import time, before any test fixture overrides PATH. The
# smoke test uses this to invoke the real CLI even though the autouse
# ``_isolate_env`` fixture clears PATH for safety.
_REAL_CLI_PATH = shutil.which("swc-workload")


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear env vars the bridge / server consult so the test starts clean.

    The test body re-sets ``SWC_WORKLOAD_BIN`` to ``_REAL_CLI_PATH`` after
    this fixture wipes it, so the bridge can resolve the real CLI captured
    at import time.
    """
    monkeypatch.delenv("SWC_WORKLOAD_BIN", raising=False)
    # Hide any real `swc-workload` on PATH so resolution is deterministic.
    monkeypatch.setenv("PATH", str(Path("/nonexistent")))


@pytest.fixture
def anyio_backend() -> str:
    """Force anyio's pytest plugin to use asyncio (single backend)."""
    return "asyncio"


# ---------------------------------------------------------------------------
# REQ-09 — end-to-end smoke through the running server via in-memory client
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_init_through_server_creates_workload_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end smoke: `init` via the running FastMCP server creates a workload.

    Per solution.md, this test FAILS LOUDLY (does not skip) if the
    ``swc-workload`` CLI isn't on PATH — the test exists precisely to
    verify the wired-up chain works against the real CLI.
    """
    if _REAL_CLI_PATH is None:
        pytest.fail(
            "swc-workload CLI must be installed to run the end-to-end smoke; "
            "this test verifies the happy path through FastMCP → tools → "
            "bridge → CLI."
        )

    # The autouse `_isolate_env` fixture wiped PATH; point the bridge at
    # the real CLI captured at import time.
    monkeypatch.setenv("SWC_WORKLOAD_BIN", _REAL_CLI_PATH)

    from mcp.shared.memory import create_connected_server_and_client_session

    from swc_workload_mcp import server

    workload_dir = tmp_path / "workload"
    workload_dir.mkdir()

    async with create_connected_server_and_client_session(
        server.mcp._mcp_server
    ) as session:
        result = await session.call_tool(
            "init", {"workload": str(workload_dir)}
        )

    assert not result.isError, f"init tool returned error: {result.content}"

    workload_json = workload_dir / "workload.json"
    assert workload_json.exists(), (
        f"workload.json was not created at {workload_json}"
    )

    # Parses as JSON and looks like a workload (CLI contract).
    parsed = json.loads(workload_json.read_text())
    assert isinstance(parsed, dict), "workload.json must be a JSON object"
