# Usage

How to register `swc-workload-mcp` with an MCP client and confirm
it's working. For install and dev setup, see
[Development](development.md).

## Register with an MCP client

Point an MCP client at the server. The launch command below is the
same shape any stdio-capable client accepts; each client has its own
place to put it. Claude Code is documented here.

## Claude Code Setup

### 1. Clone this repo

```sh
# clone this repo to be able to run this mcp server locally
git clone https://github.com/ctracey/swc-workload-mcp.git
cd ~/swc-workload-mcp # or whichever local folder you choose
```

### 2. Install uv (python package manager)

```sh
# install uv if you don't have it (macOS):
brew install uv
# or platform-agnostic:
# curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Install swc-workload-cli

This MCP server is a wrapper for the swc-workload-cli tool

```sh
# install swc-workload-cli dependency
make install
```

### 4. Register the MCP server
Register this MCP server.
With the project scope the MCP Server can be installed explicity for each project that you want to use if for

Run this from your project root (not the swc-workload-mcp location):
e.g. `cd ~/tmp/test_swc-mcp`

register swc-workload mcp server for this project scope
```sh
# register swc-workload MCP Server for a specific project
claude mcp add --scope project swc-workload -- \
  uv run --directory "$(PATH_TO_SWC-WORKLOAD-MCP)" swc-workload-mcp
```
* `--directory` - location of where you cloned swc-workload-mcp repo (DON'T use `~/`. Use full path)
* `--scope` - project scope only installs this mcp server for this folder so its installed intentionally where this behaviour is desired.

This writes a `.mcp.json` to the current location (for project scope).
Use `--scope user` instead to register globally for your own machine — appropriate when the server
lives outside the project you're working in.

### Setup Notes:
`claude mcp add` only *records* the command; nothing runs at
registration time. Each Claude Code session execs the recorded
command as a child process and speaks MCP over stdio.

The pieces:
- `uv run` — `uv`'s "run inside the project venv" wrapper. It
  activates the venv before exec, which puts `.venv/bin/swc-workload`
  on `PATH` so the server can resolve the CLI.
- `--directory "$(PATH_TO_SWC-WORKLOAD-MCP)"` — pins the project root, so the command
  works no matter what directory Claude Code launches it from.
- `swc-workload-mcp` — the console-script entry point that runs
  `swc_workload_mcp.server:main`.

If you've installed the server and CLI directly into a Python env
that's already on `PATH` (no `uv`), the command simplifies to just
`swc-workload-mcp` with no wrapper.

## Verify MCP Server Setup

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
