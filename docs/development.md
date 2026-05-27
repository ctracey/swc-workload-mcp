# Development

Inner-loop guide for working on `swc-workload-mcp`: environment setup,
test tiers, and CI.

## Environment

Local dev relies on [`uv`](https://github.com/astral-sh/uv) and a
`Makefile` wrapper. See [Install](usage.md#install) for the one-shot
setup. After `make install` you have:

- `.venv/bin/swc-workload-mcp` — the MCP server entry point
- `.venv/bin/swc-workload` — the CLI, installed as a dev dependency
- The `swc_workload_mcp` Python module (editable install)
- `pytest` for the test suite

Run `make help` to list every Make target (`install`, `test`,
`test-unit`, `test-integration`, `test-e2e`, `dev`).

## Tests

The suite is organised into three tiers under `tests/mcp/`, one
folder per tier:

| Tier | Folder | Needs `swc-workload` CLI? | What it covers |
| --- | --- | --- | --- |
| Unit | `tests/mcp/unit/` | No | Bridge, tools, and server wiring against stubs |
| Integration | `tests/mcp/integration/` | **Yes** | All 12 tools end-to-end through a real MCP server subprocess and the real CLI |
| E2E | `tests/mcp/e2e/` | **Yes** | In-memory smoke of `init` through the wired FastMCP → tools → bridge → CLI chain |

The integration and e2e tiers **fail loudly** (not skip) if the CLI
isn't resolvable — that's deliberate, so a missing CLI is never
mistaken for a green run.

### Running the suite

After `make install` (see [Install](usage.md#install)), the CLI lives
at `.venv/bin/swc-workload`, so all three tiers can run without any
additional setup:

```sh
# everything
make test

# one tier at a time
make test-unit
make test-integration
make test-e2e
```

Each `make test*` target is a thin wrapper around `uv run pytest [path]`
— invoke pytest directly via `.venv/bin/pytest` or `uv run pytest` if
you need flags the Makefile doesn't expose.

## CI

`.github/workflows/ci.yml` runs the same three tiers as three
independent jobs on every PR against `main` and every push to `main`.
Each job sets up Python (from `.python-version`), sets up `uv`
(via `astral-sh/setup-uv`), then runs `make install` followed by
`make test-<tier>` — the exact same targets you'd run locally. Runner
is `ubuntu-latest` only.
