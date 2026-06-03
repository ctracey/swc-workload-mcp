# Notes

## Decisions

### CLI dependency model
MCP locks the spec via wrappers + tests on this branch. The `swc-workload` CLI (separate repo) catches up to match. No stubbing or dual-repo coordination in this branch's scope.

### Drop `notes` as first-class field
Considered adding `notes` (free text per item) alongside `meta`. Dropped — callers can keep notes inside `meta` if needed. Reasons:
- `notes --append` would force MCP to know the value is a string, undermining `meta`'s opaque contract
- SWC (the primary consumer) already keeps free-text per work item in side-channel docs, so wouldn't even use it
- Removing the field shrinks scope and the tool surface

### No migration
Pre-existing workloads simply lack `meta`. Reads tolerate absence; new writes can add. Cheaper than designing a forward-migration; no caller is depending on the field being present yet.

### Boolean flag convention shift (`--no-ids` → `--ids false`)
Adopted across the surface: every boolean option takes an explicit value; defaults are documented. Replaces the asymmetric `--no-X` switch. Breaking change to `list` callers — accepted for this version.

### Atomic status + meta via existing transition tools
`start` / `complete` / `reset` each accept an optional `meta: {path: value, ...}` mapping so transition + multiple meta writes land together atomically. Single-write was considered and rejected because the real workflow event typically updates several fields at once (stage, timestamp, evidence ref, next-stage hint). Whole-namespace replace was considered and rejected because it wipes co-resident keys.

### Single `update_meta(ref, path, value)` writer
One path-based writer instead of separate `set_meta` (replace whole namespace) + `patch_meta` (shallow merge). Path-based addressing covers both cases naturally: empty path or first-segment path replaces the namespace; deeper path writes a specific key. Leaf semantics are always replace — no shallow-merge surprises. Earlier draft proposed two tools; collapsed to one during breakdown for smaller surface and uniform semantics.

### Read defaults
- `list` / `find` / `find_by_meta` / `summary` — meta omitted by default; opt-in via `meta: true`
- `get` — meta included by default; opt-out via `meta: false`

### `find_by_meta` matches via JSON navigation + regex
Single path-based tool with two modes:
1. Presence — `find_by_meta(path)` returns items where the dotted path resolves to any value (a namespace-only path is a special case of this).
2. Path + pattern — `find_by_meta(path, pattern)` returns items where the regex matches the string value at the path. Missing path → no match. Non-string at path → no match.

Path syntax matches `update_meta` — the MCP is uniformly path-aware and knows nothing about namespaces. Namespacing is a docs-driven caller convention.

### Version tool
New `version()` tool returns `{mcp: "<ver>", cli: "<ver>"}` so clients can detect compatibility across the breaking change.

### Architecture doc (`ref_architecture-mcp.md`)
Reference brief only — the artefact that started this conversation. Moved into `.swc/meta-attributes/` with the `ref_` prefix to mark it as historical context, not a live spec. Not updated as part of this work.

## Open questions

### Meta size limits
Raised in `ref_architecture-mcp.md`. Lean: no hard cap in this version; revisit if a real workload hits trouble.

### Concurrent transition writes
With multi-path `meta` on `start`/`complete`/`reset`, if two callers both transition the same item with overlapping paths, last-writer-wins per path. CLI-level atomicity is per single tool invocation, not across them. Document; no locking layer in this version.

## Deferred decisions

### Meta namespace convention guide
Documented as best practice in usage docs (recommended `vendor:purpose` naming, schema versioning by caller). Recommendation, not enforcement. Lives in docs work item.

### List-style selective namespace filter (`metaNamespaces: [...]`)
Considered for `list` / `find` opt-in. Dropped in favour of simpler `meta: bool`. Revisit only if payloads grow large enough that "all meta or none" becomes a problem.

### Cross-caller meta-path filtering on `list`
A `list({metaFilter: "ns.field == X"})` was raised in `architecture-mcp.md`. Out of scope — `find_by_meta` covers the cases we need without coupling `list` to caller schemas.

### Doc updates
Usage docs need updates for:
- `meta` field and namespace convention
- `version` tool
- New `get`, `set_meta`, `patch_meta`, `find_by_meta` tools
- Read defaults (meta inclusion table)
- Boolean flag convention (`--ids true|false`, `--meta true|false`)
- Breaking-change note for `--no-ids` removal

Captured as a work item, not a separate decision.

## Risks

- **CLI may not catch up.** This branch ships an interface; without the CLI implementing it, the wrappers can be unit-tested but not run end-to-end. Mitigation: design test tiers so unit tier doesn't depend on a CLI build; e2e tier may need to be marked skipped/pending until CLI ships.
- **Breaking `--no-ids` removal.** Any external caller of `list` with `--no-ids` will break. Mitigation: version bump + version tool to surface the change.

## References

- `ref_architecture-mcp.md` (this folder) — reference brief that started this conversation; historical only.
- `swc_workload_mcp/tools.py` — current MCP tool definitions (the surface this work extends).
- `swc_workload_mcp/bridge.py` — subprocess bridge to the CLI.

## Constraints

- MCP must remain ignorant of namespace contents — no validation, no inference of `status` from meta, no meta-path query operators beyond simple navigation + regex string match.
- Schema ownership (versioning, migrations, validation) lives with the caller, not the MCP.
- Reads must stay payload-aware: list-style reads omit `meta` by default; `get` includes it by default.
- Every MCP tool body must remain a thin argv-assembly + bridge call.

