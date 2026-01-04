from __future__ import annotations

import os
from pathlib import Path

from . import config
from .runner import run

class EnvError(ValueError):
    pass

def env_python(env_dir: Path) -> Path:
    win = env_dir / "Scripts" / "python.exe"
    posix = env_dir / "bin" / "python"
    if win.exists():
        return win
    if posix.exists():
        return posix
    raise EnvError(f"Invalid venv: python not found under {env_dir}")

def _py_runs(py: Path) -> bool:
    r = run([str(py), "-c", "import sys; print(sys.executable)"], timeout_sec=10, max_out=2000, max_err=2000)
    return r.exit_code == 0

def _pip_exists(py: Path) -> bool:
    r = run([str(py), "-m", "pip", "--version"], timeout_sec=10, max_out=2000, max_err=2000)
    return r.exit_code == 0

def create(env_dir: Path) -> Path:
    env_dir = env_dir.resolve()
    env_dir.parent.mkdir(parents=True, exist_ok=True)

    host_py = Path(os.sys.executable)

    # soft verify: as soon as venv python runs (and optionally pip exists), we can stop waiting
    def soft_verify() -> bool:
        try:
            vpy = env_python(env_dir)
        except Exception:
            return False
        if not _py_runs(vpy):
            return False
        # If you require pip seeded, keep this. If not, remove it.
        return _pip_exists(vpy)

    r = run(
        [str(host_py), "-m", "venv", str(env_dir)],
        timeout_sec=getattr(config, "TIMEOUT_VENV_CREATE", 180),
        max_out=20_000,
        max_err=20_000,
        idle_timeout_sec=None,
        soft_verify=soft_verify,
        soft_verify_start_after_sec=3,
        soft_verify_every_sec=2,
        soft_verify_fast_every_sec=1,
        soft_verify_grace_sec=3,
        soft_verify_kill_if_no_exit_after_sec=8,
        soft_success_hints=["Installing collected packages", "Installing pip", "successfully"],
    )

    # If command failed AND we didn't early-verify, treat as failure
    if r.exit_code != 0 and r.reason != "verified_early_exit":
        raise EnvError(f"venv creation failed (exit={r.exit_code}): {r.stderr[:1200]}")

    py = env_python(env_dir)

    # Final verification (deterministic)
    if not _py_runs(py):
        raise EnvError("venv python exists but is not runnable")

    if not _pip_exists(py):
        # optional: you can choose to seed pip separately here if needed
        raise EnvError("venv created but pip not available (ensurepip may have failed/hung)")

    return py
