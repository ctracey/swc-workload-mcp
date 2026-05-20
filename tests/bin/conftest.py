"""Shared fixtures for swc_workload CLI tests.

Direct tests against `bin/swc_workload`. No git, no _meta.json — tests pass
`--workload <tmp-path>` explicitly. The CLI is invoked via subprocess so the
argparse surface (and the exit code / stderr behaviour) is covered
end-to-end.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
SWC_WORKLOAD = PLUGIN_ROOT / "bin" / "swc_workload"


def _run(cmd: list[str], cwd: Path | None = None, env: dict | None = None):
    final_env = os.environ.copy()
    if env:
        final_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=final_env,
        capture_output=True,
        text=True,
    )


def run_swc_workload(*args, workload: Path | None = None):
    """Invoke `bin/swc_workload` as a subprocess.

    `args` is the full arg list as passed on the command line — including
    `--workload` if the test wants to position it elsewhere. If `workload`
    is supplied, it is appended as `--workload <folder>` so most tests
    don't have to thread it through every call. The `--workload` contract
    is folder-path: swc_workload resolves <folder>/workload.json
    internally.
    """
    cmd = [sys.executable, str(SWC_WORKLOAD), *map(str, args)]
    if workload is not None:
        cmd.extend(["--workload", str(workload)])
    return _run(cmd)


@pytest.fixture
def swcw(tmp_path):
    """Return (run_fn, workload_json_path).

    `run_fn(*args)` invokes swc_workload against the per-test workload
    folder (pytest's `tmp_path`). The returned `workload` value is the
    expected workload.json path inside that folder (for tests that need to
    read/write the file directly after init runs). The folder exists; the
    workload.json is NOT pre-initialised — each test calls `init` (or seeds
    the file) as needed.
    """
    folder = tmp_path
    workload_json = folder / "workload.json"

    def run(*args):
        return run_swc_workload(*args, workload=folder)

    return run, workload_json


@pytest.fixture
def swcw_ready(swcw):
    """Like `swcw` but with `init` pre-run so the workload exists."""
    run, workload = swcw
    result = run("init")
    assert result.returncode == 0, f"init failed: {result.stderr}"
    return run, workload
