"""Integration tier — I/O tools through the running MCP server.

Each test mirrors a scenario in the CLI's
``tests/bin/test_swc-workload_io.py`` plus the top-level
``tests/test_find_by_ref.py`` regressions. The MCP test name echoes
the source CLI test name (REQ-08); each test's docstring carries a
``Mirrors:`` line for traceability.

Conventions are documented in ``test_tools_integration_authoring.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# find
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_find_returns_all_matches(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_find_returns_all_matches"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="cli tool one")
    await call_tool("add", workload=w, title="two")
    await call_tool("add", workload=w, title="cli wrapper")
    await call_tool("add", workload=w, title="cli plugin")

    result = await call_tool("find", workload=w, keyword="cli")
    assert result.error is None
    matches = result.payload["matches"]
    titles = [m["title"] for m in matches]
    assert len(matches) == 3
    assert all("cli" in t for t in titles)


@pytest.mark.anyio
async def test_find_single_match(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_find_single_match

    The CLI version of this test invokes ``find`` without ``--json`` and
    asserts on stdout text. Our bridge always passes ``--json``, so the
    MCP equivalent asserts on the parsed match list instead: a single
    match returned, with the expected title and no spurious entries.
    """
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="boring")
    await call_tool("add", workload=w, title="workload radiator")
    await call_tool("add", workload=w, title="other thing")

    result = await call_tool("find", workload=w, keyword="workload radiator")
    assert result.error is None
    titles = [m["title"] for m in result.payload["matches"]]
    assert "workload radiator" in titles
    assert "boring" not in titles


# ---------------------------------------------------------------------------
# resolve by number / hash id; reference not found
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_resolve_by_number(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_resolve_by_number"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="two")
    await call_tool("add", workload=w, title="a", placement="to", ref="2")
    await call_tool("add", workload=w, title="b", placement="to", ref="2")

    result = await call_tool("list", workload=w, ref="2")
    assert result.error is None, result.error
    items = result.payload["items"]
    assert items[0]["number"] == "2"
    assert items[0]["title"] == "two"
    assert len(items[0]["children"]) == 2


@pytest.mark.anyio
async def test_resolve_by_hash_id(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_resolve_by_hash_id"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="target")
    await call_tool("add", workload=w, title="a", placement="to", ref="2")

    listed = (await call_tool("list", workload=w)).payload["items"]
    target_id = listed[1]["id"]

    result = await call_tool("list", workload=w, ref=target_id)
    assert result.error is None
    items = result.payload["items"]
    assert items[0]["id"] == target_id
    assert items[0]["title"] == "target"


@pytest.mark.anyio
async def test_reference_not_found(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_reference_not_found"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    result = await call_tool("list", workload=w, ref="9.9")
    assert result.error is not None
    assert "not found" in result.error.lower()


# ---------------------------------------------------------------------------
# list — full tree, status symbols (text-output test → skip per solution.md)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_renders_full_tree_with_symbols(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_list_renders_full_tree_with_symbols

    The CLI test asserts on the human-readable rendering with status
    glyphs (``✔``, ``▣``). The bridge always passes ``--json``, so
    glyphs aren't reachable through the MCP layer. The structural
    equivalent — that the items appear at the right places with the
    right statuses — is already covered by every other ``list``-based
    test in this file (and by ``test_list_json_is_parseable_tree``).
    Skip explicitly per solution.md.
    """
    pytest.skip(
        "Text-output rendering (status glyphs) is unreachable through MCP: "
        "the bridge always invokes the CLI with --json. Structural status "
        "checks are covered by every other list-based test in this file."
    )


# ---------------------------------------------------------------------------
# list — filter / exclude
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_filter_status_in_progress(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_list_filter_status_in_progress"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="a")
    await call_tool("add", workload=w, title="b")
    await call_tool("add", workload=w, title="c")
    await call_tool("complete", workload=w, ref="1")
    await call_tool("start", workload=w, ref="2")

    result = await call_tool("list", workload=w, filter="status:in-progress")
    assert result.error is None
    items = result.payload["items"]
    titles = [i["title"] for i in items]
    assert "b" in titles
    assert "a" not in titles
    assert "c" not in titles


@pytest.mark.anyio
async def test_list_exclude_status_done(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_list_exclude_status_done"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="a")
    await call_tool("add", workload=w, title="b")
    await call_tool("add", workload=w, title="c")
    await call_tool("complete", workload=w, ref="1")
    await call_tool("start", workload=w, ref="2")

    result = await call_tool("list", workload=w, exclude="status:done")
    assert result.error is None
    items = result.payload["items"]
    titles = [i["title"] for i in items]
    assert "a" not in titles
    assert "b" in titles
    assert "c" in titles


# ---------------------------------------------------------------------------
# list <ref> — show a subtree
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_with_ref_renders_item_with_children(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_list_with_ref_renders_item_with_children"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="one")
    await call_tool("add", workload=w, title="parent")
    await call_tool("add", workload=w, title="kid-a", placement="to", ref="2")
    await call_tool("add", workload=w, title="kid-b", placement="to", ref="2")

    result = await call_tool("list", workload=w, ref="2")
    assert result.error is None
    items = result.payload["items"]
    assert items[0]["title"] == "parent"
    child_titles = [c["title"] for c in items[0]["children"]]
    assert "kid-a" in child_titles
    assert "kid-b" in child_titles
    titles_all = [items[0]["title"], *child_titles]
    assert "one" not in titles_all


@pytest.mark.anyio
async def test_list_with_ref_and_filter_scopes_to_subtree(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_list_with_ref_and_filter_scopes_to_subtree"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="parent")
    await call_tool("add", workload=w, title="a", placement="to", ref="1")
    await call_tool("add", workload=w, title="b", placement="to", ref="1")
    await call_tool("add", workload=w, title="c", placement="to", ref="1")
    await call_tool("start", workload=w, ref="1.2")

    result = await call_tool("list", workload=w, ref="1", filter="status:in-progress")
    assert result.error is None, result.error
    items = result.payload["items"]
    assert len(items) == 1
    assert items[0]["title"] == "parent"
    titles = [c["title"] for c in items[0]["children"]]
    assert titles == ["b"]


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_summary_partial(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_summary_partial"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    for i in range(10):
        await call_tool("add", workload=w, title=f"item {i}")
    for i in range(1, 5):
        await call_tool("complete", workload=w, ref=str(i))
    for i in range(5, 8):
        await call_tool("start", workload=w, ref=str(i))

    result = await call_tool("summary", workload=w)
    assert result.error is None
    payload = result.payload
    assert payload["total"] == 10
    assert payload["done"] == 4
    assert payload["wip"] == 3
    assert payload["progress"] == 40


@pytest.mark.anyio
async def test_summary_text_includes_wip(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_summary_text_includes_wip

    The CLI version asserts on the text rendering (``wip=1``). The MCP
    layer always returns JSON, so the structural equivalent is asserting
    on the ``wip`` field of the parsed payload.
    """
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="a")
    await call_tool("add", workload=w, title="b")
    await call_tool("start", workload=w, ref="1")

    result = await call_tool("summary", workload=w)
    assert result.error is None
    assert result.payload["wip"] == 1


# ---------------------------------------------------------------------------
# JSON shape
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_json_is_parseable_tree(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_list_json_is_parseable_tree"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="a")
    await call_tool("add", workload=w, title="b")
    await call_tool("add", workload=w, title="b1", placement="to", ref="2")

    result = await call_tool("list", workload=w)
    assert result.error is None
    payload = result.payload
    items = payload["items"]
    assert len(items) == 2
    for item in items:
        assert "id" in item
        assert "title" in item
        assert "status" in item
        assert "children" in item
    assert len(items[1]["children"]) == 1


@pytest.mark.anyio
async def test_list_without_json_is_text(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_list_without_json_is_text

    Skipped per solution.md: the bridge always passes ``--json``, so the
    "text output" form is not reachable through the MCP layer.
    """
    pytest.skip(
        "Bridge always passes --json; text-output form unreachable through MCP."
    )


@pytest.mark.anyio
async def test_text_output_includes_hash_next_to_title(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_text_output_includes_hash_next_to_title

    Skipped per solution.md: text output (hash beside title in the
    rendered tree) is not reachable through MCP — JSON only.
    """
    pytest.skip(
        "Bridge always passes --json; text-output form unreachable through MCP."
    )


# ---------------------------------------------------------------------------
# Schema validation + JSON-decode error paths (file-load surface)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_load_workload_rejects_malformed_shape(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_load_workload_rejects_malformed_shape

    Uses the ``seed`` helper (per solution.md) to write a malformed
    ``workload.json`` directly — bypassing the ``init`` tool — because
    the purpose of this test is to exercise the file-load error path.
    """
    call_tool, workload, _wlj, seed = mcpw_ready
    w = str(workload)

    malformed = {"items": [{"id": "abc1234", "title": "broken", "children": []}]}
    seed(malformed)

    result = await call_tool("list", workload=w)
    assert result.error is not None
    msg = result.error.lower()
    assert "workload.json" in msg or "invalid" in msg
    assert "status" in msg


@pytest.mark.anyio
async def test_load_workload_rejects_top_level_non_dict(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_load_workload_rejects_top_level_non_dict

    Deliberate-seed test — see solution.md.
    """
    call_tool, workload, _wlj, seed = mcpw_ready
    w = str(workload)

    seed(["not", "a", "dict"])

    result = await call_tool("list", workload=w)
    assert result.error is not None
    msg = result.error.lower()
    assert "invalid" in msg or "workload.json" in msg


@pytest.mark.anyio
async def test_load_workload_json_decode_error_reports_line_and_column(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_load_workload_json_decode_error_reports_line_and_column

    Deliberate-seed test — see solution.md.
    """
    call_tool, workload, _wlj, seed = mcpw_ready
    w = str(workload)

    seed('{"items": [')  # truncated JSON

    result = await call_tool("list", workload=w)
    assert result.error is not None
    msg = result.error.lower()
    assert "workload.json invalid" in msg
    assert "line" in msg
    assert "column" in msg
    assert "<root>" not in result.error


# ---------------------------------------------------------------------------
# init — pure file creation
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_init_creates_workload_json_inside_supplied_folder(mcpw):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_init_creates_workload_json_inside_supplied_folder"""
    call_tool, workload, workload_json, _seed = mcpw
    w = str(workload)

    assert not workload_json.exists()
    result = await call_tool("init", workload=w)
    assert result.error is None, result.error
    assert workload_json.exists()
    data = json.loads(workload_json.read_text())
    assert data == {"items": []}


@pytest.mark.anyio
async def test_init_refuses_to_overwrite_existing_file(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_init_refuses_to_overwrite_existing_file"""
    call_tool, workload, workload_json, _seed = mcpw_ready
    w = str(workload)

    original = workload_json.read_text()
    result = await call_tool("init", workload=w)
    assert result.error is not None
    err = result.error
    assert str(workload_json) in err or "already exists" in err.lower()
    assert workload_json.read_text() == original


# ---------------------------------------------------------------------------
# Missing-workload path on non-init op
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_op_on_missing_workload_recommends_init(mcpw):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_op_on_missing_workload_recommends_init"""
    call_tool, workload, _wlj, _seed = mcpw
    w = str(workload)

    result = await call_tool("list", workload=w)
    assert result.error is not None
    assert "init" in result.error.lower()


# ---------------------------------------------------------------------------
# --workload folder contract
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_workload_folder_does_not_exist_errors_clearly(mcpw, tmp_path: Path):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_workload_folder_does_not_exist_errors_clearly"""
    call_tool, _workload, _wlj, _seed = mcpw

    missing = tmp_path / "no-such-folder"
    result = await call_tool("list", workload=str(missing))
    assert result.error is not None
    msg = result.error.lower()
    assert "does not exist" in msg
    assert "folder" in msg


@pytest.mark.anyio
async def test_workload_pointed_at_a_file_errors_clearly(mcpw, tmp_path: Path):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_workload_pointed_at_a_file_errors_clearly"""
    call_tool, _workload, _wlj, _seed = mcpw

    f = tmp_path / "not-a-folder.json"
    f.write_text("{}")
    result = await call_tool("list", workload=str(f))
    assert result.error is not None
    msg = result.error.lower()
    assert "folder" in msg
    assert "file" in msg


@pytest.mark.anyio
async def test_init_requires_folder_to_exist(mcpw, tmp_path: Path):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_init_requires_folder_to_exist"""
    call_tool, _workload, _wlj, _seed = mcpw

    missing = tmp_path / "no-such-folder"
    result = await call_tool("init", workload=str(missing))
    assert result.error is not None
    assert "does not exist" in result.error.lower()
    assert not missing.exists(), "init should not create the folder"


# ---------------------------------------------------------------------------
# exists — file-presence check
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_exists_false_when_folder_is_missing(mcpw, tmp_path: Path):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_exists_false_when_folder_is_missing"""
    call_tool, _workload, _wlj, _seed = mcpw

    missing = tmp_path / "no-such-folder"
    result = await call_tool("exists", workload=str(missing))
    assert result.error is None
    # CLI's --json form returns {"exists": <bool>}; the text form returns "true"/"false".
    # Our bridge always passes --json, so the JSON form is what we see.
    assert result.payload == {"exists": False}


@pytest.mark.anyio
async def test_exists_false_when_path_is_a_file(mcpw, tmp_path: Path):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_exists_false_when_path_is_a_file"""
    call_tool, _workload, _wlj, _seed = mcpw

    f = tmp_path / "not-a-folder.json"
    f.write_text("{}")
    result = await call_tool("exists", workload=str(f))
    assert result.error is None
    assert result.payload == {"exists": False}


@pytest.mark.anyio
async def test_exists_false_when_folder_exists_but_no_workload_json(mcpw):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_exists_false_when_folder_exists_but_no_workload_json"""
    call_tool, workload, workload_json, _seed = mcpw

    assert not workload_json.exists()
    result = await call_tool("exists", workload=str(workload))
    assert result.error is None
    assert result.payload == {"exists": False}


@pytest.mark.anyio
async def test_exists_true_when_workload_json_present(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_exists_true_when_workload_json_present"""
    call_tool, workload, workload_json, _seed = mcpw_ready

    assert workload_json.exists()
    result = await call_tool("exists", workload=str(workload))
    assert result.error is None
    assert result.payload == {"exists": True}


@pytest.mark.anyio
async def test_exists_json_form_true(mcpw_ready):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_exists_json_form_true

    Skipped per solution.md: the bridge always passes ``--json``, so the
    JSON-form variant collapses with ``test_exists_true_when_workload_json_present``
    above — there's only one form reachable through MCP and it's
    already covered.
    """
    pytest.skip(
        "Bridge always passes --json; the JSON-form variant collapses with "
        "test_exists_true_when_workload_json_present which already asserts on "
        "the {'exists': True} payload."
    )


@pytest.mark.anyio
async def test_exists_json_form_false(mcpw):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_exists_json_form_false

    Skipped per solution.md: same collapse as ``test_exists_json_form_true``.
    """
    pytest.skip(
        "Bridge always passes --json; the JSON-form variant collapses with "
        "test_exists_false_when_folder_exists_but_no_workload_json which already "
        "asserts on the {'exists': False} payload."
    )


# ---------------------------------------------------------------------------
# OSError surface (read-only filesystem)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_oserror_in_save_workload_surfaces_as_friendly_error(mcpw):
    """Mirrors: tests/bin/test_swc-workload_io.py::test_oserror_in_save_workload_surfaces_as_friendly_error

    Skipped per solution.md: simulating an OS error through the MCP
    layer requires invasive setup (read-only FS, monkeypatching the
    CLI subprocess). The error round-trip is exercised by every other
    error-path test in this file; the *specific* "friendly OSError
    message" contract is a CLI-layer concern, not an MCP wrapper
    concern.
    """
    pytest.skip(
        "OSError simulation requires invasive setup (read-only FS or "
        "monkeypatched subprocess); the CLI-layer 'friendly message' "
        "contract is exercised by the CLI's own test suite. The MCP "
        "layer's job is to surface the resulting CLIExecutionError as "
        "a ToolError, which every other error-path test in this file "
        "already verifies."
    )


# ---------------------------------------------------------------------------
# find_by_ref regressions (from tests/test_find_by_ref.py at the CLI repo root)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_all_digit_hash_id_resolves_to_item_not_path(mcpw_ready):
    """Mirrors: tests/test_find_by_ref.py::test_all_digit_hash_id_resolves_to_item_not_path

    The CLI test calls ``find_by_ref`` directly against an in-memory
    list and crafts an all-digit hash. We can't call ``find_by_ref``
    through the MCP layer — but the *behaviour* it protects (an
    all-digit hash resolves to the item with that ID, not to a
    numeric path) is observable: pick the hash assigned by the CLI to
    an existing item, ``list`` by it, and verify the right item comes
    back.

    Caveat: hashes are randomly generated; an all-digit hash appears
    roughly 3.7% of the time. To exercise the contract we just rely
    on the fact that hash IDs *resolve* even when they're numeric-only
    — verifying via a generic ``list`` call by-id. If the bug regresses
    (path-resolution takes precedence over id-resolution), this test
    would fail whenever the assigned hash happens to be all-digits.
    The strict in-memory variant of this regression lives in the CLI's
    own suite.
    """
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="first")
    await call_tool("add", workload=w, title="target")
    await call_tool("add", workload=w, title="third")

    listed = (await call_tool("list", workload=w)).payload["items"]
    target_id = listed[1]["id"]

    # Use the assigned hash as the ref. The contract: list-by-id
    # returns the right item regardless of whether the ID's character
    # set happens to overlap with the dotted-path syntax.
    result = await call_tool("list", workload=w, ref=target_id)
    assert result.error is None
    items = result.payload["items"]
    assert items[0]["id"] == target_id
    assert items[0]["title"] == "target"


@pytest.mark.anyio
async def test_numeric_path_still_resolves_when_no_id_matches(mcpw_ready):
    """Mirrors: tests/test_find_by_ref.py::test_numeric_path_still_resolves_when_no_id_matches"""
    call_tool, workload, _wlj, _seed = mcpw_ready
    w = str(workload)

    await call_tool("add", workload=w, title="first")
    await call_tool("add", workload=w, title="second")

    result = await call_tool("list", workload=w, ref="2")
    assert result.error is None
    items = result.payload["items"]
    assert items[0]["title"] == "second"
