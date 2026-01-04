from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os
import time

from . import config

@dataclass
class LocalState:
    """
    State stored INSIDE a workspace at: <workspace>/.dev-env-mcp/state.json
    """
    active_env: str | None = None  # stored as RELATIVE path like ".venv"
    updated_at_utc: str | None = None

@dataclass
class GlobalState:
    """
    State stored in HOME: ~/.dev-env-mcp/global_state.json
    This allows the server to remember the last selected workspace across restarts.
    """
    active_workspace: str | None = None
    updated_at_utc: str | None = None

# In-memory cache for this server process
_MEM_ACTIVE_WORKSPACE: Path | None = None
_MEM_LOCAL_STATE: dict[str, LocalState] = {}  # key: workspace_root str


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)

def _local_state_path(workspace_root: Path) -> Path:
    return workspace_root / config.APP_DIRNAME / config.LOCAL_STATE_FILENAME

def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def _dump_json(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


# -------- Global state (home) --------

def load_global_state() -> GlobalState:
    p = config.GLOBAL_STATE_PATH
    if not p.exists():
        return GlobalState()

    try:
        raw = _load_json(p)
        return GlobalState(
            active_workspace=raw.get("active_workspace"),
            updated_at_utc=raw.get("updated_at_utc"),
        )
    except Exception:
        # fail safe: ignore corrupted global state
        return GlobalState()

def save_global_state(gs: GlobalState) -> None:
    gs.updated_at_utc = _utc_now()
    _atomic_write_text(config.GLOBAL_STATE_PATH, _dump_json(asdict(gs)))

def set_active_workspace(workspace_root: Path) -> None:
    global _MEM_ACTIVE_WORKSPACE
    _MEM_ACTIVE_WORKSPACE = workspace_root.resolve()

    gs = load_global_state()
    gs.active_workspace = str(_MEM_ACTIVE_WORKSPACE)
    save_global_state(gs)

def get_active_workspace() -> Path | None:
    """
    Returns active workspace in this order:
    1) in-memory (current process)
    2) global state from home dir (last selected workspace)
    """
    global _MEM_ACTIVE_WORKSPACE
    if _MEM_ACTIVE_WORKSPACE is not None:
        return _MEM_ACTIVE_WORKSPACE

    gs = load_global_state()
    if gs.active_workspace:
        p = Path(gs.active_workspace).resolve()
        if p.exists():
            _MEM_ACTIVE_WORKSPACE = p
            return p

    return None


# -------- Local state (per-workspace) --------

def load_local_state(workspace_root: Path) -> LocalState:
    """
    Loads local state for this workspace.
    Cached in-memory per workspace for speed.
    """
    key = str(workspace_root.resolve())
    if key in _MEM_LOCAL_STATE:
        return _MEM_LOCAL_STATE[key]

    p = _local_state_path(workspace_root)
    if not p.exists():
        st = LocalState()
        _MEM_LOCAL_STATE[key] = st
        return st

    try:
        raw = _load_json(p)
        st = LocalState(
            active_env=raw.get("active_env"),
            updated_at_utc=raw.get("updated_at_utc"),
        )
        _MEM_LOCAL_STATE[key] = st
        return st
    except Exception:
        st = LocalState()
        _MEM_LOCAL_STATE[key] = st
        return st

def save_local_state(workspace_root: Path, st: LocalState) -> None:
    st.updated_at_utc = _utc_now()
    p = _local_state_path(workspace_root)
    _atomic_write_text(p, _dump_json(asdict(st)))

def set_active_env(workspace_root: Path, env_rel: str) -> None:
    st = load_local_state(workspace_root)
    st.active_env = env_rel
    save_local_state(workspace_root, st)
