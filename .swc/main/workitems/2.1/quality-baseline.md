# Quality Baseline — 2.1: Subprocess bridge + error handling

## Commands run

- `python3 --version` — pass: Python 3.14.5
- `python3 -c "import swc_workload_mcp"` — pass: v0.1.0 imports
- `which swc-workload && swc-workload --version` — pass: installed at
  `/Users/tracer/.local/bin/swc-workload`, v1.1.2
- `pip3 show pytest` — fail: not installed
- `pip3 show mcp` — fail: not installed
- `pip3 show swc-workload-mcp` — fail: package not installed in editable mode

## Findings

The Python dev environment hasn't been bootstrapped yet. None of these
failures are pre-existing — they're the first-time setup steps that
remain after work item 1 (which set up `pyproject.toml` but didn't run
any install).

In-scope for this work item:
- Installing the package in editable mode so tests can import
  `swc_workload_mcp.bridge`.
- Installing pytest (declared in `[project.optional-dependencies].dev`).

`mcp` SDK is the project's only runtime dep but is not required for
2.1's bridge unit tests — it's used by the future server module.
Installing it via `pip install -e .[dev]` will pull it in as a side
effect, which is fine.

## Decisions

- The implementation agent bootstraps the dev environment as part of
  orient — runs `pip install -e .[dev]` (or equivalent) before writing
  tests. No pre-existing failures to suppress; baseline is just
  "nothing installed yet".
