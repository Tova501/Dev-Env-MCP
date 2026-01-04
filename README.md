# dev-env-mcp

Local MCP (Model Context Protocol) server for safe, structured Python env management.
It lets agents create and select venvs, run restricted pip actions, and freeze
requirements with predictable timeouts.

## Features

- `workspace_use` selects the active workspace root
- `env_create` and `env_use` manage venvs inside the workspace
- `pip` runs allowlisted pip actions (install/uninstall/list/show/check)
- `freeze` writes a pinned `requirements.txt` from the active venv

## Requirements

- Python 3.10+
- `uv` (recommended) or `pip`

## Run the server (stdio)

```bash
uv run server.py
```

This server is intended for stdio transport (MCP client).

## Security notes

- No arbitrary command execution
- Pip options are allowlisted
- Outputs are trimmed to avoid huge logs

## Project structure

```text
dev-env-mcp/
  dev_env_mcp/
  server.py
  pyproject.toml
  README.md
```
