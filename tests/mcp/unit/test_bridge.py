"""Tests for the subprocess bridge (work item 2.1).

Each test corresponds to a Gherkin scenario in
`.swc/mcp/workitems/2.1/specs.md`. Tests use real subprocesses against a
small stub `swc-workload` Python script written to a tmp directory.
"""

from __future__ import annotations

import json
import stat
import sys
import textwrap
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Stub CLI helpers
# ---------------------------------------------------------------------------


def _write_stub(
    dir_path: Path,
    *,
    name: str = "swc-workload",
    stdout: str = "{}",
    stderr: str = "",
    exit_code: int = 0,
    record_argv: bool = False,
) -> Path:
    """Write an executable Python stub that emits canned output.

    The stub is parameterised by environment variables so the test sets
    the desired behaviour just before invoking the bridge — no per-test
    script rewrites needed.
    """
    stub_path = dir_path / name
    script = textwrap.dedent(
        """\
        #!{python}
        import json
        import os
        import sys

        if os.environ.get("STUB_RECORD_ARGV"):
            record_path = os.environ["STUB_RECORD_ARGV"]
            with open(record_path, "w") as fh:
                json.dump(sys.argv, fh)

        sys.stdout.write(os.environ.get("STUB_STDOUT", ""))
        sys.stderr.write(os.environ.get("STUB_STDERR", ""))
        sys.exit(int(os.environ.get("STUB_EXIT", "0")))
        """
    ).format(python=sys.executable)
    stub_path.write_text(script)
    stub_path.chmod(stub_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return stub_path


@pytest.fixture
def stub_dir(tmp_path: Path) -> Path:
    """A clean directory for stub binaries — one per test."""
    d = tmp_path / "bin"
    d.mkdir()
    return d


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear env vars the bridge consults so tests start from a clean slate."""
    monkeypatch.delenv("SWC_WORKLOAD_BIN", raising=False)
    monkeypatch.delenv("STUB_STDOUT", raising=False)
    monkeypatch.delenv("STUB_STDERR", raising=False)
    monkeypatch.delenv("STUB_EXIT", raising=False)
    monkeypatch.delenv("STUB_RECORD_ARGV", raising=False)
    # Hide any real `swc-workload` on PATH so PATH-lookup tests are deterministic.
    monkeypatch.setenv("PATH", str(Path("/nonexistent")))


# ---------------------------------------------------------------------------
# REQ-01 — env var override uses the provided binary path
# ---------------------------------------------------------------------------


def test_env_var_override_uses_provided_binary(
    stub_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swc_workload_mcp import bridge

    stub = _write_stub(stub_dir)
    argv_record = stub_dir / "argv.json"
    monkeypatch.setenv("SWC_WORKLOAD_BIN", str(stub))
    monkeypatch.setenv("STUB_STDOUT", '{"ok": true, "items": []}')
    monkeypatch.setenv("STUB_RECORD_ARGV", str(argv_record))

    result = bridge.invoke("list", [])

    assert result == {"ok": True, "items": []}
    recorded = json.loads(argv_record.read_text())
    # The stub was launched at the env-var path — sys.argv[0] reflects it.
    assert recorded[0] == str(stub)


# ---------------------------------------------------------------------------
# REQ-02 — PATH lookup is used when env var is unset
# ---------------------------------------------------------------------------


def test_path_lookup_when_env_var_unset(
    stub_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swc_workload_mcp import bridge

    stub = _write_stub(stub_dir)
    argv_record = stub_dir / "argv.json"
    # env var is unset (autouse fixture cleared it)
    monkeypatch.setenv("PATH", str(stub_dir))
    monkeypatch.setenv("STUB_STDOUT", '{"ok": true}')
    monkeypatch.setenv("STUB_RECORD_ARGV", str(argv_record))

    result = bridge.invoke("list", [])

    assert result == {"ok": True}
    recorded = json.loads(argv_record.read_text())
    assert recorded[0] == str(stub)


# ---------------------------------------------------------------------------
# REQ-03 — invocation passes op, args, and --json
# ---------------------------------------------------------------------------


def test_invocation_passes_op_args_and_json_flag(
    stub_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swc_workload_mcp import bridge

    stub = _write_stub(stub_dir)
    argv_record = stub_dir / "argv.json"
    monkeypatch.setenv("SWC_WORKLOAD_BIN", str(stub))
    monkeypatch.setenv("STUB_STDOUT", "{}")
    monkeypatch.setenv("STUB_RECORD_ARGV", str(argv_record))

    bridge.invoke("add", ["new item", "--workload", "/tmp/w"])

    recorded = json.loads(argv_record.read_text())
    assert recorded == [
        str(stub),
        "add",
        "new item",
        "--workload",
        "/tmp/w",
        "--json",
    ]


# ---------------------------------------------------------------------------
# REQ-04 — successful run returns parsed JSON
# ---------------------------------------------------------------------------


def test_successful_run_returns_parsed_json(
    stub_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swc_workload_mcp import bridge

    stub = _write_stub(stub_dir)
    monkeypatch.setenv("SWC_WORKLOAD_BIN", str(stub))
    monkeypatch.setenv("STUB_STDOUT", '{"ok": true, "items": []}')

    result = bridge.invoke("list", [])

    assert result == {"ok": True, "items": []}


# ---------------------------------------------------------------------------
# REQ-05a — missing CLI everywhere raises CLINotFoundError
# ---------------------------------------------------------------------------


def test_missing_cli_raises_cli_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swc_workload_mcp import bridge

    # env var is unset (autouse fixture cleared it); PATH points at an empty
    # directory so shutil.which finds nothing.
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))

    with pytest.raises(bridge.CLINotFoundError) as excinfo:
        bridge.invoke("list", [])

    assert "swc-workload" in excinfo.value.searched_paths


# ---------------------------------------------------------------------------
# REQ-05b — env var pointing nowhere raises CLINotFoundError
# ---------------------------------------------------------------------------


def test_env_var_pointing_nowhere_raises_cli_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swc_workload_mcp import bridge

    bad_path = tmp_path / "does-not-exist"
    monkeypatch.setenv("SWC_WORKLOAD_BIN", str(bad_path))

    with pytest.raises(bridge.CLINotFoundError) as excinfo:
        bridge.invoke("list", [])

    assert str(bad_path) in excinfo.value.searched_paths


# ---------------------------------------------------------------------------
# REQ-06 — non-zero exit raises CLIExecutionError
# ---------------------------------------------------------------------------


def test_non_zero_exit_raises_cli_execution_error(
    stub_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swc_workload_mcp import bridge

    stub = _write_stub(stub_dir)
    monkeypatch.setenv("SWC_WORKLOAD_BIN", str(stub))
    monkeypatch.setenv("STUB_EXIT", "2")
    monkeypatch.setenv("STUB_STDERR", "workload not initialised\n")

    with pytest.raises(bridge.CLIExecutionError) as excinfo:
        bridge.invoke("list", [])

    assert excinfo.value.exit_code == 2
    assert "workload not initialised" in excinfo.value.stderr


# ---------------------------------------------------------------------------
# REQ-07 — unparseable stdout raises CLIResponseError
# ---------------------------------------------------------------------------


def test_unparseable_stdout_raises_cli_response_error(
    stub_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swc_workload_mcp import bridge

    stub = _write_stub(stub_dir)
    monkeypatch.setenv("SWC_WORKLOAD_BIN", str(stub))
    monkeypatch.setenv("STUB_STDOUT", "not json {{{")

    with pytest.raises(bridge.CLIResponseError) as excinfo:
        bridge.invoke("list", [])

    assert "not json {{{" in excinfo.value.truncated_stdout


def test_cli_response_error_truncates_long_stdout(
    stub_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A long unparseable stdout is truncated with an ellipsis marker."""
    from swc_workload_mcp import bridge

    long_output = "x" * 1000
    stub = _write_stub(stub_dir)
    monkeypatch.setenv("SWC_WORKLOAD_BIN", str(stub))
    monkeypatch.setenv("STUB_STDOUT", long_output)

    with pytest.raises(bridge.CLIResponseError) as excinfo:
        bridge.invoke("list", [])

    truncated = excinfo.value.truncated_stdout
    assert truncated.endswith("...")
    # 500 chars + 3 char ellipsis marker
    assert len(truncated) == 503


# ---------------------------------------------------------------------------
# invoke_text — alternate entry point that does NOT append --json and
# returns raw stdout text (used by the list tool's default text mode).
# ---------------------------------------------------------------------------


def test_invoke_text_does_not_append_json_flag(
    stub_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swc_workload_mcp import bridge

    stub = _write_stub(stub_dir)
    argv_record = stub_dir / "argv.json"
    monkeypatch.setenv("SWC_WORKLOAD_BIN", str(stub))
    monkeypatch.setenv("STUB_STDOUT", "tree render\n")
    monkeypatch.setenv("STUB_RECORD_ARGV", str(argv_record))

    bridge.invoke_text("list", ["--workload", "/tmp/w"])

    recorded = json.loads(argv_record.read_text())
    assert recorded == [str(stub), "list", "--workload", "/tmp/w"]
    assert "--json" not in recorded


def test_invoke_text_returns_raw_stdout_string(
    stub_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swc_workload_mcp import bridge

    stub = _write_stub(stub_dir)
    monkeypatch.setenv("SWC_WORKLOAD_BIN", str(stub))
    monkeypatch.setenv("STUB_STDOUT", "• 1 a\n• 2 b\n")

    result = bridge.invoke_text("list", [])

    assert result == "• 1 a\n• 2 b\n"


def test_invoke_text_non_zero_exit_raises_cli_execution_error(
    stub_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from swc_workload_mcp import bridge

    stub = _write_stub(stub_dir)
    monkeypatch.setenv("SWC_WORKLOAD_BIN", str(stub))
    monkeypatch.setenv("STUB_EXIT", "2")
    monkeypatch.setenv("STUB_STDERR", "workload not initialised\n")

    with pytest.raises(bridge.CLIExecutionError) as excinfo:
        bridge.invoke_text("list", [])

    assert excinfo.value.exit_code == 2
    assert "workload not initialised" in excinfo.value.stderr


def test_invoke_text_does_not_parse_stdout(
    stub_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raw text mode must not raise CLIResponseError on non-JSON stdout."""
    from swc_workload_mcp import bridge

    stub = _write_stub(stub_dir)
    monkeypatch.setenv("SWC_WORKLOAD_BIN", str(stub))
    monkeypatch.setenv("STUB_STDOUT", "not json {{{")

    result = bridge.invoke_text("list", [])

    assert result == "not json {{{"
