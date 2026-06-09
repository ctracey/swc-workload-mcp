# Usage

How to register `swc-workload-mcp` with an MCP client and confirm
it's working. For install and dev setup, see
[Development](development.md).

- [MCP Client Setup (Claude Code)](#claude-code-setup)
- [Verify MCP Server Setup](#verify-mcp-server-setup)
- [Example Scenario with Metadata](#example-scenario-with-metadata)
- [Meta Path Notation Reference](#meta-path-notation-reference)


## Register with an MCP client

Point an MCP client at the server. The launch command below is the
same shape any stdio-capable client accepts; each client has its own
place to put it. Claude Code is documented here.

## Claude Code Setup

### 1. Clone this repo

```sh
# clone this repo to be able to run this mcp server locally
git clone https://github.com/ctracey/swc-workload-mcp.git ~/claude-mcp-servers/swc-workload-mcp
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

### 4. Pre-warm the venv

Run this once after cloning so the venv is ready before Claude Code
first launches the server. Skipping this step is fine — the server
will self-heal on first startup — but the `/mcp` dialog may briefly
show **failed** while dependencies install.

```sh
MCP_SERVER_PATH=/path/to/swc-workload-mcp
uv sync --directory "$MCP_SERVER_PATH"
```

### 5. Register the MCP server

Register this MCP server.
With the project scope the MCP Server can be installed explicitly for each project that you want to use it for.

Run this from your project root (not the swc-workload-mcp location):
e.g. `cd ~/tmp/test_swc-mcp`

```sh
MCP_SERVER_PATH=/path/to/swc-workload-mcp
claude mcp add --scope project swc-workload -- "$MCP_SERVER_PATH/bin/start.sh"
```
* `MCP_SERVER_PATH` - full path to where you cloned the repo (DON'T use `~/`. Use full path)
* `--scope` - project scope only installs this mcp server for this folder so it's installed intentionally where this behaviour is desired.

This writes a `.mcp.json` to the current location (for project scope).
Use `--scope user` instead to register globally for your own machine — appropriate when the server
lives outside the project you're working in.

### Setup Notes:
`claude mcp add` only *records* the command; nothing runs at
registration time. Each Claude Code session execs the recorded
command as a child process and speaks MCP over stdio.

`start.sh` is a small wrapper that:
1. Runs `uv sync --quiet` — a near-instant no-op when dependencies are
   already installed, but will install them if missing (self-healing).
2. Execs `.venv/bin/swc-workload-mcp` directly for a fast, low-overhead startup.

If you've installed the server and CLI directly into a Python env
that's already on `PATH` (no `uv`), the command simplifies to just
`swc-workload-mcp` with no wrapper.

## Verify MCP Server Setup

In a fresh Claude Code session started inside the repo:

1. **Check it's connected.** Type `/mcp`. You should see
   `swc-workload` listed as **connected** with 15 tools. If it shows
   **failed** on first launch after skipping the pre-warm step, the
   server is still installing dependencies — restart the server from
   the `/mcp` dialog or start a new session. If it shows **failed**
   consistently, expand the entry to see stderr; the most common cause
   is the `swc-workload` CLI not being on `PATH`.
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

## Example Scenario with Metadata

Every work item carries a free-form JSON object called `meta`
(defaults to `{}`). Attach owner, estimate, priority, links, or
any structured data your workflow needs.

**Namespace your keys.** Use `vendor:purpose` colon-separated naming
so multiple tools or agents can share a workload without colliding —
e.g. `swc:owner`, `ci:run_id`, `issue:url`. Avoid dots in key names:
dots are the path separator used by `update` and `find`, so a dot
in a key name would be misinterpreted as a sub-path.

### Example flow

The workload for this scenario lives at `/tmp/meta-demo`. Mention it
once when you set up the session — the agent carries it forward.

#### 1. Check and initialise

> Check if there's a workload at `/tmp/meta-demo`. If not, initialise one there.

`exists` returns `false`, `init` creates the workload, a second
`exists` confirms `true`.

#### 2. Add items with metadata

Pass `meta` as a JSON object at creation time. Namespace your keys —
here `swc:` — to avoid collisions with other tools writing to this
workload.

> Add "Implement login page" with meta `{"swc:owner": "alice", "swc:priority": "high"}`.

> Add "Write unit tests" with meta `{"swc:owner": "bob", "swc:estimate": "2d"}`.

> Add "Deploy to staging" with meta `{"swc:owner": "alice", "swc:estimate": "1d"}`.

Each response includes the new item's id and number.

#### 3. Find by metadata

Presence check — all items that have `swc:owner` set:

> Find all items in the workload that have `swc:owner` set.

Pattern match — only alice's items (`pattern` uses `re.search`;
partial matches work):

> Find items in the workload where `swc:owner` matches alice.

#### 4. Fetch a single item

> Get item 1.

The response includes the full `meta` blob — useful for inspecting
all metadata before an update.

#### 5. Update metadata

Write a single field (path notation: `meta.<key>`):

> Set `swc:priority` to `low` on item 1.

Replace the entire meta object:

> Replace item 1's meta with `{"swc:owner": "alice", "swc:priority": "low", "swc:reviewed": true}`.

## Meta Path Notation Reference

The dot in `meta.swc:priority` is the path separator — everything
after the first dot is the key name within the meta object. This is
why keys must use `:` (not `.`) for namespacing.

| path | meaning |
|------|---------|
| `meta` | the whole meta object |
| `meta.owner` | top-level key `owner` |
| `meta.swc:owner` | top-level key `swc:owner` (namespaced) |
| `meta.tags[0]` | first element of `tags` array |
