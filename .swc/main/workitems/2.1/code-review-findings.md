# Code Review Findings — 2.1: Subprocess bridge + error handling — 2026-05-25

## Summary

The bridge implementation is tight, idiomatic, and well-aligned with `specs.md` and `solution.md`. A single 161-line module exposes one public function (`invoke`) and a four-level exception hierarchy with structured attributes. Subprocess invocation is safe (no `shell=True`, no stdin, explicit `check=False`), binary resolution mirrors the spec exactly (env var with existence + executable check, then `shutil.which`), and the JSON parse path correctly chains the underlying `JSONDecodeError` via `raise ... from exc`. The test suite drives real subprocesses against a parameterised stub — no mocking — with one test per Gherkin scenario plus an explicit truncation-length test. Findings below are all minor; nothing blocks shipping.

## Findings

### F-01 — info: stderr is not truncated in `CLIExecutionError`

**Severity:** info
**Location:** `swc_workload_mcp/bridge.py:67-72`
**Description:** `CLIResponseError` truncates `raw_stdout` to 500 chars to keep exception/log output legible, but `CLIExecutionError` embeds the full `stderr.strip()` via `!r` in its message and stores the entire stderr verbatim. If a CLI op ever emits a large stderr (stack trace, debug log, accidental binary dump), the exception message and any log surface that re-renders it will be unwieldy. Solution.md only spec'd truncation for stdout, so this is consistent with the agreed design — flagging as an observation, not a defect.
**Suggestion:** Consider applying the same `_truncate` helper to `stderr` when constructing the exception message (keep the full string on the attribute for diagnostics, truncate only in `str(exc)`), or leave as-is and revisit if real CLI output proves noisy at the tool layer (2.3).

### F-02 — info: empty `SWC_WORKLOAD_BIN` silently falls through to PATH lookup

**Severity:** info
**Location:** `swc_workload_mcp/bridge.py:105-109`
**Description:** `os.environ.get(ENV_VAR)` followed by `if env_value:` treats an empty-string env var the same as unset, falling through to `shutil.which`. This is almost certainly the right behaviour (matches `env SWC_WORKLOAD_BIN= my-cmd` shell semantics), but it's not explicitly covered by the spec or a test. A reader could reasonably expect the empty string to either raise `CLINotFoundError` or be treated as a misconfiguration.
**Suggestion:** Either add a one-line test pinning the "empty == unset" behaviour, or add a short docstring note to `_resolve_binary` so the intent is explicit.

### F-03 — info: `os.access(..., os.X_OK)` semantics on edge filesystems

**Severity:** info
**Location:** `swc_workload_mcp/bridge.py:107`
**Description:** `os.access(env_value, os.X_OK)` can give misleading results when running as root (returns True for files that won't actually execute) or on filesystems that don't fully model POSIX permissions (some NFS/SMB mounts, ACL-only volumes). For the documented use case (local dev/CI, test stubs) this is a non-issue and the alternative — letting `subprocess.run` raise `PermissionError` — would surface as a different exception type than the spec mandates.
**Suggestion:** No change needed. If the bridge later needs to support exotic deployment environments, consider catching the `PermissionError`/`OSError` from `subprocess.run` and re-raising as `CLINotFoundError` carrying the resolved path.

### F-04 — info: README and pipeline doc drift flagged by the agent

**Severity:** info
**Location:** `README.md`, `.swc/mcp/pipeline.md` (per `summary.md` scope flags)
**Description:** The summary explicitly flags two non-2.1 doc gaps (README still references the removed plugin layout; pipeline `## Build` doesn't mention venv activation). These are out of scope per the agent's note and are tracked for later work items (4 and CI/docs respectively).
**Suggestion:** Confirm with the workload owner that these are captured for work item 4 / CI docs, then ignore here.

## Verdict

**WARN**

No blocking issues; three minor observations on the bridge plus one documentation-drift note carried over from the agent's own scope flags.
