# Plan

## Goal / Why

Build a lightweight MCP server that wraps the externally-installed
`swc-workload` CLI so AI agents (Claude Code and other MCP clients) can
manage workload items via structured tool calls instead of shelling out and
parsing CLI output. Done when the MCP service is verified working
end-to-end via testing.

## Background

This repo previously shipped a Claude Code plugin that bundled both the
CLI and a plugin manifest. The CLI now lives in its own repo at
<https://github.com/ctracey/swc-workload-cli> and is installed
independently. This repo is being reshaped into a standalone MCP service
that wraps that externally-installed CLI, exposing each CLI op as an MCP
tool with structured arguments and results.

## Approach

- Reshape the repo into a Python MCP service: `pyproject.toml`, a
  `swc_workload_mcp/` package containing the server and bridge, and a
  rewritten `README.md`. Legacy plugin manifest and CLI source are
  removed.
- Build the MCP server with the official `mcp` Python SDK (FastMCP).
  Expose each CLI op as a flat-named tool. The server invokes the
  externally-installed `swc-workload` CLI as a subprocess with `--json`
  and translates the result into the MCP tool response. The CLI binary is
  resolved via `SWC_WORKLOAD_BIN` env var → PATH lookup. CLI errors map
  to MCP tool errors; a missing CLI surfaces an actionable error pointing
  at the CLI repo.
- Document test scenarios up front. Automate what's reasonably automatable
  (bridge unit tests + tool-level tests against a temp workload + a
  protocol-level smoke test via the SDK's in-memory client). Call out any
  manual verification steps in the README and `pipeline.md`.

See `architecture.md` for the detailed layout and `notes.md` for solution
decisions, open questions, and deferred items.

## Features

- `pyproject.toml` declaring the `mcp` SDK dep and a console-script entry
  point for the MCP server.
- `swc_workload_mcp/` package with a FastMCP server that exposes one tool
  per CLI op: `init`, `exists`, `list`, `find`, `summary`, `add`,
  `rename`, `delete`, `reset`, `start`, `complete`, `move`.
- CLI bridging: subprocess + `--json` parsing; binary resolved via
  `SWC_WORKLOAD_BIN` env var → PATH; CLI errors → MCP tool errors;
  missing CLI → actionable MCP error pointing at the CLI repo.
- Tests for the MCP layer (bridge, tools, protocol smoke test).
- Rewritten `README.md` covering: overview, architecture, server + tool
  naming convention, **CLI prerequisite + install link**, Python install
  instructions, MCP-client registration, test instructions, and getting
  started.

## Delivery shape

- **Phase 1 — Reshape the repo.** `pyproject.toml`, `swc_workload_mcp/`
  package skeleton, remove plugin manifest and legacy CLI source.
  Unblocks everything downstream; nothing functional yet.
- **Phase 2 — Build the MCP server.** Implement the FastMCP server with
  one tool per CLI op, wired through the subprocess + `--json` bridge
  with CLI-error and missing-CLI mapping.
- **Phase 3 — Tests for the MCP layer.** Bridge unit tests, tool-level
  tests against a temp workload, protocol-level smoke test via the SDK's
  in-memory client.
- **Phase 4 — Documentation.** Rewrite `README.md`: overview, prerequisite
  (CLI install), Python install, client registration, tests, getting
  started.
- **Phase 5 — End-to-end verification.** Manual smoke test against a real
  MCP client.

Priority: land Phases 1 + 2 first so the service can actually be exercised.

## Out of scope

- The CLI itself — installation, packaging, maintenance, and the CLI's
  own test suite are all the responsibility of the
  <https://github.com/ctracey/swc-workload-cli> repo.
- Automatic registration of the MCP server with any client (Claude Code,
  Claude Desktop, etc.). Registration is documented in the README and
  performed by the user.
- MCP resource and prompt endpoints — tools only for now (see
  `notes.md` deferred decisions).
- Version-compatibility checking between the MCP server and the CLI (see
  `notes.md` deferred decisions).

## Open Questions

See `notes.md` → Open questions.
