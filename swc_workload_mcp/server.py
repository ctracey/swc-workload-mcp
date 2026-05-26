"""FastMCP server entry point for the swc-workload MCP service.

This module wires the package together:

1. Constructs a single module-level ``FastMCP("swc-workload")`` instance.
2. Registers every callable from :data:`swc_workload_mcp.tools.TOOLS`
   against the instance (no per-op knowledge here — the registry is
   iterated, not enumerated).
3. Exposes :func:`main`, which performs a fail-fast CLI presence check
   via :func:`swc_workload_mcp.bridge.resolve_binary` before starting
   the stdio transport.

If the CLI cannot be resolved, :func:`main` prints an actionable
message to stderr and exits non-zero. ``mcp.run()`` is never invoked in
that path — there is no graceful-degradation mode.

The console-script entry point declared in ``pyproject.toml`` and
``python -m swc_workload_mcp`` both reach :func:`main` via
:mod:`swc_workload_mcp.__main__`.
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from . import bridge, tools


SERVER_NAME = "swc-workload"
STDIO_TRANSPORT = "stdio"
CLI_REPO_URL = "https://github.com/ctracey/swc-workload-cli"


mcp = FastMCP(SERVER_NAME)


def _register_tools() -> None:
    """Register every callable in :data:`tools.TOOLS` against ``mcp``.

    Iterates the registry — no inline per-op knowledge. Adding or
    removing a tool changes only ``tools.py``; this loop does not need
    updating.
    """
    for fn in tools.TOOLS:
        mcp.add_tool(fn)


_register_tools()


def main() -> None:
    """Start the MCP server over stdio.

    Performs a fail-fast CLI presence check first: if the
    ``swc-workload`` binary cannot be resolved (no ``SWC_WORKLOAD_BIN``
    pointing at an executable AND not on ``PATH``), prints an
    actionable message to stderr and exits non-zero without touching
    the transport.

    On success, runs :meth:`FastMCP.run` with the stdio transport. The
    call blocks until the client disconnects.
    """
    try:
        bridge.resolve_binary()
    except bridge.CLINotFoundError as exc:
        searched = ", ".join(exc.searched_paths) if exc.searched_paths else "<none>"
        print(
            f"swc-workload not found (searched: {searched}). "
            f"Install from {CLI_REPO_URL} or set SWC_WORKLOAD_BIN to the binary path.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    mcp.run(STDIO_TRANSPORT)
