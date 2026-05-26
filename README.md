# swc-workload-mcp

A standalone [Model Context Protocol](https://modelcontextprotocol.io)
server that wraps the
[`swc-workload`](https://github.com/ctracey/swc-workload-cli) CLI so
MCP-aware AI agents (Claude Code, Claude Desktop, and other MCP
clients) can manage workload trees via structured tool invocations
instead of shelling out and parsing CLI output.

See [`docs/architecture.md`](docs/architecture.md) for the
layer-by-layer design.

## What it does

Exposes 12 MCP tools — one per CLI op — over the standard MCP stdio
transport:

`init`, `exists`, `list`, `find`, `summary`, `add`, `rename`,
`delete`, `reset`, `start`, `complete`, `move`

Each tool translates its kwargs into the CLI's argv, invokes
`swc-workload <op> --json` as a subprocess, parses the JSON, and
returns it to the client. CLI errors map to structured MCP tool
errors with actionable hints.

## Prerequisites

- **Python ≥ 3.10**
- **The `swc-workload` CLI** installed and on `PATH`. See
  <https://github.com/ctracey/swc-workload-cli> for install
  instructions. You can also point at an explicit binary via the
  `SWC_WORKLOAD_BIN` environment variable.

The server fails fast at startup if the CLI cannot be resolved.

## Install

```sh
git clone https://github.com/ctracey/swc-workload-mcp.git
cd swc-workload-mcp
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

The editable install gives you both the `swc-workload-mcp` console
script and the `swc_workload_mcp` Python module, plus the `pytest`
test dependency.

## Try it with MCP Inspector

[MCP Inspector](https://github.com/modelcontextprotocol/inspector) is
the SDK team's interactive UI for poking at MCP servers — list tools,
view their schemas, invoke them, and watch the responses. It's the
quickest way to confirm everything works end-to-end before wiring the
server up to a full client like Claude Code or Claude Desktop.

### Prerequisites for Inspector

- **Node.js ≥ 18** (Inspector ships as an npm package; `npx` fetches
  it on first run — no global install needed).

### Launch

From the repo root, with the venv created above:

```sh
npx @modelcontextprotocol/inspector .venv/bin/python -m swc_workload_mcp
```

That command:

1. Pulls and runs the Inspector via `npx`.
2. Spawns our MCP server (`python -m swc_workload_mcp`) as a child
   process that the Inspector communicates with over stdio.
3. Opens the Inspector UI in your browser (default
   <http://localhost:6274/>) and prints the URL to the terminal.

### What to look at

1. **Server connection.** After launch you should see status
   *Connected* alongside the server name `swc-workload`.
2. **Tools tab.** Lists all 12 registered tools with their schemas
   (kwargs, types, descriptions derived from each tool's docstring).
3. **Invoke `init`.**
   - Select `init` in the tool list.
   - Set `workload` to a path you don't mind being created, e.g.
     `/tmp/mcp-demo`.
   - Click *Run Tool*. You should see a JSON response, and
     `/tmp/mcp-demo/workload.json` will now exist on disk.
4. **Invoke `add`.**
   - Select `add`.
   - Set `workload=/tmp/mcp-demo` and `title="First item"`.
   - Click *Run Tool*. The response includes the new item's ref.
5. **Invoke `list`.** Same `workload`; no other kwargs needed. See the
   tree.
6. **Try an error path.** Select `delete`, set `ref` to a value that
   doesn't exist (e.g. `999`). The response surfaces a structured MCP
   tool error: *"swc-workload delete failed (exit N): …"* with the
   underlying CLI message.

### Verifying fail-fast startup via Inspector

To see the missing-CLI error path, point at a non-existent binary:

```sh
SWC_WORKLOAD_BIN=/nonexistent npx @modelcontextprotocol/inspector \
  .venv/bin/python -m swc_workload_mcp
```

The server will exit non-zero on startup; the Inspector surfaces the
stderr message:

```
swc-workload not found (searched: /nonexistent). Install from
https://github.com/ctracey/swc-workload-cli or set SWC_WORKLOAD_BIN
to the binary path.
```

## Tests

```sh
.venv/bin/pytest
```

Runs the full suite including:

- Bridge unit tests (real subprocesses against a parameterised Python
  stub).
- Tool wrapper unit tests (each of the 12 tools, bridge stubbed).
- Server tests, including an end-to-end smoke that boots the server
  in-memory and invokes `init` against a real `swc-workload`
  subprocess.

The end-to-end smoke fails loudly if `swc-workload` isn't installed —
it's there precisely to verify the wired chain works.
