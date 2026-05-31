"""Subprocess bridge to the `swc-workload` CLI.

Resolves the CLI binary (env var override → PATH lookup) and invokes
it as a subprocess. Two entry points are provided:

- :func:`invoke` appends ``--json`` and returns the parsed JSON object.
- :func:`invoke_text` does not append ``--json`` and returns the raw
  stdout string (used by the ``list`` tool's default text output, which
  mirrors the CLI's tree-rendered format).

Three named exceptions surface the failure modes for the MCP tool
layer to map into structured tool errors.

This module is a thin pass-through — no per-op knowledge, no business
logic.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

__all__ = [
    "BridgeError",
    "CLINotFoundError",
    "CLIExecutionError",
    "CLIResponseError",
    "invoke",
    "invoke_text",
    "resolve_binary",
]

CLI_BINARY_NAME = "swc-workload"
ENV_VAR = "SWC_WORKLOAD_BIN"
_STDOUT_TRUNCATION_LIMIT = 500


class BridgeError(Exception):
    """Base class for all subprocess-bridge failures."""


class CLINotFoundError(BridgeError):
    """Raised when the CLI binary cannot be resolved.

    Attributes
    ----------
    searched_paths:
        The paths/names that were checked while resolving the binary —
        either a single env-var path that didn't resolve, or the binary
        name searched on PATH.
    """

    def __init__(self, searched_paths: list[str]) -> None:
        self.searched_paths = list(searched_paths)
        joined = ", ".join(self.searched_paths) if self.searched_paths else "<none>"
        super().__init__(
            f"swc-workload CLI not found (searched: {joined})"
        )


class CLIExecutionError(BridgeError):
    """Raised when the CLI exits with a non-zero code.

    Attributes
    ----------
    exit_code:
        The subprocess exit code.
    stderr:
        Captured stderr from the subprocess (may be empty).
    """

    def __init__(self, exit_code: int, stderr: str) -> None:
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(
            f"swc-workload exited with code {exit_code}: {stderr.strip()!r}"
        )


class CLIResponseError(BridgeError):
    """Raised when CLI stdout cannot be parsed as JSON.

    Attributes
    ----------
    truncated_stdout:
        A truncated copy of the raw stdout for diagnostics. Capped at
        ``_STDOUT_TRUNCATION_LIMIT`` characters with an ellipsis marker
        if the original was longer.
    """

    def __init__(self, raw_stdout: str) -> None:
        self.truncated_stdout = _truncate(raw_stdout)
        super().__init__(
            f"swc-workload stdout was not valid JSON: {self.truncated_stdout!r}"
        )


def _truncate(text: str) -> str:
    if len(text) <= _STDOUT_TRUNCATION_LIMIT:
        return text
    return text[:_STDOUT_TRUNCATION_LIMIT] + "..."


def resolve_binary() -> str:
    """Resolve the CLI binary path.

    Returns the path to use for ``subprocess.run``. Raises
    :class:`CLINotFoundError` if no usable binary is found.

    Resolution order:

    1. ``SWC_WORKLOAD_BIN`` env var — if set, must point at an
       executable file or :class:`CLINotFoundError` is raised.
    2. ``shutil.which("swc-workload")`` — first match on ``PATH``.

    This is the single source of truth for binary resolution: the
    server's startup presence check (work item 2.4) and per-tool
    invocations (via :func:`invoke`) both use it.
    """
    env_value = os.environ.get(ENV_VAR)
    if env_value:
        if os.path.isfile(env_value) and os.access(env_value, os.X_OK):
            return env_value
        raise CLINotFoundError([env_value])

    resolved = shutil.which(CLI_BINARY_NAME)
    if resolved:
        return resolved

    raise CLINotFoundError([CLI_BINARY_NAME])


def _run(argv: list[str]) -> str:
    """Run ``argv`` and return stdout on success, raising on failures.

    Shared by :func:`invoke` and :func:`invoke_text`. The two differ
    only in whether ``--json`` is in ``argv`` and how stdout is then
    interpreted.
    """
    completed = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        raise CLIExecutionError(completed.returncode, completed.stderr)

    return completed.stdout


def invoke(op: str, args: list[str]) -> Any:
    """Invoke ``swc-workload <op> <args> --json`` and return parsed JSON.

    Parameters
    ----------
    op:
        The CLI op name (e.g. ``"list"``, ``"add"``).
    args:
        Additional args forwarded verbatim to the CLI. Includes
        op-specific positional args and flags such as ``--workload``.
        The bridge does not validate or interpret these.

    Returns
    -------
    Any
        The parsed JSON object emitted on stdout.

    Raises
    ------
    CLINotFoundError
        If the CLI binary cannot be resolved.
    CLIExecutionError
        If the CLI exits with a non-zero code.
    CLIResponseError
        If the CLI exits 0 but stdout is not valid JSON.
    """
    binary = resolve_binary()
    stdout = _run([binary, op, *args, "--json"])

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise CLIResponseError(stdout) from exc


def invoke_text(op: str, args: list[str]) -> str:
    """Invoke ``swc-workload <op> <args>`` and return raw stdout text.

    Same plumbing as :func:`invoke` but without ``--json`` — used to
    obtain the CLI's human-readable output (e.g. the ``list`` tool's
    tree render).

    Returns
    -------
    str
        Raw stdout emitted by the CLI.

    Raises
    ------
    CLINotFoundError
        If the CLI binary cannot be resolved.
    CLIExecutionError
        If the CLI exits with a non-zero code.
    """
    binary = resolve_binary()
    return _run([binary, op, *args])
