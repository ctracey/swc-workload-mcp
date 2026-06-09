"""Tests for the MCP tool wrappers (work item 2.3).

Each test corresponds to a Gherkin scenario in
`.swc/mcp/workitems/2.3/specs.md`. Tests unit-test each tool callable
directly by stubbing `bridge.invoke` and asserting:

- argv translation (positional + optional flags) — REQ-01, REQ-02
- error mapping for each `BridgeError` subclass — REQ-03, REQ-04, REQ-05
- the module exposes exactly the 14 expected tools — REQ-06
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
    """Records calls to the bridge entry points and returns a canned result.

    Patches both ``bridge.invoke`` (parsed-JSON path) and
    ``bridge.invoke_text`` (raw stdout path). ``calls`` aggregates
    every call across both paths so existing tests that only check
    argv keep working; ``json_calls`` / ``text_calls`` let tests that
    care about which path was taken assert on it directly.
    """

    def __init__(self, result: Any = None, *, raises: Exception | None = None) -> None:
        self.result = result
        self.raises = raises
        self.calls: list[tuple[str, list[str]]] = []
        self.json_calls: list[tuple[str, list[str]]] = []
        self.text_calls: list[tuple[str, list[str]]] = []

    def invoke(self, op: str, args: list[str]) -> Any:
        self._record(self.json_calls, op, args)
        return self._return()

    def invoke_text(self, op: str, args: list[str]) -> Any:
        self._record(self.text_calls, op, args)
        return self._return()

    def _record(self, bucket: list[tuple[str, list[str]]], op: str, args: list[str]) -> None:
        entry = (op, list(args))
        bucket.append(entry)
        self.calls.append(entry)

    def _return(self) -> Any:
        if self.raises is not None:
            raise self.raises
        return self.result


@pytest.fixture
def stub_bridge(monkeypatch: pytest.MonkeyPatch):
    """Patch both `bridge.invoke` and `bridge.invoke_text` with a recorder."""

    def _install(result: Any = None, *, raises: Exception | None = None) -> _BridgeRecorder:
        recorder = _BridgeRecorder(result, raises=raises)
        monkeypatch.setattr(tools.bridge, "invoke", recorder.invoke)
        monkeypatch.setattr(tools.bridge, "invoke_text", recorder.invoke_text)
        return recorder

    return _install


# ---------------------------------------------------------------------------
# REQ-01 — happy path: argv translation + result passthrough
# ---------------------------------------------------------------------------


def test_list_tool_default_returns_text(stub_bridge) -> None:
    """Default ``list`` routes through the text bridge — matches CLI tree render."""
    recorder = stub_bridge(result="• 1 First item\n• 2 Second item\n")

    result = tools.list(workload="/tmp/wl")

    assert result == "• 1 First item\n• 2 Second item\n"
    assert recorder.text_calls == [("list", ["--workload", "/tmp/wl"])]
    assert recorder.json_calls == []


def test_list_tool_with_json_true_returns_parsed_json(stub_bridge) -> None:
    """``json=True`` routes through the JSON bridge — returns parsed payload."""
    recorder = stub_bridge(result={"items": []})

    result = tools.list(workload="/tmp/wl", json=True)

    assert result == {"items": []}
    assert recorder.json_calls == [("list", ["--workload", "/tmp/wl"])]
    assert recorder.text_calls == []


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
    """JSON-mode list (and every other tool) maps CLIResponseError to a ToolError.

    The text-mode default of ``list`` cannot encounter
    ``CLIResponseError`` because it does not parse stdout — so we
    explicitly exercise the JSON path with ``json=True``.
    """
    stub_bridge(raises=bridge.CLIResponseError(raw_stdout="not json blah"))

    with pytest.raises(ToolError) as excinfo:
        tools.list(workload="/tmp/wl", json=True)

    msg = str(excinfo.value)
    assert "not json blah" in msg
    assert "CLI/MCP version mismatch" in msg


# ---------------------------------------------------------------------------
# REQ-06 — module exposes exactly the 15 expected tools
# ---------------------------------------------------------------------------


EXPECTED_TOOLS = [
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


def test_module_exposes_exactly_the_15_expected_tools() -> None:
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
        "optional": ["ref", "filter", "exclude", "no_ids", "json"],
    },
    "find": {
        "required": ["workload"],
        "optional": ["keyword", "meta", "pattern"],
    },
    "summary": {
        "required": ["workload"],
        "optional": [],
    },
    "get": {
        "required": ["workload", "ref"],
        "optional": [],
    },
    "add": {
        "required": ["workload", "title"],
        "optional": ["placement", "ref"],
    },
    "update": {
        "required": ["workload", "ref", "path", "value"],
        "optional": [],
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
    "version": {
        "required": [],
        "optional": [],
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


def test_find_meta_presence_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"matches": []})

    tools.find(workload="/tmp/wl", meta="swc:stage")

    assert recorder.calls == [("find", ["--workload", "/tmp/wl", "--meta", "swc:stage"])]


def test_find_meta_with_pattern_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"matches": []})

    tools.find(workload="/tmp/wl", meta="swc:stage", pattern="plan")

    assert recorder.calls == [("find", ["--workload", "/tmp/wl", "--meta", "swc:stage", "plan"])]


def test_find_requires_keyword_or_meta() -> None:
    with pytest.raises(ToolError, match="keyword"):
        tools.find(workload="/tmp/wl")


def test_find_keyword_and_meta_are_mutually_exclusive() -> None:
    with pytest.raises(ToolError, match="both"):
        tools.find(workload="/tmp/wl", keyword="foo", meta="swc:stage")


def test_summary_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"total": 0})

    tools.summary(workload="/tmp/wl")

    assert recorder.calls == [("summary", ["--workload", "/tmp/wl"])]


def test_get_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"id": "abc1234", "title": "foo", "status": "not-started", "meta": {}})

    tools.get(workload="/tmp/wl", ref="2.3")

    assert recorder.calls == [("get", ["--workload", "/tmp/wl", "2.3"])]


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


def test_update_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"id": "abc1234"})

    tools.update(workload="/tmp/wl", ref="2", path="meta.owner", value="alice")

    assert recorder.calls == [("update", ["--workload", "/tmp/wl", "2", "meta.owner", "alice"])]


def test_rename_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"ok": True})

    tools.rename(workload="/tmp/wl", ref="2.3", title="New title")

    assert recorder.calls == [
        ("update", ["--workload", "/tmp/wl", "2.3", "title", "New title"])
    ]


def test_delete_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"ok": True})

    tools.delete(workload="/tmp/wl", ref="2.3")

    assert recorder.calls == [("delete", ["--workload", "/tmp/wl", "2.3"])]


def test_reset_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"status": "not-started"})

    tools.reset(workload="/tmp/wl", ref="2.3")

    assert recorder.calls == [("update", ["--workload", "/tmp/wl", "2.3", "status", "not-started"])]


def test_start_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"status": "in-progress"})

    tools.start(workload="/tmp/wl", ref="2.3")

    assert recorder.calls == [("update", ["--workload", "/tmp/wl", "2.3", "status", "in-progress"])]


def test_complete_tool_argv(stub_bridge) -> None:
    recorder = stub_bridge(result={"status": "done"})

    tools.complete(workload="/tmp/wl", ref="2.3")

    assert recorder.calls == [("update", ["--workload", "/tmp/wl", "2.3", "status", "done"])]


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
# version — does not call the bridge
# ---------------------------------------------------------------------------


def test_version_returns_mcp_key() -> None:
    result = tools.version()
    assert "mcp" in result
    assert isinstance(result["mcp"], str)
    assert len(result["mcp"]) > 0


def test_version_matches_package_version() -> None:
    from swc_workload_mcp import __version__
    assert tools.version() == {"mcp": __version__}


# ---------------------------------------------------------------------------
# Error mapping is uniform across tools — spot-check a non-list tool
# ---------------------------------------------------------------------------


def test_error_mapping_applies_to_every_tool(stub_bridge) -> None:
    stub_bridge(raises=bridge.CLINotFoundError(searched_paths=["swc-workload"]))

    # `version` does not call the bridge — skip it here.
    bridge_tools = [n for n in EXPECTED_TOOLS if n != "version"]

    for name in bridge_tools:
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
