# dev-env-mcp

A local **MCP (Model Context Protocol)** server that gives coding agents a **safe, structured way to manage Python environments** inside a project workspace.

Instead of letting an agent run arbitrary shell commands, `dev-env-mcp` exposes a small, well-defined API for:
- selecting a project workspace
- creating/using a virtual environment inside that workspace
- running **restricted** `pip` operations in that venv
- freezing pinned dependencies to `requirements.txt`

---

## Why this exists

Agents often struggle to reliably manage Python envs because:
- environment details are implicit (which interpreter? which venv?)
- shell command execution is powerful but risky
- installs can be slow/hang on Windows and cause inconsistent state

`dev-env-mcp` makes env management **explicit and verifiable**:
- all actions are scoped to a chosen workspace root
- the **active venv** is persisted per workspace

---

## Key concepts

### Workspace

A **workspace** is the project directory that the server is allowed to modify.  
All file paths are sandboxed to the active workspace root.

Select it with:

- `workspace_use(path)`

The active workspace is persisted globally so the server can remember it across restarts.

### Active venv

Inside each workspace, the server tracks which venv is currently active.  
The active venv is persisted in:

```
<workspace>/.dev-env-mcp/state.json
```

---

## Features

### Workspace management
- **`workspace_use(path)`**
  - Selects the active workspace root (typically where `pyproject.toml` / `.git` lives)
  - All subsequent operations are restricted to this workspace

### Virtual environment management
- **`env_create(path=".venv")`**
  - Creates a venv inside the active workspace and marks it as active
- **`env_use(path=".venv")`**
  - Selects an existing venv inside the active workspace and marks it as active

### Restricted pip operations
- **`pip(action, packages=None, options=None, confirm=False)`**
  - Actions: `install | uninstall | list | show | check`
  - Runs `python -m pip ...` using the **active venv python**
  - Pip options are allowlisted
  - Uninstall requires `confirm=true`

### Freezing dependencies
- **`freeze(path="requirements.txt")`**
  - Writes pinned requirements from the active venv to a file in the workspace

---

## Reliability and stability

- **Bounded execution:** per-action timeouts + capped stdout/stderr.
- **Post-condition verification:** if `pip`/`venv` hangs after the desired state is reached, the server verifies the state, stops the process, and returns success with an audit trail.
- **Process-tree termination:** stops the full subprocess tree to avoid orphaned children.

---

## Security model

This MCP is intentionally restrictive:

- ✅ No arbitrary command execution (no `shell=True`)
- ✅ Workspace sandboxing: all file paths must resolve inside the active workspace
- ✅ pip runs only via the active venv python (`<venv>/python -m pip`)
- ✅ pip options are allowlisted (unknown flags are rejected)
- ✅ destructive actions require explicit confirmation (`confirm=true` for uninstall)
- ✅ outputs are truncated to prevent log flooding
- ✅ audit log per workspace

Audit log:

```
<workspace>/.dev-env-mcp/audit.log
```

---

## Requirements

- Python 3.10+ (tested on Windows)
- `uv` recommended (fast runner + reproducible installs)
- Runtime dependencies (from `pyproject.toml`):
  - `mcp[cli]`
  - `psutil`

---

## Run the server (stdio transport)

This server is intended to be started by an MCP client (Codex / Cursor / Inspector) using **stdio**.

From the repo root:

```bash
uv run server.py
```

> If you run it manually, it will wait for MCP client messages on stdin.

---

## Example client workflow (tool-call sequence)

Typical agent flow:

1. Select the project workspace
2. Create a venv
3. Install dependencies
4. Freeze requirements

Example calls:

- `workspace_use("C:\\path\\to\\project")`
- `env_create(".venv")`
- `pip(action="install", packages=["requests", "python-dotenv"])`
- `freeze("requirements.txt")`

---

## Project structure

```text
dev-env-mcp/
  dev_env_mcp/
    server.py        # MCP tool definitions and orchestration
    workspace.py     # workspace root detection + sandbox path resolver
    state.py         # per-workspace + global persistent state
    audit.py         # JSONL audit logging
    runner.py        # safe subprocess runner (timeouts, caps, process-tree kill)
    venv_ops.py      # venv create/use helpers (+ optional soft verify)
    pip_ops.py       # allowlisted pip actions + verification-based early exit
    freeze.py        # requirements.txt generation
    config.py        # timeouts, caps, allowlists
  server.py          # entrypoint
  pyproject.toml
  README.md
```

---

## Notes / limitations

- This server intentionally supports a narrow set of operations.
- It does not modify global Python installations.
- It does not support conda/poetry by design.
- For very large packages, installs may still take time — the goal is to be safe, predictable, and verifiable.

---

## License

MIT
