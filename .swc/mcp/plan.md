# Plan

## Goal / Why

Build a lightweight MCP server that wraps the existing `swc_workload` CLI so AI
agents (Claude Code and other MCP clients) can manage workload items via
structured tool calls instead of shelling out and parsing CLI output. The
existing CLI is kept intact — the MCP service is a thin wrapper over it, not
a replacement. Done when the MCP service is verified working end-to-end via
testing.

## Background

The repo currently ships as a Claude Code plugin: it bundles `bin/swc_workload`
(a pure-stdlib Python CLI) with a `.claude-plugin/plugin.json` manifest. AI
agents that want to use the CLI today have to spawn it and parse its output.
Reshaping the repo as an MCP service lets agents invoke workload operations
as proper MCP tools, with structured arguments and results, while preserving
the CLI for any caller that still prefers it.

## Approach

- Reshape the repo from "Claude Code plugin" into a Python MCP service:
  add `pyproject.toml`, a `swc_workload_mcp/` package containing the server,
  and a rewritten `README.md`. Remove the plugin manifest.
- Build the MCP server with the official `mcp` Python SDK (FastMCP). Expose
  each CLI op as a flat-named tool. The server invokes `bin/swc_workload` as
  a subprocess with `--json` and translates the result into the MCP tool
  response. CLI errors are mapped to MCP tool errors.
- Document test scenarios up front. Automate what's reasonably automatable
  (wrapper unit tests + a small protocol-level smoke test via the SDK's
  in-memory client). Call out any manual verification steps in the README
  and `pipeline.md`.
- Keep the CLI and its existing subprocess tests unchanged.

See `architecture.md` for the detailed layout and `notes.md` for solution
decisions, open questions, and deferred items.

## Features

- `pyproject.toml` declaring the `mcp` SDK dep and a console-script entry
  point for the server.
- `swc_workload_mcp/` package with a FastMCP server that exposes one tool
  per CLI op: `init`, `exists`, `list`, `find`, `summary`, `add`, `rename`,
  `delete`, `reset`, `start`, `complete`, `move`.
- CLI bridging: subprocess + `--json` parsing, with CLI errors translated
  to MCP tool errors.
- Tests for the MCP layer alongside the kept-as-is CLI tests.
- Rewritten `README.md` covering: brief overview, architecture, server +
  tool naming convention, CLI-wrapper approach, install / dependency
  instructions, MCP-client registration instructions, test instructions,
  and getting started.

## Delivery shape

- **Phase 1 — Reshape the repo.** Add `pyproject.toml`, set up the
  `swc_workload_mcp/` package skeleton, remove `.claude-plugin/plugin.json`.
  Unblocks everything downstream; nothing functional yet.
- **Phase 2 — Build the MCP server.** Implement the FastMCP server with one
  tool per CLI op, wired through the subprocess + `--json` bridge with
  CLI-error → MCP-error mapping.
- **Phase 3 — Tests for the MCP layer.** Wrapper unit tests plus a
  protocol-level smoke test via the SDK's in-memory client.
- **Phase 4 — Documentation.** Rewrite `README.md`: overview, architecture,
  naming, install, client registration, tests, getting started.
- **Phase 5 — End-to-end verification.** Manual smoke test against a real
  MCP client.

Priority: land Phases 1 + 2 first so the service can actually be exercised.

## Out of scope

- Refactoring `bin/swc_workload` — kept exactly as-is.
- Automatic registration of the MCP server with any client (Claude Code,
  Claude Desktop, etc.). Registration is documented in the README and
  performed by the user.
- MCP resource and prompt endpoints — tools only for now (see
  `notes.md` deferred decisions).

## Open Questions

See `notes.md` → Open questions.
