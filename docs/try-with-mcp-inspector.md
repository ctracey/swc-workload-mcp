# Try it with MCP Inspector

[MCP Inspector](https://github.com/modelcontextprotocol/inspector) is
the SDK team's interactive UI for poking at MCP servers — list tools,
view their schemas, invoke them, and watch the responses. It's the
quickest way to confirm everything works end-to-end before wiring the
server up to a full client like Claude Code or Claude Desktop.

## Prerequisites

- A working dev install (see [Install](development.md#install)).
- **Node.js ≥ 18** (Inspector ships as an npm package; `npx` fetches
  it on first run — no global install needed).

## Launch

From the repo root, with the venv created via `make install`:

```sh
make dev
```

That target runs `npx @modelcontextprotocol/inspector uv run swc-workload-mcp`,
which:

1. Pulls and runs the Inspector via `npx` (Node's fetch-and-run; no
   global install needed).
2. Spawns our MCP server via `uv run swc-workload-mcp` as a child
   process. `uv run` activates the project venv first so the server
   can find its bundled `swc-workload` CLI on `PATH`.
3. Opens the Inspector UI in your browser (default
   <http://localhost:6274/>) and prints the URL to the terminal.

## What's actually running

Once you launch, there are **two long-running processes** (plus a
short-lived one per tool call):

```
Browser (you)
   │  HTTP/WebSocket
   ▼
[Inspector — Node]                  ← long-running; hosts the UI on :6274
   │                                  and acts as an MCP client
   │  stdio (MCP JSON-RPC)
   ▼
[swc-workload-mcp — Python]         ← long-running; speaks MCP, doesn't
   │                                  open a port of its own
   │  subprocess.run("swc-workload …")
   ▼
[swc-workload — Python]             ← ephemeral, one per tool invocation
```

The MCP server uses **stdio transport** — no network port — which is
the same way real MCP clients like Claude Code and Claude Desktop will
launch it in production. The Inspector is just acting as a test
client with a browser UI on top.

## What to look at

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

## Verifying fail-fast startup via Inspector

To see the missing-CLI error path, point at a non-existent binary:

```sh
SWC_WORKLOAD_BIN=/nonexistent npx @modelcontextprotocol/inspector \
  uv run swc-workload-mcp
```

The server will exit non-zero on startup; the Inspector surfaces the
stderr message:

```
swc-workload not found (searched: /nonexistent). Install from
https://github.com/ctracey/swc-workload-cli or set SWC_WORKLOAD_BIN
to the binary path.
```
