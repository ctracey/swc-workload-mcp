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

- **CLI is an external dependency.** The `swc-workload` CLI lives in its
  own repo (<https://github.com/ctracey/swc-workload-cli>) and is
  installed independently. This repo ships only the MCP service. The
  bridge resolves the CLI binary via `SWC_WORKLOAD_BIN` env var →
  `shutil.which("swc-workload")` on PATH. Reason: keeps the MCP and CLI
  concerns cleanly separated and matches how MCP servers typically wrap
  pre-existing tools.
- **Graceful handling of missing CLI.** Server still starts if the CLI
  isn't found (so MCP clients can connect and see the error); a stderr
  warning is logged on startup, and tool calls return a structured MCP
  error pointing at the CLI repo. No raw `FileNotFoundError`.
- **Wrap the CLI, don't import it.** The MCP server invokes the CLI as
  a subprocess with `--json` and parses the result. Chosen because the
  CLI is a separately-versioned external dependency; subprocess keeps
  the boundary clean and means the MCP server has no knowledge of CLI
  internals.
- **Server name `swc-workload`; flat tool names.** MCP clients prefix
  tools with the server name (e.g. `mcp__swc-workload__add`), so tools
  don't need a redundant `workload_` prefix inside the server.
- **Repo is reshaped from plugin → MCP service.** The Claude Code plugin
  manifest and the legacy in-repo CLI source are removed; project layout
  follows MCP service conventions (`pyproject.toml` + `swc_workload_mcp/`
  package).
- **No automatic client registration.** README documents how to register
  the server with an MCP client; the repo doesn't ship a config that
  does it implicitly.
- **Test scenarios are documented.** We automate what we reasonably can
  (bridge unit tests, tool-level tests against a temp workload, and a
  protocol-level smoke test via the SDK's in-memory client). Anything
  not reasonably automatable — e.g. real protocol round-trips with a
  live MCP client — is called out as a manual verification step in the
  README and `pipeline.md`.

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
- **Version-compatibility check between MCP server and CLI.** No version
  pinning or compatibility check today. If the CLI's `--json` contract
  changes, the bridge breaks silently. Worth revisiting once both repos
  have stable version numbers.

## Parked (intent phase)

- (none)

## References

- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- swc-workload CLI repo: https://github.com/ctracey/swc-workload-cli
