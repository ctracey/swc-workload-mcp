# Code Review Findings — 6.1: GitHub Actions pipeline for PR and main (lint, test) — 2026-05-27

## Summary

The work item lands cleanly and behaviour-preservingly. The
`tests/mcp/` restructure into `unit/`, `integration/`, `e2e/` is
executed via `git mv` (history preserved), each tier has an empty
`__init__.py` matching the existing pattern, the integration-only
`conftest.py` moves down into the integration tier so its fixtures
cannot leak, and the REQ-09 e2e smoke is extracted into
`tests/mcp/e2e/test_smoke.py` with its own copy of `_isolate_env`,
`anyio_backend`, and `_REAL_CLI_PATH` capture exactly as agreed in
solution.md. Test totals match the quality baseline test-for-test
(129 passed, 7 skipped). `.python-version` contains exactly
`3.14.5\n`. `.github/workflows/ci.yml` defines the three required
jobs on `ubuntu-latest`, triggered by `pull_request` against `main`
and `push` to `main`, with a sensible `concurrency:` group to cancel
in-flight runs. The CLI install via `pipx` lands only on the
`integration` and `e2e` jobs as specified, and `$HOME/.local/bin` is
exported to `$GITHUB_PATH` so the next steps can resolve
`swc-workload`. Open concerns are CI-hygiene-level — supply-chain
pinning for both GitHub Actions and the unpinned `pipx install` of
the CLI — none of which block the work item.

## Findings

### F-01 — warn: `pipx install` of CLI is unpinned (tracks HEAD)

**Severity:** warn
**Location:** `.github/workflows/ci.yml:46`, `.github/workflows/ci.yml:69`
**Description:** Both the `integration` and `e2e` jobs run
`pipx install git+https://github.com/ctracey/swc-workload-cli.git`
with no `@<ref>` suffix, so every CI run pulls whatever is at the
default branch HEAD of the CLI repo. This couples the green/red of
this repo's CI to out-of-band changes in another repo: a breaking
change merged to `ctracey/swc-workload-cli` will start failing PRs
here with no commit in this repo to point at. It also means CI is
non-reproducible across reruns — a rerun on the same SHA can yield
a different result.
**Suggestion:** Pin the CLI to a known-good ref —
`pipx install git+https://github.com/ctracey/swc-workload-cli.git@<tag-or-sha>` —
and bump it deliberately when the CLI moves. If a moving target is
intentional during early development, leave it but document the
trade-off in `notes.md` and tracked tech debt so future failures
have a known cause to look at first.

### F-02 — info: GitHub Actions are major-tag-pinned, not SHA-pinned

**Severity:** info
**Location:** `.github/workflows/ci.yml:19`, `.github/workflows/ci.yml:22` (and the duplicates in `integration` / `e2e` jobs)
**Description:** `actions/checkout@v4` and `actions/setup-python@v5`
are pinned to a mutable major-version tag. A supply-chain compromise
or a regression in a re-published minor would silently affect this
workflow. SHA-pinning is the OpenSSF-recommended posture for
third-party actions.
**Suggestion:** If supply-chain hygiene is a concern for this repo,
replace tag pins with full commit SHAs (with the tag in a trailing
comment) and adopt Dependabot's `github-actions` ecosystem to bump
them. Acceptable to defer if the project's threat model treats tag
pins as good enough — note in tech debt either way.

### F-03 — info: jobs have no `timeout-minutes`

**Severity:** info
**Location:** `.github/workflows/ci.yml` — all three jobs
**Description:** None of the three jobs set `timeout-minutes`, so a
hung step (network stall during `pipx install`, a deadlocked stdio
test, a runaway subprocess) falls back to GitHub's 360-minute
default. The current suite runs in ~15s locally; a 5–10 minute cap
would catch genuine hangs early without false positives on slow
runners.
**Suggestion:** Add `timeout-minutes: 10` (or similar) to each job
under `runs-on:`. Small change, large floor on worst-case runner
spend.

### F-04 — info: `pipx` availability is an implicit runner contract

**Severity:** info
**Location:** `.github/workflows/ci.yml:46`, `.github/workflows/ci.yml:69`
**Description:** The CLI install step assumes `pipx` is preinstalled
on the `ubuntu-latest` runner image. This is true today, but
GitHub's runner-image inventory is a moving target — `pipx` has
been preinstalled on `ubuntu-22.04`/`ubuntu-24.04` but is not part
of any documented stability contract. A surprise removal would
break `integration` and `e2e` with a confusing "pipx: command not
found" rather than a clean diagnostic.
**Suggestion:** Either (a) add `python -m pip install --user pipx`
before the `pipx install` line as a belt-and-braces no-op when
already present, or (b) accept the runner contract and pin to a
specific runner image (`runs-on: ubuntu-24.04`) so an image
upgrade is opt-in rather than ambient. The current code is fine for
now; this is a "future debugging time" investment.

### F-05 — info: `_isolate_env` duplicated across `unit/test_server.py` and `e2e/test_smoke.py`

**Severity:** info
**Location:** `tests/mcp/unit/test_server.py:26`, `tests/mcp/e2e/test_smoke.py:29`
**Description:** Both files carry an identical autouse `_isolate_env`
fixture (delete `SWC_WORKLOAD_BIN`, set `PATH=/nonexistent`). This
is a deliberate decision per `context.md` ("the two files
intentionally each carry their own `_isolate_env` because they live
in different tier folders and there is no shared conftest at
`tests/mcp/` any more") and the solution.md decision to keep no
conftest at `tests/mcp/`. Worth flagging as a known duplication so a
future reader doesn't refactor it back into a shared conftest
without understanding why it was split. No action needed unless a
third tier file appears.
**Suggestion:** Leave as-is. If a third tier ends up needing the
same fixture, revisit whether a small shared helper module
(`tests/mcp/_shared.py` imported explicitly, not a conftest) is
warranted.

## Verdict

**WARN**

Restructure and workflow are correct and behaviour-preserving; the
single substantive concern is the unpinned `pipx install` of the
CLI (F-01), which is an operational risk rather than a code defect
and is acceptable to ship if tracked.
