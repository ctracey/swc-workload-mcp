# swc-workload

A standalone Claude Code plugin that ships the `swc_workload` CLI — a
path-driven tree manager for `workload.json` files.

This is the binary half of [Sessionless Workload Context (SWC)](https://github.com/ctracey/swc),
extracted so other tools and plugins can depend on it without pulling in
the full SWC skills suite. The companion `swc` plugin uses this CLI for
its `swc workload <op>` wrapper.

## What it does

`swc_workload` manages a hierarchical workload tree persisted as
`workload.json`. It is purely a tree manager: it knows nothing about git
branches, context resolution, or `.swc/_meta.json`. Every operation
takes `--workload <folder>` and operates on `<folder>/workload.json`.

```
python3 bin/swc_workload <op> --workload <folder> [args]
```

Run `python3 bin/swc_workload --help` for the full subcommand list.

## Installation as a Claude Code plugin

Add this plugin via your preferred plugin marketplace, or clone it
directly into your plugins directory:

```
git clone https://github.com/ctracey/swc-workload-cli.git
```

Once loaded the CLI is available at `bin/swc_workload` inside the plugin
directory.

## Tests

```
pytest tests/
```

Tests invoke the CLI via subprocess against per-test temp workload
folders — no git or other plugin state required.

## Relationship to the `swc` plugin

The `swc` plugin (the full SWC suite) historically bundled its own copy
of this CLI. As of the refactor that introduced this package, `swc`
delegates to `swc-workload` when present and degrades gracefully when
not.
