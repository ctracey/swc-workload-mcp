# mcp — convert swc-workload to an MCP service

## Work items

- [x] **1. Reshape the repo as an MCP service**
  - [x] 1.1. Add `pyproject.toml` (declare `mcp` dep, console-script entry point)
  - [x] 1.2. Create `swc_workload_mcp/` package skeleton (`__init__.py`, `__main__.py`)
  - [x] 1.3. Remove `.claude-plugin/plugin.json` and update `.gitignore` as needed

- [ ] **2. Build the MCP server**
  - [ ] 2.1. Subprocess bridge — resolve CLI (`SWC_WORKLOAD_BIN` env → PATH), invoke `swc_workload --json`, parse output
  - [ ] 2.2. Error mapping — CLI non-zero exit + stderr → MCP tool error; missing CLI → actionable error pointing at swc-workload-cli
  - [ ] 2.3. Define MCP tools, one per CLI op (`init`, `exists`, `list`, `find`, `summary`, `add`, `rename`, `delete`, `reset`, `start`, `complete`, `move`)
  - [ ] 2.4. Wire tools into the FastMCP server with stdio transport

- [ ] **3. Tests for the MCP layer**
  - [ ] 3.1. Wrapper unit tests — subprocess bridge + error mapping
  - [ ] 3.2. Tool-level tests — each tool exercised against a temp workload
  - [ ] 3.3. Protocol smoke test via the SDK's in-memory client

- [ ] **4. Rewrite the README**
  - [ ] 4.1. Overview + architecture + naming convention
  - [ ] 4.2. Install / dependency instructions
  - [ ] 4.3. MCP-client registration instructions
  - [ ] 4.4. Test instructions + getting started

- [ ] **5. End-to-end verification**
  - [ ] 5.1. Register the server in a real MCP client and confirm tools list
  - [ ] 5.2. Exercise `init` → `add` → `list` flow; verify `workload.json` matches CLI output
  - [ ] 5.3. Exercise an error path and confirm MCP error surfaces with a useful message
