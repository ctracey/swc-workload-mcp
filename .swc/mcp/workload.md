# mcp — convert swc-workload to an MCP service

## Work items

- [x] **1. Reshape the repo as an MCP service**
  - [x] 1.1. Add `pyproject.toml` (declare `mcp` dep, console-script entry point)
  - [x] 1.2. Create `swc_workload_mcp/` package skeleton (`__init__.py`, `__main__.py`)
  - [x] 1.3. Remove `.claude-plugin/plugin.json` and update `.gitignore` as needed

- [x] **2. Build the MCP server**
  - [x] 2.1. Subprocess bridge + error handling — resolve CLI (`SWC_WORKLOAD_BIN` env → PATH), invoke `swc-workload --json`, parse output; named exceptions for missing CLI / non-zero exit / parse failure; includes automated tests for the bridge layer
  - [x] 2.3. Define MCP tools, one per CLI op (`init`, `exists`, `list`, `find`, `summary`, `add`, `rename`, `delete`, `reset`, `start`, `complete`, `move`), mapping bridge exceptions to actionable MCP errors with hints
  - [x] 2.4. Wire tools into the FastMCP server with stdio transport

- [x] **3. Tests for the MCP layer**
  - [x] 3.2. Tool-level tests — each tool exercised against a temp workload
  - [x] 3.3. Protocol smoke test via the SDK's in-memory client

- [ ] **4. Rewrite the README**
  - [ ] 4.1. Overview + architecture + naming convention
  - [ ] 4.2. Install / dependency instructions
  - [ ] 4.3. MCP-client registration instructions
  - [ ] 4.4. Test instructions + getting started

- [ ] **5. End-to-end verification**
  - [ ] 5.1. Register the server in a real MCP client and confirm tools list
  - [ ] 5.2. Exercise `init` → `add` → `list` flow; verify `workload.json` matches CLI output
  - [ ] 5.3. Exercise an error path and confirm MCP error surfaces with a useful message

- [x] **6. Release automation & docs**
  - [x] 6.1. GitHub Actions pipeline for PR and main (lint, test)
  - [x] 6.2. Version sync — workflow to bump MCP service version, kept in sync with release tag
  - [x] 6.3. README badges, including a version-from-tag badge
