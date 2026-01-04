from __future__ import annotations

from pathlib import Path
import json
from typing import Literal

from . import config
from .runner import run, RunResult

PipAction = Literal["install", "uninstall", "list", "show", "check", "freeze"]


class PipPolicyError(ValueError):
    pass


def _validate_options(options: list[str]) -> None:
    for opt in options:
        if opt.startswith("-") and not any(opt.startswith(p) for p in config.ALLOWED_PIP_OPTIONS_PREFIXES):
            raise PipPolicyError(f"Disallowed pip option: {opt}")


def _parse_specs(specs: list[str]) -> list[tuple[str, str | None]]:
    """
    Minimal parser: supports 'name' or 'name==version'.
    """
    out: list[tuple[str, str | None]] = []
    for s in specs:
        s = s.strip()
        if not s:
            continue
        if "==" in s:
            name, ver = s.split("==", 1)
            out.append((name.strip(), ver.strip()))
        else:
            out.append((s, None))
    return out


def _verify_installed(env_py: Path, specs: list[str]) -> bool:
    """
    Verify requested top-level packages are installed in the venv.
    If 'name==ver' is given, verify exact version.
    """
    parsed = _parse_specs(specs)
    if not parsed:
        return True

    payload = json.dumps(parsed)
    code = r"""
import json, sys
from importlib import metadata

parsed = json.loads(sys.argv[1])
ok = True
for name, ver in parsed:
    try:
        v = metadata.version(name)
        if ver is not None and v != ver:
            ok = False
    except metadata.PackageNotFoundError:
        ok = False
print("1" if ok else "0")
"""
    r = run(
        [str(env_py), "-c", code, payload],
        timeout_sec=getattr(config, "VERIFY_SUBPROCESS_TIMEOUT_SEC", 20),
        max_out=2000,
        max_err=2000,
    )
    return (r.stdout or "").strip().endswith("1")


def _verify_absent(env_py: Path, specs: list[str]) -> bool:
    parsed = _parse_specs(specs)
    if not parsed:
        return True

    payload = json.dumps([name for (name, _ver) in parsed])
    code = r"""
import json, sys
from importlib import metadata

names = json.loads(sys.argv[1])
ok = True
for name in names:
    try:
        _ = metadata.version(name)
        ok = False
    except metadata.PackageNotFoundError:
        pass
print("1" if ok else "0")
"""
    r = run(
        [str(env_py), "-c", code, payload],
        timeout_sec=getattr(config, "VERIFY_SUBPROCESS_TIMEOUT_SEC", 20),
        max_out=2000,
        max_err=2000,
    )
    return (r.stdout or "").strip().endswith("1")


def _pip(
    env_py: Path,
    args: list[str],
    timeout: int,
    idle_timeout: int | None = None,
    soft_verify=None,
    soft_success_hints: list[str] | None = None,
) -> RunResult:
    # Always non-interactive
    argv = [str(env_py), "-m", "pip", "--disable-pip-version-check", "--no-input", *args]
    return run(
        argv,
        timeout_sec=timeout,
        max_out=config.MAX_STDOUT_CHARS,
        max_err=config.MAX_STDERR_CHARS,
        idle_timeout_sec=idle_timeout,
        soft_verify=soft_verify,
        soft_verify_start_after_sec=getattr(config, "SOFT_VERIFY_START_AFTER_SEC", 8),
        soft_verify_every_sec=getattr(config, "SOFT_VERIFY_EVERY_SEC", 12),
        soft_verify_fast_every_sec=getattr(config, "SOFT_VERIFY_FAST_EVERY_SEC", 2),
        soft_verify_grace_sec=getattr(config, "SOFT_VERIFY_GRACE_SEC", 12),
        soft_verify_kill_if_no_exit_after_sec=getattr(config, "SOFT_VERIFY_KILL_IF_NO_EXIT_AFTER_SEC", 15),
        soft_success_hints=soft_success_hints,
    )


def pip_install(env_py: Path, packages: list[str], options: list[str]) -> RunResult:
    _validate_options(options)

    # Soft verify: if packages are installed, exit early even if pip hangs.
    def soft() -> bool:
        return _verify_installed(env_py, packages)

    return _pip(
        env_py,
        ["install", *options, *packages],
        timeout=config.TIMEOUT_PIP_INSTALL,
        idle_timeout=None,  # do NOT use idle timeout for installs
        soft_verify=soft,
        # hints only to speed up verification cadence, NOT to kill
        soft_success_hints=["Successfully installed", "Requirement already satisfied"],
    )


def pip_uninstall(env_py: Path, packages: list[str], options: list[str]) -> RunResult:
    _validate_options(options)

    def soft() -> bool:
        return _verify_absent(env_py, packages)

    return _pip(
        env_py,
        ["uninstall", "-y", *options, *packages],
        timeout=config.TIMEOUT_PIP_UNINSTALL,
        idle_timeout=None,
        soft_verify=soft,
        soft_success_hints=["Successfully uninstalled"],
    )


def pip_list(env_py: Path) -> RunResult:
    return _pip(
        env_py,
        ["list", "--format=json"],
        timeout=config.TIMEOUT_PIP_OTHER,
        idle_timeout=getattr(config, "TIMEOUT_PIP_IDLE_OTHER", None),
    )


def pip_show(env_py: Path, packages: list[str]) -> RunResult:
    return _pip(
        env_py,
        ["show", *packages],
        timeout=config.TIMEOUT_PIP_OTHER,
        idle_timeout=getattr(config, "TIMEOUT_PIP_IDLE_OTHER", None),
    )


def pip_check(env_py: Path) -> RunResult:
    return _pip(
        env_py,
        ["check"],
        timeout=config.TIMEOUT_PIP_OTHER,
        idle_timeout=getattr(config, "TIMEOUT_PIP_IDLE_OTHER", None),
    )


def pip_freeze(env_py: Path) -> RunResult:
    return _pip(
        env_py,
        ["freeze"],
        timeout=config.TIMEOUT_PIP_FREEZE,
        idle_timeout=getattr(config, "TIMEOUT_PIP_IDLE_OTHER", None),
    )
