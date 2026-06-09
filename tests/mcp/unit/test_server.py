"""Tests for the FastMCP server wiring (work item 2.4).

Each test corresponds to a Gherkin scenario in
`.swc/mcp/workitems/2.4/specs.md`. The unit tests monkeypatch
`mcp.run()` so the stdio loop is never entered. The REQ-09 end-to-end
smoke test (real CLI through the in-memory client/server harness) lives
in ``tests/mcp/e2e/test_smoke.py``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from swc_workload_mcp import bridge


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear env vars the bridge / server consult so tests start clean.

    Tests that need the CLI to be resolvable set SWC_WORKLOAD_BIN
    explicitly via monkeypatch in their own body.
    """
    monkeypatch.delenv("SWC_WORKLOAD_BIN", raising=False)
    # Hide any real `swc-workload` on PATH so resolution is deterministic.
    monkeypatch.setenv("PATH", str(Path("/nonexistent")))


@pytest.fixture
def fake_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``SWC_WORKLOAD_BIN`` at an executable file so resolution succeeds.

    The file is never executed by the unit tests — they monkeypatch
    ``mcp.run()`` so the server never reaches the run loop. The fake
    just satisfies the startup presence check.
    """
    fake = tmp_path / "swc-workload"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    monkeypatch.setenv("SWC_WORKLOAD_BIN", str(fake))
    return fake


class _RunRecorder:
    """Stand-in for ``FastMCP.run`` that records the transport argument."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple, dict]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append((args, kwargs))


# ---------------------------------------------------------------------------
# REQ-01 — happy startup: construct FastMCP, register tools, run stdio
# ---------------------------------------------------------------------------


def test_main_constructs_fastmcp_registers_tools_and_runs_stdio(
    fake_cli: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swc_workload_mcp import server, tools

    recorder = _RunRecorder()
    monkeypatch.setattr(server.mcp, "run", recorder)

    server.main()

    # mcp.run() was invoked exactly once with stdio transport.
    assert len(recorder.calls) == 1
    args, kwargs = recorder.calls[0]
    transport = args[0] if args else kwargs.get("transport")
    assert transport == "stdio"

    # Every callable in tools.TOOLS is registered on the instance —
    # no extras leaked in, no entries dropped.
    registered = {t.name for t in server.mcp._tool_manager.list_tools()}
    expected = {fn.__name__ for fn in tools.TOOLS}
    assert registered == expected


# ---------------------------------------------------------------------------
# REQ-02 — fail-fast on missing CLI (no env, not on PATH)
# ---------------------------------------------------------------------------


def test_main_exits_nonzero_when_cli_is_missing(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swc_workload_mcp import server

    # Hard-guard: if main() reaches run() despite the missing CLI, fail loud.
    def _must_not_run(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("mcp.run() must NOT be invoked when CLI is missing")

    monkeypatch.setattr(server.mcp, "run", _must_not_run)

    with pytest.raises(SystemExit) as excinfo:
        server.main()

    assert excinfo.value.code != 0

    err = capsys.readouterr().err
    assert "swc-workload not found" in err
    assert "https://github.com/ctracey/swc-workload-cli" in err
    assert "SWC_WORKLOAD_BIN" in err


# ---------------------------------------------------------------------------
# REQ-02 — fail-fast on misconfigured SWC_WORKLOAD_BIN
# ---------------------------------------------------------------------------


def test_main_exits_nonzero_when_env_var_points_at_nonexistent_path(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from swc_workload_mcp import server

    bad_path = tmp_path / "does-not-exist"
    monkeypatch.setenv("SWC_WORKLOAD_BIN", str(bad_path))

    def _must_not_run(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("mcp.run() must NOT be invoked when CLI is missing")

    monkeypatch.setattr(server.mcp, "run", _must_not_run)

    with pytest.raises(SystemExit) as excinfo:
        server.main()

    assert excinfo.value.code != 0
    err = capsys.readouterr().err
    assert "swc-workload not found" in err
    assert str(bad_path) in err


# ---------------------------------------------------------------------------
# REQ-03 — server.py registers tools by iterating TOOLS (no literal op names)
# ---------------------------------------------------------------------------


def test_server_module_does_not_hardcode_op_names_in_registration() -> None:
    """Static check on `server.py`: no literal op-name strings should
    appear anywhere outside the module docstring / server-name constant.

    Catches the regression where someone inlines
    ``mcp.tool()(tools.init)`` etc instead of iterating the registry.
    """
    from swc_workload_mcp import server as server_module

    source = Path(server_module.__file__).read_text()

    op_names = [
        "init",
        "exists",
        "find",
        "summary",
        "add",
        "rename",
        "delete",
        "reset",
        "start",
        "complete",
        "move",
    ]
    # `list` is excluded — too generic; checked via the registration loop
    # presence instead.

    # Strip the module docstring before scanning, since this test's own
    # module docstring may also mention these names.
    src_no_doc = source.split('"""', 2)[-1] if source.startswith('"""') else source

    for op in op_names:
        # Look for the literal as a quoted string — that's how an inline
        # registration would reference an op by name.
        assert f'"{op}"' not in src_no_doc, (
            f"server.py contains literal op name '{op}' in code — "
            "registration should iterate tools.TOOLS instead"
        )
        assert f"'{op}'" not in src_no_doc, (
            f"server.py contains literal op name '{op}' in code — "
            "registration should iterate tools.TOOLS instead"
        )

    # Positive check: the source contains an actual iteration over
    # ``tools.TOOLS``. Asserting on the loop pattern (rather than the
    # bare ``TOOLS`` token) catches a regression where someone removes
    # the loop but leaves a stray docstring/identifier reference behind.
    assert re.search(r"for\s+\w+\s+in\s+tools\.TOOLS", src_no_doc), (
        "server.py must iterate `tools.TOOLS` to register tools — "
        "the registration loop appears to be missing or refactored away"
    )


# ---------------------------------------------------------------------------
# REQ-04 — FastMCP server name is `swc-workload`
# ---------------------------------------------------------------------------


def test_fastmcp_instance_name_is_swc_workload() -> None:
    from swc_workload_mcp import server

    assert server.mcp.name == "swc-workload"


# ---------------------------------------------------------------------------
# Server version is surfaced via the MCP initialize handshake serverInfo
# ---------------------------------------------------------------------------


def test_server_version_is_set_on_low_level_server() -> None:
    """FastMCP's constructor doesn't expose `version`, so server.py sets
    it on the underlying low-level Server. Pin this so a future SDK
    refactor that renames `_mcp_server` or `version` doesn't silently
    revert to a missing serverInfo.version field in the handshake.
    """
    from swc_workload_mcp import server
    from swc_workload_mcp._version import __version__

    assert server.mcp._mcp_server.version == __version__


# ---------------------------------------------------------------------------
# REQ-05 — exactly 15 tools registered with the right flat names
# ---------------------------------------------------------------------------


EXPECTED_TOOL_NAMES = [
    "init",
    "exists",
    "list",
    "find",
    "summary",
    "get",
    "add",
    "update",
    "rename",
    "delete",
    "reset",
    "start",
    "complete",
    "move",
    "version",
]


def test_exactly_fifteen_tools_registered_with_flat_names(
    fake_cli: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swc_workload_mcp import server

    recorder = _RunRecorder()
    monkeypatch.setattr(server.mcp, "run", recorder)

    server.main()

    registered_names = sorted(t.name for t in server.mcp._tool_manager.list_tools())
    assert registered_names == sorted(EXPECTED_TOOL_NAMES)
    assert len(registered_names) == 15


# ---------------------------------------------------------------------------
# REQ-06 — __main__.main() delegates to server.main()
# ---------------------------------------------------------------------------


def test_dunder_main_delegates_to_server_main(monkeypatch: pytest.MonkeyPatch) -> None:
    from swc_workload_mcp import __main__ as dunder_main
    from swc_workload_mcp import server

    calls: list[int] = []

    def _recorder() -> None:
        calls.append(1)

    monkeypatch.setattr(server, "main", _recorder)

    dunder_main.main()

    assert calls == [1], "__main__.main() must delegate to server.main()"


# ---------------------------------------------------------------------------
# REQ-07 — startup CLI check reuses the bridge resolver
# ---------------------------------------------------------------------------


def test_startup_uses_bridge_resolver_not_shutil_which(
    fake_cli: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swc_workload_mcp import server

    recorder = _RunRecorder()
    monkeypatch.setattr(server.mcp, "run", recorder)

    call_count = {"n": 0}
    original = bridge.resolve_binary

    def _counting_resolve() -> str:
        call_count["n"] += 1
        return original()

    monkeypatch.setattr(bridge, "resolve_binary", _counting_resolve)

    server.main()

    assert call_count["n"] >= 1, "server.main() must call bridge.resolve_binary()"


def test_server_source_does_not_call_shutil_which() -> None:
    """Static check: ensure no direct shutil.which usage in server.py."""
    from swc_workload_mcp import server as server_module

    source = Path(server_module.__file__).read_text()
    assert "shutil.which" not in source, (
        "server.py must not call shutil.which directly — reuse bridge.resolve_binary"
    )
