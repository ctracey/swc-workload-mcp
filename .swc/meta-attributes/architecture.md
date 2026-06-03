# Architecture

## Context

`swc-workload-mcp` is a thin MCP server that wraps the `swc-workload` CLI binary. Every tool translates kwargs into CLI argv, shells out via a subprocess bridge, and returns either parsed JSON or raw text. The MCP owns no data — the workload artefact (`workload.json`) is read and written by the CLI.

This work extends the workload data model with two new concepts (`notes`-as-free-text was considered and dropped; only `meta` survives) and reshapes the tool surface to expose them. Because the MCP is a wrapper, every new capability requires a matching CLI change — the MCP work locks the interface; the CLI catches up.

## Design

### New workitem field

```jsonc
{
  "id": "...",
  "n": 1,
  "title": "...",
  "status": "not-started" | "wip" | "done",
  "meta": { /* any valid JSON tree, opaque, caller-owned */ }
}
```

- `meta` — opaque JSON tree on each item. The MCP stores it verbatim and does not interpret structure.
- **Convention (docs, not enforced)**: callers use the first path segment as a namespace named `vendor:purpose` (e.g. `swc:workflow-status`). Avoiding `.` in namespace names keeps dotted-path parsing unambiguous.

### Tool surface — additions

| Tool | Purpose |
|---|---|
| `get(ref, meta=True)` | Single item by exact ref. Errors if not found. Returns meta by default. |
| `update_meta(ref, path, value)` | Write `value` at dotted `path` within `meta`. Empty path replaces the whole `meta` blob. Leaf semantics: replace (not shallow merge). Creates intermediate objects if missing. |
| `find_by_meta(path, pattern?, meta=False)` | Path-based search. Presence-only if no `pattern`; regex match against the string value at `path` if `pattern` is provided. Missing path or non-string value → no match (no error). |
| `version()` | Returns `{mcp: "<ver>", cli: "<ver>"}`. |

### Tool surface — changes to existing tools

| Tool | Change |
|---|---|
| `add(title, meta=None, placement=None, ref=None)` | Accepts optional `meta` at creation. |
| `list(...)` | Accepts `meta: bool = False` (opt-in to include meta). Replaces `no_ids: bool` with `ids: bool = True` (explicit value, default documented). |
| `find(keyword, meta=False)` | Accepts `meta: bool = False`. |
| `summary(meta=False)` | Accepts `meta: bool = False`. |
| `start(ref, meta=None)` | Optional `meta: {path: value, ...}` — one or more path writes applied atomically with the status flip. |
| `complete(ref, meta=None)` | Same. |
| `reset(ref, meta=None)` | Same. |

### Read defaults

| Tool | Meta default |
|---|---|
| `list` | omitted |
| `find` | omitted |
| `find_by_meta` | omitted |
| `summary` | omitted |
| `get` | **included** |

Documented in usage docs alongside the tools.

## Decisions

- **MCP locks the interface; CLI catches up.** This branch defines the spec via MCP wrappers + tests. CLI work happens upstream to match.
- **Drop `notes` as a first-class field.** Free text lives in `meta` if a caller wants it. Avoids forcing the MCP to know meta is a string for append semantics, and avoids inventing a near-universal field that some callers (e.g. SWC) won't use because they already have side-channel docs.
- **No migration.** Pre-existing workload artefacts simply lack `meta` on their items. Reads tolerate absence. New writes can add.
- **Boolean flag convention shift**: `--no-ids` → `--ids false`. All boolean options take explicit values; defaults are documented (`ids: true`, `meta: false` except on `get` where `meta: true`).
- **Atomic status + meta writes.** `start` / `complete` / `reset` accept an optional `meta: {path: value, ...}` mapping so a status flip and one or more path writes land in one call. Multi-path chosen over single-write because the real workflow event (e.g. completing a stage) typically updates several fields in one atomic move (stage, timestamp, evidence ref, next-stage hint).
- **Single `update_meta(ref, path, value)` writer**, not separate replace + merge tools. Path-based addressing covers whole-namespace replace (empty path / first-segment path) and single-key write (deeper path) in one shape. Reduces the surface and avoids overlapping semantics. Earlier design proposed separate `set_meta` + `patch_meta`; collapsed during breakdown.
- **Breaking MCP interface change accepted for this version.** `--no-ids` removal and read-shape additions break existing callers. Justified by the cleanup and the early stage of the MCP.
- **`find_by_meta` matching is dumb JSON navigation + regex on string values.** Missing path → no match (no error). Non-string values at the path are no-match. Path syntax is the same dotted syntax as `update_meta`. Keeps the MCP free of a query language while covering 95% of practical lookups.
- **Version tool**: `version()` returns both MCP and CLI versions for runtime compatibility checks. CLI version sourced via `swc-workload --version`.

## Constraints

- MCP must remain ignorant of meta contents — no validation, no inference of `status` from meta, no meta-path query operators beyond simple navigation + regex string match.
- Schema ownership (versioning, migrations, validation) lives with the caller.
- Reads must stay payload-aware — `meta` can grow; list-style reads omit by default.
- Every MCP tool body must remain a thin argv-assembly + bridge call. No business logic in the MCP layer.

## Folder structure

```
swc_workload_mcp/
  __init__.py
  __main__.py        # entry point — `swc-workload-mcp` script
  _version.py        # MCP version (read by version() tool)
  bridge.py          # subprocess bridge to swc-workload CLI
  server.py          # FastMCP server bootstrap; iterates TOOLS to register
  tools.py           # one callable per CLI op + TOOLS registry

tests/mcp/
  unit/              # tool argv assembly, bridge behaviour
  integration/       # tools-against-real-CLI
  e2e/               # smoke

docs/                # usage docs — needs updates for meta, version, ids/meta defaults
```

