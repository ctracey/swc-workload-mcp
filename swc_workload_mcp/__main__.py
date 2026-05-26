"""Entry point for ``python -m swc_workload_mcp`` and the console script.

Thin delegation to :func:`swc_workload_mcp.server.main` so both the
``swc-workload-mcp`` console script (declared in ``pyproject.toml``)
and ``python -m swc_workload_mcp`` reach the same entry point.
"""

from __future__ import annotations

from . import server


def main() -> None:
    """Delegate to :func:`server.main`."""
    server.main()


if __name__ == "__main__":
    main()
