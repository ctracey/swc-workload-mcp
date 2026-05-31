"""MCP tool wrappers — one per `swc-workload` CLI op.

Each tool is a thin typed callable that:

1. Translates its kwargs into the CLI's argv (positional args in CLI
   order, then ``--flag value`` for each set optional kwarg).
2. Delegates to :func:`swc_workload_mcp.bridge.invoke`.
3. Re-raises any :class:`~swc_workload_mcp.bridge.BridgeError` subclass
   as a FastMCP :class:`~mcp.server.fastmcp.exceptions.ToolError` with
   an actionable hint.

The module exports a :data:`TOOLS` registry — a list of the 12
callables — which the FastMCP server (work item 2.4) iterates over to
register each tool against the server instance.

Tool names are flat (e.g. ``add``, not ``workload_add``) because the
MCP client namespaces them by server name. The ``list`` tool shadows
the builtin ``list`` within this module — acceptable per the solution
design; no built-in ``list`` usage is needed here. The alias
:data:`_StrList` is used for type hints so that ``list[str]`` does not
resolve to the rebound function in deferred-annotation contexts.
"""

from __future__ import annotations

import builtins
from typing import Any

from mcp.server.fastmcp.exceptions import ToolError

from . import bridge


__all__ = [
    "TOOLS",
    "init",
    "exists",
    "list",
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


CLI_REPO_URL = "https://github.com/ctracey/swc-workload-cli"

# Type alias used inside this module to avoid the ``list`` rebinding
# below. ``list[str]`` would resolve to the rebound function under
# ``typing.get_type_hints``.
_StrList = builtins.list[str]


# ---------------------------------------------------------------------------
# Private helpers — shared error mapping + flag construction
# ---------------------------------------------------------------------------


def _invoke(op: str, args: _StrList) -> Any:
    """Call the bridge and map ``BridgeError`` subclasses to ``ToolError``.

    Every tool body delegates to this helper (or :func:`_invoke_text`
    for ops that want the CLI's raw text output). Centralising the
    mapping keeps tool bodies to argv assembly + a single call,
    satisfying the thin-wrapper invariant (REQ-08).
    """
    try:
        return bridge.invoke(op, args)
    except bridge.CLINotFoundError as exc:
        raise ToolError(
            f"swc-workload not found (searched: {', '.join(exc.searched_paths)}). "
            f"Install from {CLI_REPO_URL} or set SWC_WORKLOAD_BIN to the binary path."
        ) from exc
    except bridge.CLIExecutionError as exc:
        raise ToolError(
            f"swc-workload {op} failed (exit {exc.exit_code}): {exc.stderr.strip()}"
        ) from exc
    except bridge.CLIResponseError as exc:
        raise ToolError(
            f"swc-workload {op} returned unparseable output "
            f"(truncated): {exc.truncated_stdout}. "
            f"Likely a CLI/MCP version mismatch."
        ) from exc


def _invoke_text(op: str, args: _StrList) -> str:
    """Like :func:`_invoke` but returns the CLI's raw stdout text.

    Only the not-found and non-zero-exit failures apply here — the
    text path never tries to parse JSON, so ``CLIResponseError``
    cannot fire.
    """
    try:
        return bridge.invoke_text(op, args)
    except bridge.CLINotFoundError as exc:
        raise ToolError(
            f"swc-workload not found (searched: {', '.join(exc.searched_paths)}). "
            f"Install from {CLI_REPO_URL} or set SWC_WORKLOAD_BIN to the binary path."
        ) from exc
    except bridge.CLIExecutionError as exc:
        raise ToolError(
            f"swc-workload {op} failed (exit {exc.exit_code}): {exc.stderr.strip()}"
        ) from exc


def _flag(name: str, value: Any) -> _StrList:
    """Render ``--name value`` if value is set, else an empty list.

    A value is considered set when it is not ``None``. Boolean flags
    are handled separately by :func:`_bool_flag`.
    """
    if value is None:
        return []
    return [f"--{name}", str(value)]


def _bool_flag(name: str, value: bool | None) -> _StrList:
    """Render a standalone ``--name`` switch if ``value`` is truthy."""
    if value:
        return [f"--{name}"]
    return []


# ---------------------------------------------------------------------------
# Tool definitions — one per CLI op
# ---------------------------------------------------------------------------


def init(workload: str) -> Any:
    """Initialise a fresh, empty workload tree at the given folder.

    Fails if a workload is already present.
    """
    args = ["--workload", workload]
    return _invoke("init", args)


def exists(workload: str) -> Any:
    """Check whether a workload is initialised at the given folder.

    Lenient: returns ``false`` (never errors) for missing folders or
    missing ``workload.json``.
    """
    args = ["--workload", workload]
    return _invoke("exists", args)


def list(  # noqa: A001 — intentional shadowing of builtin, see module docstring
    workload: str,
    ref: str | None = None,
    filter: str | None = None,  # noqa: A002 — matches CLI flag name
    exclude: str | None = None,
    no_ids: bool | None = None,
    json: bool | None = None,
) -> Any:
    """Display the workload tree, optionally scoped to a ref and filtered.

    - ``ref`` — optional item reference (number or hash). When given,
      renders just that item and its descendants.
    - ``filter`` / ``exclude`` — ``key:val[,val…]`` filter expressions
      (supported keys: ``status``).
    - ``no_ids`` — hide hash IDs from output (shown by default).
    - ``json`` — when true, return the parsed JSON tree. Default is the
      CLI's human-readable tree render (string).
    """
    args = ["--workload", workload]
    args += _flag("filter", filter)
    args += _flag("exclude", exclude)
    args += _bool_flag("no-ids", no_ids)
    if ref is not None:
        args.append(ref)
    if json:
        return _invoke("list", args)
    return _invoke_text("list", args)


def find(workload: str, keyword: str) -> Any:
    """Find work items whose title contains ``keyword`` (case-insensitive)."""
    args = ["--workload", workload, keyword]
    return _invoke("find", args)


def summary(workload: str) -> Any:
    """Emit total / done / progress percentage for the workload."""
    args = ["--workload", workload]
    return _invoke("summary", args)


def add(
    workload: str,
    title: str,
    placement: str | None = None,
    ref: str | None = None,
) -> Any:
    """Add a work item to the workload.

    - ``add(title=...)`` — append at top level.
    - ``add(title=..., placement="to", ref="<parent>")`` — append as the
      last child of ``<parent>``.
    - ``add(title=..., placement="at", ref="<position>")`` — insert at
      that position; siblings shift down.
    """
    args = ["--workload", workload, title]
    if placement is not None:
        args.append(placement)
    if ref is not None:
        args.append(ref)
    return _invoke("add", args)


def rename(workload: str, ref: str, title: str) -> Any:
    """Rename a work item. ID, status, parent, and position are preserved."""
    args = ["--workload", workload, ref, title]
    return _invoke("rename", args)


def delete(workload: str, ref: str) -> Any:
    """Delete a work item and all of its descendants."""
    args = ["--workload", workload, ref]
    return _invoke("delete", args)


def reset(workload: str, ref: str) -> Any:
    """Mark a work item as not-started (re-opens done items)."""
    args = ["--workload", workload, ref]
    return _invoke("reset", args)


def start(workload: str, ref: str) -> Any:
    """Mark a work item as in-progress.

    A done item is silently preserved (file unchanged, exits 0).
    """
    args = ["--workload", workload, ref]
    return _invoke("start", args)


def complete(workload: str, ref: str) -> Any:
    """Mark a work item as done. Parent ancestors re-roll."""
    args = ["--workload", workload, ref]
    return _invoke("complete", args)


def move(
    workload: str,
    ref: str,
    direction: str,
    target: str | None = None,
) -> Any:
    """Move a work item.

    Two forms:

    - relative: ``direction`` is one of ``up|down|top|bottom``;
      ``target`` must be omitted.
    - absolute: ``direction="to"`` plus ``target=<position>``.
    """
    args = ["--workload", workload, ref, direction]
    if target is not None:
        args.append(target)
    return _invoke("move", args)


# ---------------------------------------------------------------------------
# Registry — order matches the CLI op order documented in workload.md
# ---------------------------------------------------------------------------


TOOLS = [
    init,
    exists,
    list,
    find,
    summary,
    add,
    rename,
    delete,
    reset,
    start,
    complete,
    move,
]
