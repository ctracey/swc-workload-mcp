# Usage

How to register `swc-workload-mcp` with an MCP client and confirm
it's working. For install and dev setup, see
[Development](development.md).

## Register with an MCP client

Point an MCP client at the server. The launch command below is the
same shape any stdio-capable client accepts; each client has its own
place to put it. Claude Code is documented here.

### Claude Code

From the repo root:

```sh
claude mcp add --scope project swc-workload -- \
  uv run --directory "$(pwd)" swc-workload-mcp
```

This writes a `.mcp.json` to the repo root (project scope, shared
with anyone who clones the repo). Use `--scope user` instead to
register globally for your own machine — appropriate when the server
lives outside the project you're working in.

`claude mcp add` only *records* the command; nothing runs at
registration time. Each Claude Code session execs the recorded
command as a child process and speaks MCP over stdio. The pieces:

- `uv run` — `uv`'s "run inside the project venv" wrapper. It
  activates the venv before exec, which puts `.venv/bin/swc-workload`
  on `PATH` so the server can resolve the CLI.
- `--directory "$(pwd)"` — pins the project root, so the command
  works no matter what directory Claude Code launches it from.
- `swc-workload-mcp` — the console-script entry point that runs
  `swc_workload_mcp.server:main`.

If you've installed the server and CLI directly into a Python env
that's already on `PATH` (no `uv`), the command simplifies to just
`swc-workload-mcp` with no wrapper.

### Verify

In a fresh Claude Code session started inside the repo:

1. **Check it's connected.** Type `/mcp`. You should see
   `swc-workload` listed as **connected** with 12 tools. If it shows
   **failed**, expand the entry — the server's stderr is shown
   there; the most common cause is the `swc-workload` CLI not being
   resolvable, which `uv run` should fix.
2. **Exercise the golden path.** Ask the session something like:

   > Use swc-workload to init a workload at `/tmp/mcp-demo`, add an
   > item titled "First item", then list it.

   The tool calls should succeed and `/tmp/mcp-demo/workload.json`
   should exist on disk.
3. **Exercise an error path.** Ask:

   > Delete ref 999 from `/tmp/mcp-demo`.

   The underlying CLI will fail; the tool result surfaces a
   structured MCP error of the form *"swc-workload delete failed
   (exit N): …"* rather than a stack trace. That confirms the bridge
   is mapping CLI failures correctly.

For a more interactive way to poke at the server (independent of any
client), see [Test with MCP Inspector](test-with-mcp-inspector.md).
