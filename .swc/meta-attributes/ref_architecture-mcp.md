# Architecture — swc-workload-mcp

The MCP is a **generic workload store**. It tracks a list of work items with status, free-form notes, and an opaque namespaced metadata blob. It has no knowledge of SWC, workflow stages, or any other consumer-specific semantics.

## Goal

Provide a small, scenario-agnostic workload API so any orchestrator (SWC today, others later) can:

1. CRUD work items with stable identity and ordinal numbering.
2. Track high-level lifecycle via a simple `status` field.
3. Attach arbitrary structured state to a work item under a namespaced `meta` map, without the MCP needing to understand or validate it.

The MCP is deliberately ignorant of what callers put in `meta`. Schema ownership lives entirely with the caller.

## Workitem shape

```jsonc
{
  "id": "uuid-or-stable-id",
  "n": 4,                       // human-friendly ordinal
  "title": "Add meta support to MCP",
  "notes": "Free text. No structure imposed.",
  "status": "not-started" | "wip" | "done",
  "meta": {
    "<namespace>": { /* any valid JSON */ }
  }
}
```

Field roles:

- **`id`** — stable identifier, MCP-generated.
- **`n`** — human-friendly ordinal, reassigned on `move`.
- **`title`** — short label.
- **`notes`** — free text. Replaces the previous `description` field (a rename only; the bucket is unchanged).
- **`status`** — coarse lifecycle: `not-started` → `wip` → `done`. The MCP enforces this enum but does not infer transitions.
- **`meta`** — top-level object keyed by namespace. Each namespace's value is any valid JSON. The MCP stores it verbatim and does not validate structure.

## Meta: opaque, namespaced, caller-owned

Design contract:

- **Namespaced** — callers pick a namespace key (e.g. `swc-workflow-status`, `swc:notes-index`). The MCP treats namespaces as opaque strings.
- **Opaque** — the MCP does not parse, validate, or interpret any namespace's contents.
- **Caller-owned schema** — versioning, migrations, and validation are the caller's responsibility.
- **Payload-aware reads** — `meta` can grow, so list-style reads omit it by default and require opt-in (see `includeMeta` semantics below).

## Tool surface

### Core CRUD

| Tool       | Purpose                                          | Notes                                            |
| ---------- | ------------------------------------------------ | ------------------------------------------------ |
| `init`     | Initialise an empty workload artefact.           |                                                  |
| `add`      | Append a new work item.                          | Assigns next `n` and a fresh `id`.               |
| `list`     | List work items.                                 | Omits `meta` by default.                         |
| `find`     | Search by query (e.g. title substring).          | Returns **zero or more** matches. Omits `meta`.  |
| `get`      | Exact lookup by `n` or `id`.                     | Returns **one** item, `meta` **included** by default. Errors if not found. |
| `summary`  | Compact overview (counts, status breakdown).     | Generic; does not synthesise meta-derived views. |
| `exists`   | Existence check.                                 |                                                  |
| `rename`   | Update `title`.                                  |                                                  |
| `move`     | Reorder; reassigns `n`.                          |                                                  |
| `start`    | Transition `status` to `wip`.                    |                                                  |
| `complete` | Transition `status` to `done`.                   |                                                  |
| `reset`    | Transition `status` back to `not-started`.       |                                                  |
| `delete`   | Remove a work item.                              |                                                  |

### Meta writes

Two dedicated tools (preferred over overloading `update`):

- **`set_meta(target, namespace, value)`** — replace one namespace blob wholesale.
- **`patch_meta(target, namespace, partial)`** — shallow-merge `partial` into the namespace blob. Missing namespace is created.

Targets accept `n` or `id`. Both tools are no-ops for other namespaces.

### `find` vs `get`

Standard MCP split:

- **`find`** = many by query (search). Returns 0..N.
- **`get`** = one by identity (exact). Returns 1 or errors.

Confirmation against the current implementation is an open question (see below).

### `includeMeta` semantics

| Tool       | Default              | Opt-in                                                      |
| ---------- | -------------------- | ----------------------------------------------------------- |
| `list`     | meta omitted         | `includeMeta: true` or `metaNamespaces: ["ns1", "ns2"]`     |
| `find`     | meta omitted         | same                                                        |
| `summary`  | meta omitted         | same                                                        |
| `get`      | **meta included**    | `includeMeta: false` to opt out                             |

`metaNamespaces` is preferred over a boolean for list-style reads — keeps payloads small as meta grows and lets callers ask for exactly what they need.

## What the MCP does NOT do

- It does not interpret or validate any `meta` namespace contents.
- It does not infer `status` from `meta` (e.g. it won't flip to `done` because a caller's meta blob says a stage finished).
- It does not provide meta-path querying (e.g. `list({ metaFilter: "ns.field == X" })`). Callers filter client-side.
- It does not enforce ordering or dependencies between work items.
- It does not version or migrate caller-owned meta schemas.

## Migration

One-shot migration shipped with the version bump that introduces `meta`:

1. Rename `description` → `notes` on every existing work item.
2. Add `meta: {}` to every existing work item.

No data loss; no caller-visible changes beyond the field rename.

## Open questions

1. **Does current `find` already return multiple matches?** Verify against `swc-workload-mcp/tools.py` before locking the `find`/`get` split.
2. **Atomicity of status + meta writes.** A caller often wants `status` and a `meta` namespace update to land together (e.g. flipping to `done` while recording exit evidence). Options:
   - (a) Extend `complete`/`set_status` to accept an optional `meta` patch.
   - (b) Accept eventual consistency between two calls.
   - (c) Introduce a transactional `update` tool.

   Leaning (a) — narrow extension to existing tools.
3. **Dedicated `set_meta`/`patch_meta` vs overloading `update`.** Narrow tools are easier to reason about and document; one general tool means fewer surface items. Leaning narrow tools.
4. **`summary` tool surface.** Should `summary` ever synthesise meta-derived views? Likely no — keep `summary` generic; callers compute richer views from `get` results.
5. **Listing by stage / meta-path filter.** A `list({ metaFilter: ... })` would be useful but couples the MCP to caller-defined paths. Defer until a real cross-caller use case appears.
6. **Meta size limits.** Should the MCP cap per-namespace blob size or total `meta` size to protect the artefact? Probably soft cap with a warning rather than hard limit.
