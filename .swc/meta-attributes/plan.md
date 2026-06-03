# Plan

## Goal / Why

Add a generic, opaque, namespaced `meta` blob to work items in the workload MCP. Today work items only carry `title` + `status`; orchestrators consuming the MCP (SWC's delivery workflow first, others later) need somewhere to attach richer structured per-item state — workflow stage, exit evidence, indexes — without the MCP learning each consumer's vocabulary. When this lands, callers can persist arbitrary per-item state through the MCP under their own namespace, schema ownership stays with the caller, and SWC stops needing side-channel files for per-item workflow state.

> `ref_architecture-mcp.md` (in this folder) describes a `description` → `notes` rename, but inspection of `swc_workload_mcp/tools.py` shows no `description` field exists today. After discussion, `notes` was dropped entirely from this scope — free text lives in `meta` if callers want it.

## Users and scenarios

- **SWC orchestrator (primary consumer today)** — needs to record per-item workflow state (current workflow stage, exit evidence, deferred decisions) against each work item without inventing a parallel storage mechanism. Will use a namespace such as `swc-workflow-status`.
- **Future orchestrators** — same shape: pick a namespace, write JSON, read it back. The MCP treats every namespace as an opaque string keying an opaque JSON blob.

## Features

1. **New `meta` field on work items** — top-level object; caller-defined namespace is conventionally the first path segment. Values are opaque JSON.
2. **`update_meta(ref, path, value)`** — single path-based writer. Writes `value` at the dotted `path` within `meta`. Empty path replaces the entire `meta` blob. Leaf semantics: replace (not shallow merge).
3. **`get(ref, meta=True)`** — new dedicated single-item lookup by exact ref. Errors on miss. Meta included by default.
4. **`find_by_meta(path, pattern?, meta=False)`** — path-based search. Presence-only when no `pattern`; regex match against the string value at `path` when `pattern` is provided. Missing path or non-string value → no match (no error).
5. **`version()`** — returns `{mcp: "<ver>", cli: "<ver>"}` for runtime compatibility checks.
6. **Read-shape changes on existing tools** — `list` / `find` / `summary` accept `meta: bool = False`. `get` defaults `meta: true`.
7. **Atomic status + meta** — `start` / `complete` / `reset` accept optional `meta: {path: value, ...}` so a status flip and one or more meta writes land together.
8. **`add(title, meta=None, ...)`** — accepts optional `meta` at creation.
9. **Boolean flag convention shift** — `--no-ids` → `--ids false`. Documented defaults (`ids: true`, `meta: false`/`true` per tool).
10. **Usage docs updates** — meta field, namespace convention guide (`vendor:purpose`, first path segment, avoid dots), new tools, read defaults, boolean flag convention, breaking-change note.

## Out of scope

- Data migration of pre-existing workloads. New writes add `meta`; old items simply lack it. Reads tolerate absence.
- A first-class `notes` field. Free text lives in `meta` if callers want it.
- A query language beyond JSON-path + regex on string values for `find_by_meta`.
- `summary` synthesising meta-derived views.
- Updating `architecture-mcp.md` — that doc is reference-only and becomes obsolete once these planning docs are sealed.
- CLI work — locked spec defined here; CLI catches up upstream.
- Hard limits on meta size.

## Approach

This branch ships the MCP-side interface (wrappers + tests). The CLI is updated upstream to match. Test tiers structured so unit work is achievable now; e2e may depend on CLI catch-up.

Breaking change accepted — `--no-ids` removed, read-shape changes, version-bumped accordingly.

## Open Questions

- Path syntax confirmed dotted (`a.b.c`); namespace convention recommends `vendor:purpose` so `:` segments vendors without colliding with `.`
- Meta size limits — defer until a real workload hits trouble

## Delivery shape

Four sequential phases, each landing with its own tests (no separate test phase — tests are created/updated alongside the code they cover):

1. **Meta field + writers** — workitem shape change, `set_meta`, `patch_meta`, `add` accepting `meta`. Foundation; everything else depends on it.
2. **Reads** — `get`, `find_by_meta`, `meta` opt-in on `list` / `find` / `summary`, `--ids true|false` convention shift.
3. **Transitions** — atomic status + meta on `start` / `complete` / `reset`.
4. **Docs + version handshake** — usage docs for `meta`, namespace convention guide, new tools, read defaults, breaking-change note, plus the `version()` tool.

