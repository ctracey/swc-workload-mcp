## Pass 1 — 2026-05-25

- **Decision:** Bootstrapped the dev environment in `.venv/` (already
  gitignored) via `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`.
  The system Python is externally managed (PEP 668), so direct
  `pip3 install` is blocked. The venv is local-only — no project changes
  required.
- **Decision:** Stub `swc-workload` for tests is a single Python script
  parameterised by env vars (`STUB_STDOUT`, `STUB_STDERR`, `STUB_EXIT`,
  `STUB_RECORD_ARGV`) rather than one script per scenario. Each test
  sets the env vars before invoking the bridge, so the stub stays
  generic and the test intent stays in the test body. Avoids creating
  many near-identical scripts.
- **Decision:** Autouse `_isolate_env` fixture clears `SWC_WORKLOAD_BIN`
  and stub env vars at the start of every test, and overrides `PATH` to
  a non-existent directory so PATH-lookup tests are deterministic
  regardless of the host environment (the real `swc-workload` is on
  PATH at `/Users/tracer/.local/bin/`). Tests that need PATH lookup
  override `PATH` explicitly to point at their stub directory.
- **Decision:** Added a second test for REQ-07
  (`test_cli_response_error_truncates_long_stdout`) to cover the 500-char
  truncation behaviour documented in `solution.md`. The base REQ-07
  Gherkin only asserts "truncated copy"; an explicit length+ellipsis
  test pins down the contract.
- **Tried:** PATH lookup test was initially flaky concern because of
  the real `swc-workload` on the host PATH. Resolved via the autouse
  fixture that overrides `PATH` to `/nonexistent` by default; tests
  that want PATH lookup opt in by setting it explicitly.
- **Doc rename:** Replaced `swc_workload` (underscore, binary
  references) with `swc-workload` (hyphen) in `plan.md`,
  `architecture.md`, and `notes.md` per solution.md. Also fixed inline
  binary references in `swc_workload_mcp/__init__.py` (docstring
  pointed at a removed `bin/` path) and `pyproject.toml` `description`.
  Left Python package name `swc_workload_mcp` and CLI repo URL
  `swc-workload-cli` untouched. README is out of scope (work item 4).
- **All 8 Gherkin scenarios pass** (REQ-01 through REQ-07 + the
  truncation behaviour). Test file: `tests/mcp/test_bridge.py`. Bridge
  module: `swc_workload_mcp/bridge.py`.
