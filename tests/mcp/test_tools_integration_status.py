"""Integration tier — status tools through the running MCP server.

Each test mirrors a scenario in the CLI's
``tests/bin/test_swc-workload_status.py``. The MCP test name echoes
the source CLI test name (REQ-08); each test's docstring carries a
``Mirrors:`` line for traceability.

Conventions are documented in ``test_tools_integration_authoring.py``.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# status update and rollup
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_marking_child_in_progress_rolls_parent_to_in_progress(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_status.py::test_marking_child_in_progress_rolls_parent_to_in_progress"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="two")
    await call_tool("add", workload=w, title="three")
    await call_tool("add", workload=w, title="3a", placement="to", ref="3")
    await call_tool("add", workload=w, title="3b", placement="to", ref="3")

    result = await call_tool("start", workload=w, ref="3.2")
    assert result.error is None, result.error

    after = (await call_tool("list", workload=w)).payload["items"]
    parent = after[2]
    assert parent["children"][1]["status"] == "in-progress"
    assert parent["status"] == "in-progress"


@pytest.mark.anyio
async def test_marking_last_child_done_rolls_parent_to_done(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_status.py::test_marking_last_child_done_rolls_parent_to_done"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="p")
    await call_tool("add", workload=w, title="a", placement="to", ref="1")
    await call_tool("add", workload=w, title="b", placement="to", ref="1")

    await call_tool("complete", workload=w, ref="1.1")
    await call_tool("start", workload=w, ref="1.2")
    result = await call_tool("complete", workload=w, ref="1.2")
    assert result.error is None, result.error

    after = (await call_tool("list", workload=w)).payload["items"]
    p = after[0]
    assert p["children"][1]["status"] == "done"
    assert p["status"] == "done"


# ---------------------------------------------------------------------------
# done is sticky
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_start_on_done_is_sticky_and_leaves_file_unchanged(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_status.py::test_start_on_done_is_sticky_and_leaves_file_unchanged"""
    call_tool, workload, workload_json, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="leaf")
    await call_tool("complete", workload=w, ref="1")

    original = workload_json.read_text()
    result = await call_tool("start", workload=w, ref="1")
    assert result.error is None, result.error

    assert workload_json.read_text() == original

    after = (await call_tool("list", workload=w)).payload["items"]
    assert after[0]["status"] == "done"


@pytest.mark.anyio
async def test_reset_on_done_re_opens_it(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_status.py::test_reset_on_done_re_opens_it"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="leaf")
    await call_tool("complete", workload=w, ref="1")
    before_list = (await call_tool("list", workload=w)).payload["items"]
    assert before_list[0]["status"] == "done"

    result = await call_tool("reset", workload=w, ref="1")
    assert result.error is None, result.error

    after = (await call_tool("list", workload=w)).payload["items"]
    assert after[0]["status"] == "not-started"


# ---------------------------------------------------------------------------
# Parent-marked-done warning path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_parent_marked_done_with_undone_children_warns_on_stderr(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_status.py::test_parent_marked_done_with_undone_children_warns_on_stderr

    The CLI version asserts on a stderr warning emitted alongside an
    exit-0 success. Our bridge captures stderr but only surfaces it on
    *non-zero* exits (via ``CLIExecutionError``). On the exit-0 success
    path, the warning is currently lost through the MCP layer.

    The agent ports this as a structural assertion: the operation
    succeeds (no error returned), the file is rewritten (mtime/contents
    change), and the parent status is now ``done``. If the CLI's
    warning ever surfaces through MCP in the future (e.g. via a
    structured warnings array in the JSON payload), this test should
    be extended to assert on it.
    """
    call_tool, workload, workload_json, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="p")
    await call_tool("add", workload=w, title="a", placement="to", ref="1")
    await call_tool("add", workload=w, title="b", placement="to", ref="1")
    await call_tool("add", workload=w, title="c", placement="to", ref="1")

    await call_tool("complete", workload=w, ref="1.1")
    before = workload_json.read_text()

    result = await call_tool("complete", workload=w, ref="1")
    assert result.error is None, result.error

    assert workload_json.read_text() != before
    after = (await call_tool("list", workload=w)).payload["items"]
    assert after[0]["status"] == "done"
