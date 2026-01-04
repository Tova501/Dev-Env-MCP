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

# --- pip timeouts ---
TIMEOUT_PIP_INSTALL = 1800      # 30 min safety net
TIMEOUT_PIP_UNINSTALL = 600
TIMEOUT_PIP_OTHER = 90
TIMEOUT_PIP_FREEZE = 90
TIMEOUT_PIP_IDLE_OTHER = 15     # only for list/show/check/freeze

# --- soft verified-exit tuning (install/uninstall only) ---
SOFT_VERIFY_START_AFTER_SEC = 8          # don't verify immediately
SOFT_VERIFY_EVERY_SEC = 12              # normal verify cadence
SOFT_VERIFY_FAST_EVERY_SEC = 2          # after "success-looking" output
SOFT_VERIFY_GRACE_SEC = 12              # let pip exit naturally after verified
SOFT_VERIFY_KILL_IF_NO_EXIT_AFTER_SEC = 15  # then kill tree
VERIFY_SUBPROCESS_TIMEOUT_SEC = 20       # for env verification python -c


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
