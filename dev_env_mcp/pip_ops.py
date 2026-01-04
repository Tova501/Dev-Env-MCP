from __future__ import annotations

from pathlib import Path
import os
import time
from typing import Literal

from . import config
from .runner import run, RunResult

PipAction = Literal["install", "uninstall", "list", "show", "check", "freeze"]

class PipPolicyError(ValueError):
    pass

def _debug(msg: str) -> None:
    if not os.getenv("DEV_ENV_MCP_DEBUG"):
        return
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    line = f"[{ts}] [dev-env-mcp] {msg}\n"
    log_path = Path.cwd() / ".dev-env-mcp" / "debug.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.open("a", encoding="utf-8").write(line)

def _validate_options(options: list[str]) -> None:
    for opt in options:
        if opt.startswith("-") and not any(opt.startswith(p) for p in config.ALLOWED_PIP_OPTIONS_PREFIXES):
            raise PipPolicyError(f"Disallowed pip option: {opt}")

def _pip(
    env_py: Path,
    args: list[str],
    timeout: int,
    idle_timeout: int | None = None,
    success_markers: list[str] | None = None,
) -> RunResult:
    argv = [str(env_py), "-m", "pip", "--disable-pip-version-check", *args]
    _debug(f"pip call timeout={timeout}s argv={argv}")
    return run(
        argv,
        timeout_sec=timeout,
        max_out=config.MAX_STDOUT_CHARS,
        max_err=config.MAX_STDERR_CHARS,
        idle_timeout_sec=idle_timeout,
        success_markers=success_markers,
    )

def pip_install(env_py: Path, packages: list[str], options: list[str]) -> RunResult:
    _validate_options(options)
    return _pip(
        env_py,
        ["install", *options, *packages],
        timeout=config.TIMEOUT_PIP_INSTALL,
        success_markers=["Successfully installed", "Requirement already satisfied"],
    )

def pip_uninstall(env_py: Path, packages: list[str], options: list[str]) -> RunResult:
    # Always add -y to avoid interactive prompts; keep options allowlisted.
    _validate_options(options)
    return _pip(
        env_py,
        ["uninstall", "-y", *options, *packages],
        timeout=config.TIMEOUT_PIP_UNINSTALL,
        success_markers=["Successfully uninstalled"],
    )

def pip_list(env_py: Path) -> RunResult:
    return _pip(
        env_py,
        ["list", "--format=json"],
        timeout=config.TIMEOUT_PIP_OTHER,
        idle_timeout=config.TIMEOUT_PIP_IDLE_OTHER,
    )

def pip_show(env_py: Path, packages: list[str]) -> RunResult:
    return _pip(
        env_py,
        ["show", *packages],
        timeout=config.TIMEOUT_PIP_OTHER,
        idle_timeout=config.TIMEOUT_PIP_IDLE_OTHER,
    )

def pip_check(env_py: Path) -> RunResult:
    return _pip(
        env_py,
        ["check"],
        timeout=config.TIMEOUT_PIP_OTHER,
        idle_timeout=config.TIMEOUT_PIP_IDLE_OTHER,
    )

def pip_freeze(env_py: Path) -> RunResult:
    return _pip(
        env_py,
        ["freeze"],
        timeout=config.TIMEOUT_PIP_FREEZE,
        idle_timeout=config.TIMEOUT_PIP_IDLE_OTHER,
    )
