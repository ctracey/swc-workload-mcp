# CLI Change Spec — `swc-workload`

Changes required in the `swc-workload` CLI (separate repo) to back the meta-attributes work in `swc-workload-mcp`. The MCP is a thin subprocess wrapper, so every capability below must be present in the CLI before the matching MCP wrapper can pass its integration / e2e tier.

This spec is the contract: MCP tests are written against these shapes. Deviations require re-aligning the wrappers or re-negotiating the spec.

## Versioning

This is a breaking change. Bump the CLI's version accordingly.

### `--version` flag

If not already present, support:

```
swc-workload --version
```

Output: a single version string (e.g. `0.4.0`) on stdout, exit 0. The MCP's new `version` tool shells out to read this.

---

## New workitem field: `meta`

Add a top-level `meta` object on every workitem. The CLI treats it as an **opaque JSON tree** — not a "namespace map" at the CLI level. Namespacing is a caller convention reinforced by docs, not a CLI-enforced structure.

```jsonc
{
  "id": "...",
  "n": 1,
  "title": "...",
  "status": "not-started" | "wip" | "done",
  "meta": { /* any valid JSON object, opaque, caller-owned */ }
}
```

Rules:

- `meta` is any valid JSON object. CLI does not interpret, validate, or constrain its shape.
- New items default to `meta: {}` if not provided.
- Pre-existing workload artefacts without `meta` are valid; reads tolerate absence.
- **No migration** — the CLI does not rewrite existing artefacts on first read with the new version.
- **Recommended caller convention (docs guidance, not enforced):** the first path segment is the caller's namespace, named `vendor:purpose` (e.g. `swc:workflow-status`). Avoid `.` in the namespace string so dotted-path parsing stays unambiguous.

## Path syntax

Used by `update-meta`, `find-by-meta`, and the transition `--meta` flag.

- **Dotted**: `a.b.c`. No JSONPath, no array indexing.
- An **empty path** (`""`) refers to the root of `meta` (the whole blob).
- Writes create intermediate objects on the path as needed.
- Reads / searches treat a missing intermediate as "no value at path" — not an error.

---

## New CLI subcommands

### `get`

```
swc-workload get <ref> [--meta true|false]
```

- Returns a single workitem by exact `ref` (number or hash).
- Errors (non-zero exit + stderr) if not found.
- `--meta` defaults to `true` for `get`.
- JSON output (`--json`) shape: a single workitem object (not an array).

### `update-meta`

```
swc-workload update-meta <ref> <path> <json-value>
```

- Writes `<json-value>` at the dotted `<path>` within the item's `meta`.
- `<path>` may be `""` (empty string) to replace the entire `meta` blob.
- `<json-value>` is parsed as JSON. The CLI does not interpret the parsed value.
- **Leaf semantics: replace, not merge.** If the value at `<path>` is an object, it is fully replaced — co-resident keys are not preserved.
- Creates intermediate objects on the path as needed.

### `find-by-meta`

```
swc-workload find-by-meta <path> [<pattern>] [--meta true|false]
```

Two modes, distinguished by whether `<pattern>` is supplied:

1. **Presence** — `find-by-meta <path>`: returns every item where the dotted `<path>` resolves to any value within `meta`. A namespace-only path is the common case.
2. **Path + pattern** — `find-by-meta <path> <pattern>`: returns every item where the dotted `<path>` resolves to a **string** value AND the regex `<pattern>` matches that string.

Semantics:

- Missing path → no match. Non-string value at path → no match. No errors raised for these cases.
- `--meta` defaults to `false` (omit meta from returned items unless requested).

---

## Changed subcommands

### `add`

```
swc-workload add <title> [--meta <json>] [<placement> <ref>]
```

- New optional `--meta <json>` flag. Value is a JSON object stored verbatim as the item's `meta`.

### `list`

```
swc-workload list [<ref>] [--filter ...] [--exclude ...] [--meta true|false] [--ids true|false]
```

- **New**: `--meta true|false` — include meta in items (default `false`).
- **New**: `--ids true|false` — show hash IDs (default `true`).
- **Removed**: `--no-ids` switch. Callers must migrate to `--ids false`.

### `find`

```
swc-workload find <keyword> [--meta true|false]
```

- New `--meta true|false` (default `false`).

### `summary`

```
swc-workload summary [--meta true|false]
```

- New `--meta true|false` (default `false`).

### `start` / `complete` / `reset`

```
swc-workload start    <ref> [--meta <json>]
swc-workload complete <ref> [--meta <json>]
swc-workload reset    <ref> [--meta <json>]
```

- New optional `--meta <json>` flag.
- Value is a JSON object of the form `{ "<path>": <value>, ... }`. Each entry is an `update-meta`-style write applied to the item's `meta`.
- Multiple path writes per call are supported.
- Status transition and **all** meta writes must land atomically — either every write applies (alongside the status flip) or none do.

---

## Unchanged subcommands

`init`, `exists`, `rename`, `delete`, `move` — no shape change. They continue to write `meta: {}` on newly-created items (`init` via fresh artefact) and preserve existing `meta` on items they touch.

---

## Read defaults — summary

| Subcommand     | Default `--meta` | Default `--ids` |
| -------------- | ---------------- | --------------- |
| `list`         | `false`          | `true`          |
| `find`         | `false`          | n/a             |
| `find-by-meta` | `false`          | n/a             |
| `summary`      | `false`          | n/a             |
| `get`          | `true`           | n/a             |

---

## Breaking changes — caller-visible

1. `--no-ids` on `list` removed; use `--ids false`.
2. JSON output for `list` / `find` / `summary` / `get` may include the new `meta` field depending on the new flag; existing parsers should tolerate the extra key.

---

## Out of scope for the CLI

- No data migration. Pre-existing workloads simply lack `meta` on existing items.
- No query language richer than dotted-path + regex on string values for `find-by-meta`.
- No meta-derived synthesis in `summary` (counts/percentages stay status-only).
- No hard cap on `meta` size in this version.
- No `notes` first-class field. Free text lives in `meta` if callers want it.
- No separate `set-meta` / `patch-meta` tools. The path-based `update-meta` covers both whole-namespace replace (empty path or first-segment path) and per-key writes (deeper path).
- No bulk-add. Each item creation is a separate `add` invocation, per standard one-at-a-time resource API convention.

---

## Test recommendations (CLI side)

- Round-trip: `add --meta '{"swc:status":{"stage":"plan"}}'` → `get <ref>` returns it.
- `update-meta` at various depths:
  - `update-meta <ref> "" '{...}'` replaces the whole `meta`.
  - `update-meta <ref> "swc:status" '{...}'` replaces just that namespace.
  - `update-meta <ref> "swc:status.stage" '"review"'` replaces just the leaf.
  - Leaf replace semantics confirmed for objects (no shallow merge with co-resident keys).
- `find-by-meta` presence vs path+pattern; missing path / non-string value → no match (no error).
- `start --meta '{"swc:status.stage":"impl","swc:status.started_at":"..."}'` writes both paths and flips status in the same atomic write to the artefact.
- `list --ids false` matches the pre-change `--no-ids` output.
- `list --meta true` includes the field; default omits it.
- Pre-existing artefact (no `meta` on items) loads cleanly; subsequent writes can add `meta`.
- `--version` outputs the new version string.
