# swc-workload-mcp

![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/github/v/tag/ctracey/swc-workload-mcp?filter=v*&label=version)

A standalone [Model Context Protocol](https://modelcontextprotocol.io)
server that wraps the
[`swc-workload`](https://github.com/ctracey/swc-workload-cli) CLI so
MCP-aware AI agents (Claude Code, Claude Desktop, and other MCP
clients) can manage workload trees via structured tool invocations
instead of shelling out and parsing CLI output.

## What it does

Exposes 12 MCP tools — one per CLI op — over the standard MCP stdio
transport:

`init`, `exists`, `list`, `find`, `summary`, `add`, `rename`,
`delete`, `reset`, `start`, `complete`, `move`

Each tool translates its kwargs into the CLI's argv, invokes
`swc-workload <op> --json` as a subprocess, parses the JSON, and
returns it to the client. CLI errors map to structured MCP tool
errors with actionable hints.

## Documentation

- [Architecture](docs/architecture.md) — layer-by-layer design.
- [Usage](docs/usage.md) — register the server with an MCP client
  (Claude Code) and confirm it's working.
- [Development](docs/development.md) — prerequisites, install, tests,
  CI, and the release workflow.
- [Try with MCP Inspector](docs/try-with-mcp-inspector.md) — interactive
  end-to-end smoke test with the SDK's Inspector UI.
