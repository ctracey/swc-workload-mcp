"""Integration tier — authoring tools through the running MCP server.

Each test mirrors a scenario in the CLI's
``tests/bin/test_swc-workload_authoring.py``. The MCP test name echoes
the source CLI test name (REQ-08); each test's docstring carries a
``Mirrors:`` line for traceability. The composed chain under test is:
``ClientSession → FastMCP → tools.<op> → bridge → real swc-workload
subprocess``.

Conventions
-----------
- Every test is ``async`` and marked ``@pytest.mark.anyio``.
- Tests start by unpacking ``mcpw_ready`` (init-already-run) or
  ``mcpw`` (no init).
- Success paths read ``result.payload[...]`` from the helper's
  parsed-JSON return; error paths assert substrings on
  ``result.error``.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# add — top-level appends, hashes, dotted-prefix rejection
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_add_appends_top_level_item_with_hash_id(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_appends_top_level_item_with_hash_id"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="first")
    await call_tool("add", workload=w, title="second")
    result = await call_tool("add", workload=w, title="build a thing")
    assert result.error is None, result.error

    listed = await call_tool("list", workload=w)
    items = listed.payload["items"]
    assert len(items) == 3
    assert items[2]["title"] == "build a thing"
    assert items[2]["number"] == "3"
    assert len(items[2]["id"]) == 7


@pytest.mark.anyio
async def test_add_assigns_unique_hashes_when_titles_collide_across_parents(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_assigns_unique_hashes_when_titles_collide_across_parents"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="duplicate title")
    await call_tool("add", workload=w, title="duplicate title", placement="to", ref="1")
    listed = await call_tool("list", workload=w)
    top = listed.payload["items"][0]
    child = top["children"][0]
    assert top["id"] != child["id"], (
        f"expected distinct hashes for same title under different parents, "
        f"got {top['id']} and {child['id']}"
    )


@pytest.mark.anyio
async def test_add_rejects_dotted_number_prefix_title(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_rejects_dotted_number_prefix_title"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    result = await call_tool("add", workload=w, title="1.1 something")
    assert result.error is not None
    msg = result.error.lower()
    assert "number" in msg or "automatically" in msg


@pytest.mark.anyio
async def test_add_accepts_leading_digits_without_dot(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_accepts_leading_digits_without_dot"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    result = await call_tool("add", workload=w, title="12 monkeys")
    assert result.error is None, result.error
    listed = await call_tool("list", workload=w)
    items = listed.payload["items"]
    assert items[0]["title"] == "12 monkeys"


@pytest.mark.anyio
async def test_add_as_child_of_parent(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_as_child_of_parent

    This is the demo-bug-relevant scenario: ``add("sub item", placement="to",
    ref="2")`` must place the new item under the second top-level item as
    ``2.1``. If this test fails, the demo bug is real.
    """
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="two")
    result = await call_tool("add", workload=w, title="sub item", placement="to", ref="2")
    assert result.error is None, result.error

    listed = await call_tool("list", workload=w)
    items = listed.payload["items"]
    assert items[1]["children"][0]["title"] == "sub item"
    assert items[1]["children"][0]["number"] == "2.1"


@pytest.mark.anyio
async def test_add_rejects_duplicate_sibling_title(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_rejects_duplicate_sibling_title"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="first")
    result = await call_tool("add", workload=w, title="first")
    assert result.error is not None
    msg = result.error.lower()
    assert "collide" in msg or "first" in msg


@pytest.mark.anyio
async def test_add_rejects_case_variant_duplicate_sibling_title(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_rejects_case_variant_duplicate_sibling_title"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="ASDF")
    result = await call_tool("add", workload=w, title="asdf")
    assert result.error is not None
    assert "collide" in result.error.lower()


@pytest.mark.anyio
async def test_add_allows_same_title_under_different_parent(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_allows_same_title_under_different_parent"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="alpha")  # 1
    await call_tool("add", workload=w, title="beta")   # 2
    result = await call_tool("add", workload=w, title="alpha", placement="to", ref="2")
    assert result.error is None, result.error

    listed = await call_tool("list", workload=w)
    items = listed.payload["items"]
    assert items[0]["title"] == "alpha"
    assert items[1]["children"][0]["title"] == "alpha"
    assert items[1]["children"][0]["number"] == "2.1"


# ---------------------------------------------------------------------------
# add — `to <parent>` (append under) and `at <position>` (insert at slot)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_add_at_top_level_position_shifts_siblings_down(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_at_top_level_position_shifts_siblings_down"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="a")
    await call_tool("add", workload=w, title="b")
    await call_tool("add", workload=w, title="c")

    result = await call_tool("add", workload=w, title="x", placement="at", ref="2")
    assert result.error is None, result.error

    listed = await call_tool("list", workload=w)
    titles = [i["title"] for i in listed.payload["items"]]
    assert titles == ["a", "x", "b", "c"]


@pytest.mark.anyio
async def test_add_at_nested_position_uses_parent_from_target(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_at_nested_position_uses_parent_from_target"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="two")
    await call_tool("add", workload=w, title="a", placement="to", ref="2")
    await call_tool("add", workload=w, title="b", placement="to", ref="2")

    result = await call_tool("add", workload=w, title="x", placement="at", ref="2.1")
    assert result.error is None, result.error

    listed = await call_tool("list", workload=w)
    items = listed.payload["items"]
    titles = [c["title"] for c in items[1]["children"]]
    assert titles == ["x", "a", "b"]


@pytest.mark.anyio
async def test_add_at_out_of_range_caps_at_end(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_at_out_of_range_caps_at_end"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="a")
    await call_tool("add", workload=w, title="b")

    result = await call_tool("add", workload=w, title="x", placement="at", ref="99")
    assert result.error is None, result.error

    listed = await call_tool("list", workload=w)
    titles = [i["title"] for i in listed.payload["items"]]
    assert titles == ["a", "b", "x"]


@pytest.mark.anyio
async def test_add_collision_uses_siblings_at_target_slot(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_collision_uses_siblings_at_target_slot"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="alpha")          # 1
    await call_tool("add", workload=w, title="two")            # 2
    await call_tool("add", workload=w, title="alpha", placement="to", ref="2")  # 2.1

    result = await call_tool("add", workload=w, title="alpha", placement="at", ref="2.2")
    assert result.error is not None
    assert "collide" in result.error.lower()


@pytest.mark.anyio
async def test_add_collision_is_case_insensitive_at_target_slot(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_collision_is_case_insensitive_at_target_slot"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="ALPHA")
    result = await call_tool("add", workload=w, title="alpha", placement="at", ref="2")
    assert result.error is not None
    assert "collide" in result.error.lower()


@pytest.mark.anyio
async def test_add_at_rejects_missing_target_parent(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_at_rejects_missing_target_parent"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="a")
    result = await call_tool("add", workload=w, title="x", placement="at", ref="9.9")
    assert result.error is not None
    msg = result.error.lower()
    assert "not exist" in msg or "does not" in msg


# ---------------------------------------------------------------------------
# add — argparse-rejection round-trips (REQ-09)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_add_rejects_extra_positional_after_target(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_rejects_extra_positional_after_target

    REQ-09: the CLI rejects this at argparse; through the MCP layer the
    rejection still must surface as a ``ToolError`` (i.e.
    ``result.error is not None``). There's no MCP-equivalent way to
    pass "extra positionals" — the closest valid analogue is invoking
    ``add`` with a kwargs combo that exercises an invalid placement
    keyword (covered by ``test_add_rejects_unknown_placement_keyword``).

    Since the MCP tool's signature only accepts ``placement`` + ``ref``
    (not a sequence of extra positional args), the literal CLI shape
    isn't reachable. Skip with reason — see solution.md "Tests with
    no MCP equivalent — explicit skip with reason".
    """
    pytest.skip(
        "MCP tool surface has no equivalent for 'extra positional after "
        "target'; the tool signature is (workload, title, placement, "
        "ref) — there's no way to pass a fifth positional through. The "
        "argparse-rejection contract is exercised by "
        "test_add_rejects_unknown_placement_keyword instead."
    )


@pytest.mark.anyio
async def test_add_to_requires_target(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_to_requires_target

    REQ-09 argparse round-trip: ``add <title> to`` without a target must
    error. The MCP equivalent is ``placement="to"`` with ``ref=None``.
    """
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    result = await call_tool("add", workload=w, title="x", placement="to")
    assert result.error is not None
    msg = result.error.lower()
    assert "target" in msg or "to" in msg


@pytest.mark.anyio
async def test_add_at_requires_target(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_at_requires_target

    REQ-09 argparse round-trip: ``add <title> at`` without a target must error.
    """
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    result = await call_tool("add", workload=w, title="x", placement="at")
    assert result.error is not None
    msg = result.error.lower()
    assert "target" in msg or "at" in msg


@pytest.mark.anyio
async def test_add_ref_without_placement_surfaces_cli_rejection(mcpw_ready):
    """MCP-shape-specific regression: a client (e.g. MCP Inspector with
    its form-serialiser quirk) may send ``placement=null`` but ``ref="X"``.
    The MCP tool must forward ``ref`` to the CLI so the CLI rejects the
    malformed argv with a clear "expected 'to <parent>' or 'at <position>'"
    message — instead of silently dropping ``ref`` and adding at top level.

    Has no CLI-suite mirror because the CLI's positional argv can't
    represent this state (you can't pass a ref without the placement
    keyword in the slot before it). The MCP layer can — hence this
    MCP-only test.
    """
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="parent")
    result = await call_tool("add", workload=w, title="orphan", ref="1")

    assert result.error is not None, (
        "ref without placement must surface as a ToolError, not a silent "
        "top-level add"
    )
    msg = result.error.lower()
    assert "expected" in msg and ("to <parent>" in msg or "at <position>" in msg)
    # And confirm the workload state matches: only the parent, no orphan
    tree = (await call_tool("list", workload=w)).payload["items"]
    assert len(tree) == 1
    assert tree[0]["title"] == "parent"
    assert tree[0]["children"] == []


@pytest.mark.anyio
async def test_add_rejects_unknown_placement_keyword(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_rejects_unknown_placement_keyword

    REQ-09 argparse round-trip: second positional must be ``to`` or
    ``at``. Anything else (``in``, etc.) rejects loudly.
    """
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    result = await call_tool("add", workload=w, title="x", placement="in", ref="1")
    assert result.error is not None
    msg = result.error.lower()
    assert "'to'" in msg or "'at'" in msg or "expected" in msg


@pytest.mark.anyio
async def test_add_at_rejects_non_numeric_target(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_add_at_rejects_non_numeric_target"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="a")
    result = await call_tool("add", workload=w, title="x", placement="at", ref="abc1234")
    assert result.error is not None
    assert "number" in result.error.lower()


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_delete_drops_item_and_descendants_with_renumber(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_delete_drops_item_and_descendants_with_renumber"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="two")
    await call_tool("add", workload=w, title="three")
    await call_tool("add", workload=w, title="two-a", placement="to", ref="2")
    await call_tool("add", workload=w, title="two-b", placement="to", ref="2")

    result = await call_tool("delete", workload=w, ref="2")
    assert result.error is None, result.error

    listed = await call_tool("list", workload=w)
    items = listed.payload["items"]
    titles = [i["title"] for i in items]
    assert titles == ["one", "three"]
    assert items[1]["number"] == "2"


# ---------------------------------------------------------------------------
# rename
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_rename_preserves_id_status_position(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_rename_preserves_id_status_position"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="two")
    await call_tool("add", workload=w, title="x", placement="to", ref="2")
    await call_tool("add", workload=w, title="y", placement="to", ref="2")
    await call_tool("add", workload=w, title="target", placement="to", ref="2")
    await call_tool("start", workload=w, ref="2.3")

    before = (await call_tool("list", workload=w)).payload["items"]
    target_id = before[1]["children"][2]["id"]

    result = await call_tool("rename", workload=w, ref="2.3", title="new title")
    assert result.error is None, result.error

    after = (await call_tool("list", workload=w)).payload["items"]
    target = after[1]["children"][2]
    assert target["title"] == "new title"
    assert target["id"] == target_id
    assert target["status"] == "in-progress"
    assert target["number"] == "2.3"


@pytest.mark.anyio
async def test_rename_rejects_dotted_number_prefix(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_rename_rejects_dotted_number_prefix"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="first")
    result = await call_tool("rename", workload=w, ref="1", title="2.3 new title")
    assert result.error is not None
    listed = await call_tool("list", workload=w)
    items = listed.payload["items"]
    assert items[0]["title"] == "first"


@pytest.mark.anyio
async def test_rename_rejects_duplicate_sibling_title(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_rename_rejects_duplicate_sibling_title"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="alpha")
    await call_tool("add", workload=w, title="beta")
    result = await call_tool("rename", workload=w, ref="2", title="ALPHA")
    assert result.error is not None
    msg = result.error.lower()
    assert "collide" in msg or "alpha" in msg
    listed = await call_tool("list", workload=w)
    items = listed.payload["items"]
    assert items[1]["title"] == "beta"


@pytest.mark.anyio
async def test_rename_allows_no_op_self_rename(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_rename_allows_no_op_self_rename"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="alpha")
    result = await call_tool("rename", workload=w, ref="1", title="alpha")
    assert result.error is None, result.error


@pytest.mark.anyio
async def test_rename_allows_case_change_of_own_title(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_rename_allows_case_change_of_own_title"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="alpha")
    result = await call_tool("rename", workload=w, ref="1", title="ALPHA")
    assert result.error is None, result.error
    listed = await call_tool("list", workload=w)
    items = listed.payload["items"]
    assert items[0]["title"] == "ALPHA"


@pytest.mark.anyio
async def test_rename_allows_same_title_as_non_sibling(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_rename_allows_same_title_as_non_sibling"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="alpha")
    await call_tool("add", workload=w, title="beta")
    await call_tool("add", workload=w, title="gamma", placement="to", ref="1")
    result = await call_tool("rename", workload=w, ref="2", title="gamma")
    assert result.error is None, result.error


# ---------------------------------------------------------------------------
# move — direction form
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_move_up_preserves_ids(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_move_up_preserves_ids"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="parent")
    for label in ("a", "b", "c"):
        await call_tool("add", workload=w, title=label, placement="to", ref="1")
    before = (await call_tool("list", workload=w)).payload["items"][0]["children"]
    ids = [c["id"] for c in before]

    result = await call_tool("move", workload=w, ref="1.3", direction="up")
    assert result.error is None, result.error

    after = (await call_tool("list", workload=w)).payload["items"][0]["children"]
    assert [c["title"] for c in after] == ["a", "c", "b"]
    assert {c["id"] for c in after} == set(ids)


@pytest.mark.anyio
async def test_move_top_moves_to_first_slot(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_move_top_moves_to_first_slot"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="p")
    for label in ("a", "b", "c"):
        await call_tool("add", workload=w, title=label, placement="to", ref="1")
    result = await call_tool("move", workload=w, ref="1.3", direction="top")
    assert result.error is None
    after = (await call_tool("list", workload=w)).payload["items"][0]["children"]
    assert [c["title"] for c in after] == ["c", "a", "b"]
    assert after[0]["number"] == "1.1"


@pytest.mark.anyio
async def test_move_direction_rejects_unexpected_target(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_move_direction_rejects_unexpected_target

    REQ-09 argparse round-trip: ``move 2 up 3`` is rejected — the
    direction form does not accept a target.
    """
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="two")
    result = await call_tool("move", workload=w, ref="2", direction="up", target="1")
    assert result.error is not None
    msg = result.error.lower()
    assert "unexpected" in msg or "up" in msg


# ---------------------------------------------------------------------------
# move — `to <target>` form
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_move_reparents_and_reflows_both_sides(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_move_reparents_and_reflows_both_sides"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    for label in ("one", "two", "three"):
        await call_tool("add", workload=w, title=label)
    for label in ("2a", "2b", "2c"):
        await call_tool("add", workload=w, title=label, placement="to", ref="2")
    await call_tool("add", workload=w, title="moveme", placement="to", ref="2.3")  # 2.3.1
    for label in ("3a", "3b"):
        await call_tool("add", workload=w, title=label, placement="to", ref="3")

    before = (await call_tool("list", workload=w)).payload["items"]
    target_id = before[1]["children"][2]["children"][0]["id"]

    result = await call_tool("move", workload=w, ref="2.3.1", direction="to", target="3.2")
    assert result.error is None, result.error

    after = (await call_tool("list", workload=w)).payload["items"]
    three_children = after[2]["children"]
    assert [c["title"] for c in three_children] == ["3a", "moveme", "3b"]
    assert three_children[1]["id"] == target_id
    assert three_children[1]["number"] == "3.2"
    assert after[1]["children"][2]["children"] == []


@pytest.mark.anyio
async def test_move_rejects_cycle(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_move_rejects_cycle"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="two")
    for label in ("2a", "2b", "2c"):
        await call_tool("add", workload=w, title=label, placement="to", ref="2")
    await call_tool("add", workload=w, title="deep", placement="to", ref="2.3")  # 2.3.1

    before = (await call_tool("list", workload=w)).payload["items"]
    result = await call_tool("move", workload=w, ref="2", direction="to", target="2.3.1")
    assert result.error is not None
    assert "cycle" in result.error.lower()
    after = (await call_tool("list", workload=w)).payload["items"]
    assert after == before


@pytest.mark.anyio
async def test_move_rejects_missing_target_parent(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_move_rejects_missing_target_parent"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="two")
    await call_tool("add", workload=w, title="2a", placement="to", ref="2")

    before = (await call_tool("list", workload=w)).payload["items"]
    result = await call_tool("move", workload=w, ref="2.1", direction="to", target="9.9")
    assert result.error is not None
    msg = result.error.lower()
    assert "not exist" in msg or "does not" in msg
    after = (await call_tool("list", workload=w)).payload["items"]
    assert after == before


@pytest.mark.anyio
async def test_move_rejects_unknown_second_token(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_move_rejects_unknown_second_token

    REQ-09 argparse round-trip: the second positional must be a
    direction or the literal ``to``. ``too`` (typo) etc. errors loudly
    and leaves the tree untouched.
    """
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    for label in ("one", "two"):
        await call_tool("add", workload=w, title=label)
    for label in ("2a", "2b"):
        await call_tool("add", workload=w, title=label, placement="to", ref="2")

    before = (await call_tool("list", workload=w)).payload["items"]
    result = await call_tool("move", workload=w, ref="2.1", direction="too", target="2.2")
    assert result.error is not None
    msg = result.error.lower()
    assert "too" in msg or "expected" in msg or "'to'" in msg
    after = (await call_tool("list", workload=w)).payload["items"]
    assert after == before


@pytest.mark.anyio
async def test_move_to_requires_target(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_move_to_requires_target

    REQ-09 argparse round-trip: ``move <ref> to`` without a target must
    error. The MCP equivalent is ``direction="to"`` with ``target=None``.
    """
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="two")
    result = await call_tool("move", workload=w, ref="2", direction="to")
    assert result.error is not None
    assert "target" in result.error.lower()


@pytest.mark.anyio
async def test_move_target_without_to_errors(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_move_target_without_to_errors

    REQ-09 argparse round-trip: bare numeric in ``direction`` slot (e.g.
    ``move 2 1``) must error. The MCP equivalent is ``direction="1"``.
    """
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="two")
    result = await call_tool("move", workload=w, ref="2", direction="1")
    assert result.error is not None
    msg = result.error.lower()
    assert "expected" in msg or "'to'" in msg or "1" in msg


@pytest.mark.anyio
async def test_move_to_target_works(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_move_to_target_works"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="two")
    result = await call_tool("move", workload=w, ref="2", direction="to", target="1")
    assert result.error is None, result.error


@pytest.mark.anyio
async def test_move_leaves_orphaned_parent_status_untouched(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_move_leaves_orphaned_parent_status_untouched"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="parent")
    await call_tool("add", workload=w, title="kid", placement="to", ref="2")
    await call_tool("start", workload=w, ref="2.1")

    before = (await call_tool("list", workload=w)).payload["items"]
    assert before[1]["status"] == "in-progress"

    result = await call_tool("move", workload=w, ref="2.1", direction="to", target="2")
    assert result.error is None, result.error

    after = (await call_tool("list", workload=w)).payload["items"]
    orphaned = next(i for i in after if i["title"] == "parent")
    assert orphaned["children"] == []
    assert orphaned["status"] == "in-progress"


@pytest.mark.anyio
async def test_move_same_parent_source_after_target_lands_at_requested_position(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_move_same_parent_source_after_target_lands_at_requested_position"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="two")
    for label in ("2a", "2b", "2c"):
        await call_tool("add", workload=w, title=label, placement="to", ref="2")

    result = await call_tool("move", workload=w, ref="2.3", direction="to", target="2.1")
    assert result.error is None, result.error

    after = (await call_tool("list", workload=w)).payload["items"]
    titles = [c["title"] for c in after[1]["children"]]
    assert titles == ["2c", "2a", "2b"]


@pytest.mark.anyio
async def test_move_same_parent_source_before_target_lands_at_requested_position(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_authoring.py::test_move_same_parent_source_before_target_lands_at_requested_position"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="two")
    for label in ("a", "b", "c"):
        await call_tool("add", workload=w, title=label, placement="to", ref="2")

    before = (await call_tool("list", workload=w)).payload["items"]
    ids_before = {c["title"]: c["id"] for c in before[1]["children"]}

    result = await call_tool("move", workload=w, ref="2.1", direction="to", target="2.3")
    assert result.error is None, result.error

    after = (await call_tool("list", workload=w)).payload["items"]
    titles = [c["title"] for c in after[1]["children"]]
    ids_after = {c["title"]: c["id"] for c in after[1]["children"]}

    assert titles == ["b", "c", "a"], (
        f"expected [b, c, a] (final-position semantics); got {titles}. "
        "If this is [b, a, c], the removed `insert_idx -= 1` block has been re-added."
    )
    assert ids_after == ids_before
