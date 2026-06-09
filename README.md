# swc-workload MCP Server

![Linux](https://img.shields.io/badge/Linux-FCC624?style=flat&logo=linux&logoColor=black)
![macOS](https://img.shields.io/badge/macOS-000000?style=flat&logo=apple&logoColor=white)
![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/github/v/tag/ctracey/swc-workload-mcp?filter=v*&label=version)

This MCP Server works with [Sessionless Workload Context (SWC)](https://github.com/ctracey/swc),
to extract workload management for more efficient token usage with [SWC Workflows](https://github.com/ctracey/swc/blob/main/docs/usage.md#using-the-workflows).

A standalone [Model Context Protocol](https://modelcontextprotocol.io)
server that wraps the
[`swc-workload CLI`](https://github.com/ctracey/swc-workload-cli) so
MCP-aware AI agents (Claude Code, Claude Desktop, and other MCP
clients) can manage workload trees via structured tool invocations
instead of shelling out and parsing CLI output.

## What it does

Exposes 15 MCP tools over the standard MCP stdio transport. Each tool
translates its kwargs into the CLI's argv, invokes
`swc-workload <op> --json` as a subprocess, parses the JSON, and
returns it to the client. CLI errors map to structured MCP tool
errors with actionable hints.

| Tool | Description |
|------|-------------|
| `init` | Initialise a fresh workload at a folder
| `exists` | Check whether a workload exists at a folder
| `list` | Display the workload tree; filter by status, scope to a ref
| `summary` | Total / done / progress percentage
| `add` | Add a work item; optionally set `meta` at creation
| `get` | Fetch a single item including its full `meta` blob
| `find` | Find items by title keyword or meta path (with optional regex)
| `move` | Move a work item (relative or absolute position)
| `update` | Write to any field or `meta` path on a work item
| `rename` | Rename a work item
| `start` | Mark a work item as in-progress
| `complete` | Mark a work item as done
| `reset` | Mark a work item as not-started
| `delete` | Delete a work item and all descendants
| `version` | Return the MCP server version

## Documentation

- [Usage](docs/usage.md) — register the server with an MCP client
  (e.g Claude Code) and confirm it's working.
- [Architecture](docs/architecture.md) — layer-by-layer design.
- [Development](docs/development.md) — prerequisites, install, tests,
  CI, and the release workflow.
- [Test with MCP Inspector](docs/test-with-mcp-inspector.md) — interactive
  end-to-end smoke test with the SDK's Inspector UI.
