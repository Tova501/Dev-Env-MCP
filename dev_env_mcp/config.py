from __future__ import annotations

from pathlib import Path

APP_DIRNAME = ".dev-env-mcp"
LOCAL_STATE_FILENAME = "state.json"
AUDIT_FILENAME = "audit.log"

# Global state stored in user's home directory, survives restarts and lets you switch workspaces.
GLOBAL_STATE_PATH = Path.home() / APP_DIRNAME / "global_state.json"

MAX_STDOUT_CHARS = 80_000
MAX_STDERR_CHARS = 80_000

TIMEOUT_VENV_CREATE = 1800
TIMEOUT_PIP_INSTALL = 6000
TIMEOUT_PIP_UNINSTALL = 3000
TIMEOUT_PIP_OTHER = 900
TIMEOUT_PIP_FREEZE = 900
TIMEOUT_PIP_IDLE_OTHER = 60

# Allowlist of pip options. Keep strict to avoid “agent does too much”.
ALLOWED_PIP_OPTIONS_PREFIXES = [
    "--no-deps",
    "--no-input",
    "--disable-pip-version-check",
    "--no-cache-dir",
    "--prefer-binary",
    "--only-binary",
    "--index-url",
    "--extra-index-url",
    "--trusted-host",
    "--find-links",
    "--require-hashes",
]
