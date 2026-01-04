from __future__ import annotations

from pathlib import Path
import venv

class EnvError(ValueError):
    pass

def env_python(env_dir: Path) -> Path:
    """
    Return python executable inside a venv directory.
    Supports Windows and POSIX layouts.
    """
    win = env_dir / "Scripts" / "python.exe"
    posix = env_dir / "bin" / "python"

    if win.exists():
        return win
    if posix.exists():
        return posix

    raise EnvError(f"Invalid venv: python not found under {env_dir}")

def create(env_dir: Path) -> Path:
    """
    Create venv and return its python executable.
    """
    env_dir.mkdir(parents=True, exist_ok=True)
    venv.EnvBuilder(with_pip=True).create(str(env_dir))
    return env_python(env_dir)
