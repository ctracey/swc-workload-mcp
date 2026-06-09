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
   `swc-workload` listed as **connected** with 15 tools. If it shows
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

## Working with meta fields

Every work item carries a free-form JSON object called `meta`
(defaults to `{}`). Attach owner, estimate, priority, links, or
any structured data your workflow needs.

**Namespace your keys.** Use `vendor:purpose` colon-separated naming
so multiple tools or agents can share a workload without colliding —
e.g. `swc:owner`, `ci:run_id`, `issue:url`. Avoid dots in key names:
dots are the path separator used by `update` and `find`, so a dot
in a key name would be misinterpreted as a sub-path.

### Example flow

#### 1. Check and initialise

```
exists  workload=/tmp/meta-demo
→ false

init    workload=/tmp/meta-demo
→ {"initialised": true}

exists  workload=/tmp/meta-demo
→ true
```

#### 2. Add items with metadata

Pass `meta` as a JSON object at creation time. Namespace your keys —
here `swc:` — to avoid collisions with other tools writing to this
workload.

```
add  workload=/tmp/meta-demo
     title="Implement login page"
     meta={"swc:owner": "alice", "swc:priority": "high"}

add  workload=/tmp/meta-demo
     title="Write unit tests"
     meta={"swc:owner": "bob", "swc:estimate": "2d"}

add  workload=/tmp/meta-demo
     title="Deploy to staging"
     meta={"swc:owner": "alice", "swc:estimate": "1d"}
```

#### 3. Find by metadata

Presence check — all items that have `swc:owner` set:

```
find  workload=/tmp/meta-demo  meta=swc:owner
→ [all three items]
```

Pattern match — items where `swc:owner` matches `alice` (regex,
`re.search`; partial matches work):

```
find  workload=/tmp/meta-demo  meta=swc:owner  pattern=alice
→ [{"title": "Implement login page", ...}, {"title": "Deploy to staging", ...}]
```

#### 4. Fetch a single item

```
get  workload=/tmp/meta-demo  ref=1
→ {
    "id": "a1b2c3d", "number": "1",
    "title": "Implement login page",
    "status": "not-started",
    "meta": {"swc:owner": "alice", "swc:priority": "high"}
  }
```

`get` always returns the full `meta` blob.

#### 5. Update metadata

Write a single field — path is `meta.<key>`:

```
update  workload=/tmp/meta-demo  ref=1
        path=meta.swc:priority  value=low
```

Replace the entire meta object — path is `meta`, value must be a
JSON object:

```
update  workload=/tmp/meta-demo  ref=1
        path=meta
        value={"swc:owner": "alice", "swc:priority": "low", "swc:reviewed": true}
```

### Path notation reference

The dot in `meta.swc:priority` is the path separator — everything
after the first dot is the key name within the meta object. This is
why keys must use `:` (not `.`) for namespacing.

| path | meaning |
|------|---------|
| `meta` | the whole meta object |
| `meta.owner` | top-level key `owner` |
| `meta.swc:owner` | top-level key `swc:owner` (namespaced) |
| `meta.tags[0]` | first element of `tags` array |
