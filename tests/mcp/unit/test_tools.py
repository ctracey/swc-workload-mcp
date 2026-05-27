"""Tests for the MCP tool wrappers (work item 2.3).

Each test corresponds to a Gherkin scenario in
`.swc/mcp/workitems/2.3/specs.md`. Tests unit-test each tool callable
directly by stubbing `bridge.invoke` and asserting:

- argv translation (positional + optional flags) — REQ-01, REQ-02
- error mapping for each `BridgeError` subclass — REQ-03, REQ-04, REQ-05
- the module exposes exactly the 12 expected tools — REQ-06
- each tool's signature matches the CLI op's documented args — REQ-07

Integration-level tests against a real CLI + temp workload are out of
scope here (work item 3.2).
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

import pytest

from mcp.server.fastmcp.exceptions import ToolError

from swc_workload_mcp import bridge, tools


# ---------------------------------------------------------------------------
# Bridge stubbing helpers
# ---------------------------------------------------------------------------


class _BridgeRecorder:
    """Records calls to a stub `bridge.invoke` and returns a canned result."""

    def __init__(self, result: Any = None, *, raises: Exception | None = None) -> None:
        self.result = result
        self.raises = raises
        self.calls: list[tuple[str, list[str]]] = []

    def __call__(self, op: str, args: list[str]) -> Any:
        self.calls.append((op, list(args)))
        if self.raises is not None:
            raise self.raises
        return self.result


@pytest.fixture
def stub_bridge(monkeypatch: pytest.MonkeyPatch):
    """Patch `tools._invoke`'s underlying `bridge.invoke` with a recorder."""

    def _install(result: Any = None, *, raises: Exception | None = None) -> _BridgeRecorder:
        recorder = _BridgeRecorder(result, raises=raises)
        monkeypatch.setattr(tools.bridge, "invoke", recorder)
        return recorder

    return _install


# ---------------------------------------------------------------------------
# REQ-01 — happy path: argv translation + result passthrough
# ---------------------------------------------------------------------------


def test_list_tool_returns_parsed_json(stub_bridge) -> None:
    recorder = stub_bridge(result={"items": []})

    result = tools.list(workload="/tmp/wl")

    assert result == {"items": []}
    assert recorder.calls == [("list", ["--workload", "/tmp/wl"])]


def test_add_tool_forwards_positional_args_alongside_flags(stub_bridge) -> None:
    recorder = stub_bridge(result={"id": "1.1"})

    result = tools.add(workload="/tmp/wl", title="Foo")

    assert result == {"id": "1.1"}
    assert recorder.calls == [("add", ["--workload", "/tmp/wl", "Foo"])]


# ---------------------------------------------------------------------------
# REQ-02 — optional kwarg presence/absence controls flag in argv
# ---------------------------------------------------------------------------


def test_optional_kwarg_omitted_flag_absent(stub_bridge) -> None:
    recorder = stub_bridge(result={})

    tools.list(workload="/tmp/wl")

    op, args = recorder.calls[0]
    assert "--filter" not in args


def test_optional_kwarg_set_flag_present(stub_bridge) -> None:
    recorder = stub_bridge(result={})

    tools.list(workload="/tmp/wl", filter="status:done")

    op, args = recorder.calls[0]
    assert "--filter" in args
    assert args[args.index("--filter") + 1] == "status:done"


# ---------------------------------------------------------------------------
# REQ-03 — CLINotFoundError → ToolError with install hint
# ---------------------------------------------------------------------------


def test_cli_not_found_maps_to_tool_error_with_install_hint(stub_bridge) -> None:
    stub_bridge(raises=bridge.CLINotFoundError(searched_paths=["swc-workload"]))

    with pytest.raises(ToolError) as excinfo:
        tools.list(workload="/tmp/wl")

    msg = str(excinfo.value)
    assert "swc-workload not found" in msg
    assert "https://github.com/ctracey/swc-workload-cli" in msg
    assert "SWC_WORKLOAD_BIN" in msg


# ---------------------------------------------------------------------------
# REQ-04 — CLIExecutionError → ToolError with exit code + stderr
# ---------------------------------------------------------------------------


def test_cli_execution_error_maps_to_tool_error_with_exit_and_stderr(stub_bridge) -> None:
    stub_bridge(raises=bridge.CLIExecutionError(exit_code=2, stderr="no such ref: 9.9"))

    with pytest.raises(ToolError) as excinfo:
        tools.list(workload="/tmp/wl")

    msg = str(excinfo.value)
    assert "exit 2" in msg
    assert "no such ref: 9.9" in msg


# ---------------------------------------------------------------------------
# REQ-05 — CLIResponseError → ToolError with version-mismatch hint
# ---------------------------------------------------------------------------


def test_cli_response_error_maps_to_tool_error_with_version_mismatch_hint(
    stub_bridge,
) -> None:
    stub_bridge(raises=bridge.CLIResponseError(raw_stdout="not json blah"))

    with pytest.raises(ToolError) as excinfo:
        tools.list(workload="/tmp/wl")

    msg = str(excinfo.value)
    assert "not json blah" in msg
    assert "CLI/MCP version mismatch" in msg


# ---------------------------------------------------------------------------
# REQ-06 — module exposes exactly the 12 expected tools
# ---------------------------------------------------------------------------


EXPECTED_TOOLS = [
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


def test_module_exposes_exactly_the_12_expected_tools() -> None:
    registry_names = [fn.__name__ for fn in tools.TOOLS]
    assert registry_names == EXPECTED_TOOLS


def test_each_expected_name_is_a_callable_on_the_module() -> None:
    for name in EXPECTED_TOOLS:
        fn = getattr(tools, name, None)
        assert callable(fn), f"tools.{name} must be a callable"


# ---------------------------------------------------------------------------
# REQ-07 — each tool's kwargs correspond 1:1 to the CLI op's --help
# ---------------------------------------------------------------------------


# Derived from `swc-workload <op> --help`. `workload` is required by every op.
EXPECTED_SIGNATURES: dict[str, dict[str, Any]] = {
    "init": {
        "required": ["workload"],
        "optional": [],
    },
    "exists": {
        "required": ["workload"],
        "optional": [],
    },
    "list": {
        "required": ["workload"],
        "optional": ["ref", "filter", "exclude", "no_ids"],
    },
    "find": {
        "required": ["workload", "keyword"],
        "optional": [],
    },
    "summary": {
        "required": ["workload"],
        "optional": [],
    },
    "add": {
        "required": ["workload", "title"],
        "optional": ["placement", "ref"],
    },
    "rename": {
        "required": ["workload", "ref", "title"],
        "optional": [],
    },
    "delete": {
        "required": ["workload", "ref"],
        "optional": [],
    },
    "reset": {
        "required": ["workload", "ref"],
        "optional": [],
    },
    "start": {
        "required": ["workload", "ref"],
        "optional": [],
    },
    "complete": {
        "required": ["workload", "ref"],
        "optional": [],
    },
    "move": {
        # `ref direction|to [target]` — `direction` carries either a
        # relative direction (up|down|top|bottom) or the literal "to".
        "required": ["workload", "ref", "direction"],
        "optional": ["target"],
    },
}


@pytest.mark.parametrize("op", EXPECTED_TOOLS)
def test_tool_signature_matches_expected(op: str) -> None:
    expected = EXPECTED_SIGNATURES[op]
    fn = getattr(tools, op)
    sig = inspect.signature(fn)
    params = sig.parameters

    required = [n for n, p in params.items() if p.default is inspect.Parameter.empty]
    optional = [n for n, p in params.items() if p.default is not inspect.Parameter.empty]

    assert required == expected["required"], f"{op} required kwargs mismatch"
    assert optional == expected["optional"], f"{op} optional kwargs mismatch"


# ---------------------------------------------------------------------------
# Per-op argv translation — spot-check the trickier shapes
# ---------------------------------------------------------------------------


def test_init_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"ok": True})

    tools.init(workload="/tmp/wl")

    assert recorder.calls == [("init", ["--workload", "/tmp/wl"])]


def test_exists_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"exists": True})

    tools.exists(workload="/tmp/wl")

    assert recorder.calls == [("exists", ["--workload", "/tmp/wl"])]


def test_find_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"matches": []})

    tools.find(workload="/tmp/wl", keyword="bug")

    assert recorder.calls == [("find", ["--workload", "/tmp/wl", "bug"])]


def test_summary_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"total": 0})

    tools.summary(workload="/tmp/wl")

    assert recorder.calls == [("summary", ["--workload", "/tmp/wl"])]


def test_list_tool_with_all_optional_kwargs(stub_bridge) -> None:
    recorder = stub_bridge(result={})

    tools.list(
        workload="/tmp/wl",
        ref="2.3",
        filter="status:done",
        exclude="status:wip",
        no_ids=True,
    )

    op, args = recorder.calls[0]
    assert op == "list"
    # --workload, --filter, --exclude, --no-ids, then positional ref.
    assert args[0] == "--workload"
    assert args[1] == "/tmp/wl"
    assert "--filter" in args and args[args.index("--filter") + 1] == "status:done"
    assert "--exclude" in args and args[args.index("--exclude") + 1] == "status:wip"
    assert "--no-ids" in args
    # ref appears as the trailing positional.
    assert args[-1] == "2.3"


def test_list_tool_no_ids_false_does_not_emit_flag(stub_bridge) -> None:
    """A False no_ids must not emit `--no-ids` (boolean flag semantics)."""
    recorder = stub_bridge(result={})

    tools.list(workload="/tmp/wl", no_ids=False)

    op, args = recorder.calls[0]
    assert "--no-ids" not in args


def test_add_tool_top_level(stub_bridge) -> None:
    recorder = stub_bridge(result={"id": "1"})

    tools.add(workload="/tmp/wl", title="Foo")

    assert recorder.calls == [("add", ["--workload", "/tmp/wl", "Foo"])]


def test_add_tool_to_parent(stub_bridge) -> None:
    recorder = stub_bridge(result={"id": "1.1"})

    tools.add(workload="/tmp/wl", title="Foo", placement="to", ref="1")

    assert recorder.calls == [("add", ["--workload", "/tmp/wl", "Foo", "to", "1"])]


def test_add_tool_at_position(stub_bridge) -> None:
    recorder = stub_bridge(result={"id": "2"})

    tools.add(workload="/tmp/wl", title="Foo", placement="at", ref="2")

    assert recorder.calls == [("add", ["--workload", "/tmp/wl", "Foo", "at", "2"])]


def test_add_tool_forwards_ref_even_when_placement_is_missing(stub_bridge) -> None:
    """ref must reach the CLI even if placement is None — otherwise a buggy
    or partial client (e.g. an MCP UI that nulls one optional but sets the
    other) silently lands the item at top level instead of surfacing the
    CLI's "expected 'to <parent>' or 'at <position>'" error.
    """
    recorder = stub_bridge(result={"id": "1"})

    tools.add(workload="/tmp/wl", title="Foo", ref="1")

    assert recorder.calls == [("add", ["--workload", "/tmp/wl", "Foo", "1"])]


def test_rename_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"ok": True})

    tools.rename(workload="/tmp/wl", ref="2.3", title="New title")

    assert recorder.calls == [
        ("rename", ["--workload", "/tmp/wl", "2.3", "New title"])
    ]


def test_delete_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"ok": True})

    tools.delete(workload="/tmp/wl", ref="2.3")

    assert recorder.calls == [("delete", ["--workload", "/tmp/wl", "2.3"])]


def test_reset_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"status": "not-started"})

    tools.reset(workload="/tmp/wl", ref="2.3")

    assert recorder.calls == [("reset", ["--workload", "/tmp/wl", "2.3"])]


def test_start_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"status": "in-progress"})

    tools.start(workload="/tmp/wl", ref="2.3")

    assert recorder.calls == [("start", ["--workload", "/tmp/wl", "2.3"])]


def test_complete_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"status": "done"})

    tools.complete(workload="/tmp/wl", ref="2.3")

    assert recorder.calls == [("complete", ["--workload", "/tmp/wl", "2.3"])]


def test_move_tool_relative(stub_bridge) -> None:
    recorder = stub_bridge(result={"ok": True})

    tools.move(workload="/tmp/wl", ref="2.3", direction="up")

    assert recorder.calls == [("move", ["--workload", "/tmp/wl", "2.3", "up"])]


def test_move_tool_absolute(stub_bridge) -> None:
    recorder = stub_bridge(result={"ok": True})

    tools.move(workload="/tmp/wl", ref="2.3", direction="to", target="3.2")

    assert recorder.calls == [
        ("move", ["--workload", "/tmp/wl", "2.3", "to", "3.2"])
    ]


# ---------------------------------------------------------------------------
# Error mapping is uniform across tools — spot-check a non-list tool
# ---------------------------------------------------------------------------


def test_error_mapping_applies_to_every_tool(stub_bridge) -> None:
    stub_bridge(raises=bridge.CLINotFoundError(searched_paths=["swc-workload"]))

    for name in EXPECTED_TOOLS:
        fn = getattr(tools, name)
        with pytest.raises(ToolError):
            # Pass a minimal kwarg set — every tool requires `workload`.
            # Required positionals for other ops use placeholder strings;
            # bridge.invoke is stubbed so values are inert.
            sig = inspect.signature(fn)
            kwargs: dict[str, Any] = {}
            for pname, p in sig.parameters.items():
                if p.default is inspect.Parameter.empty:
                    kwargs[pname] = "x"
            fn(**kwargs)
