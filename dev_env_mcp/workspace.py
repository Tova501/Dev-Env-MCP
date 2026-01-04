from __future__ import annotations

from pathlib import Path

class WorkspaceError(ValueError):
    pass

def find_workspace_root(start: Path) -> Path:
    """
    Walk upwards from 'start' to find a repo/workspace root.
    Root is a directory containing pyproject.toml or .git.
    If none found, returns the resolved start directory.
    """
    start = start.resolve()
    if start.is_file():
        start = start.parent

    for p in [start, *start.parents]:
        if (p / "pyproject.toml").exists() or (p / ".git").exists():
            return p
    return start

def resolve_in_workspace(root: Path, user_path: str) -> Path:
    """
    Resolve user_path and enforce that it stays inside root.
    Relative paths are resolved relative to root.
    """
    root = root.resolve()
    p = Path(user_path)

    resolved = (root / p).resolve() if not p.is_absolute() else p.resolve()

    if resolved != root and root not in resolved.parents:
        raise WorkspaceError(f"Path must be inside workspace root: {root}")

    return resolved
