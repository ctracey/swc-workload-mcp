# Notes

## Doc purpose

| Doc                | Purpose                                                        |
| ------------------ | -------------------------------------------------------------- |
| `plan.md`          | The why and what — goal, features, delivery shape, scope.      |
| `architecture.md`  | The how at a structural level — tech stack, layout, constraints. |
| `notes.md`         | Decisions, open questions, deferred items, references.         |
| `workload.md`      | The work item breakdown — what gets implemented and in what order. |
| `pipeline.md`      | How to verify the work — build, dev env, acceptance.           |
| `changelog.md`     | Append-only record of work landed during implementation.       |

## Solution decisions

- **Wrap the CLI, don't refactor it.** The MCP server invokes
  `bin/swc_workload` as a subprocess with `--json` and parses the result.
  Chosen because the CLI is already stable and well-tested; wrapping
  preserves that, keeps the CLI dep-free, and avoids a larger refactor.
- **Server name `swc-workload`; flat tool names.** MCP clients prefix tools
  with the server name (e.g. `mcp__swc-workload__add`), so tools don't need
  a redundant `workload_` prefix inside the server.
- **Repo is reshaped from plugin → MCP service.** The Claude Code plugin
  manifest is removed; project layout follows MCP service conventions
  (`pyproject.toml` + `swc_workload_mcp/` package + `bin/` for the CLI).
- **No automatic client registration.** README documents how to register
  the server with an MCP client; the repo doesn't ship a config that does
  it implicitly.
- **Test scenarios are documented.** We automate what we reasonably can
  (CLI tests stay; new MCP-layer tests cover the wrapper and the
  CLI-error → MCP-error mapping). Anything not reasonably automatable —
  e.g. real protocol round-trips with a live MCP client — is called out as
  a manual verification step in the README and `pipeline.md`.

## Open questions

- **MCP test depth.** Direct calls against the tool functions catch
  wrapper logic but skip the protocol layer. An in-process MCP client
  doing real protocol round-trips is closer to "tested it works
  end-to-end" but heavier. Resolution likely: direct-call unit tests
  for the wrapper + one or two protocol-level smoke tests via the SDK's
  in-memory client.

## Deferred decisions

- **Resource / prompt endpoints.** MCP supports resources and prompts in
  addition to tools. For now, scope is tools-only — workload browsing as
  a resource (e.g. expose `workload.json` to the client) can be revisited
  once the tool surface is in place.

## Parked (intent phase)

- (none)

## References

- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Existing CLI: `bin/swc_workload`
- Existing CLI tests: `tests/bin/`
