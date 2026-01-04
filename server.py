from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from dev_env_mcp.workspace import find_workspace_root, resolve_in_workspace
from dev_env_mcp import state, audit, config
from dev_env_mcp.venv_ops import create as venv_create, env_python
from dev_env_mcp.pip_ops import (
    pip_install, pip_uninstall, pip_list, pip_show, pip_check, PipPolicyError
)
from dev_env_mcp.freeze import freeze_to_file

mcp = FastMCP("dev-env-mcp", json_response=True)

PipAction = Literal["install", "uninstall", "list", "show", "check"]


def _workspace_root() -> Path:
    """
    Determine the active workspace root.

    Priority:
    1) explicit workspace selected via workspace_use()
    2) last workspace from global state (~/.dev-env-mcp/global_state.json)
    3) auto-detect from current working directory (pyproject.toml/.git)
    """
    p = state.get_active_workspace()
    if p is not None:
        return p

    detected = find_workspace_root(Path.cwd())
    # Don’t auto-write global state here; only workspace_use() should set it.
    return detected


def _active_env_python() -> tuple[Path, Path, Path]:
    """
    Return (workspace_root, env_dir, env_python) for the currently active env.
    env path is stored relative to the workspace for portability.
    """
    root = _workspace_root()
    st = state.load_local_state(root)

    if not st.active_env:
        raise ValueError(
            "No active env in this workspace. Call env_create() or env_use() first. "
            "If you intended a different project, call workspace_use(path) first."
        )

    env_dir = resolve_in_workspace(root, st.active_env)
    return root, env_dir, env_python(env_dir)


@mcp.tool()
def workspace_use(path: str) -> dict[str, Any]:
    """
    Select the project/workspace to manage.

    - 'path' can be a repo root or any subdirectory inside a repo.
    - The server will auto-find the workspace root by walking up to pyproject.toml or .git.
    - All future operations (env_create/pip/freeze) are sandboxed to this workspace.
    """
    root = find_workspace_root(Path(path))
    if not root.exists():
        raise ValueError(f"Workspace path does not exist: {root}")

    state.set_active_workspace(root)
    audit.append(root, {"tool": "workspace_use", "workspace_root": str(root)})
    return {"ok": True, "workspace_root": str(root)}


@mcp.tool()
def env_create(path: str = ".venv") -> dict[str, Any]:
    """
    Create a venv inside the active workspace (default: .venv) and set it active.
    """
    root = _workspace_root()
    env_dir = resolve_in_workspace(root, path)

    py = venv_create(env_dir)

    # store relative path for portability
    env_rel = str(env_dir.relative_to(root))
    state.set_active_env(root, env_rel)

    audit.append(root, {"tool": "env_create", "env_dir": str(env_dir), "env_rel": env_rel})
    return {"ok": True, "workspace_root": str(root), "env_dir": str(env_dir), "env_rel": env_rel, "python_executable": str(py)}


@mcp.tool()
def env_use(path: str = ".venv") -> dict[str, Any]:
    """
    Use an existing venv inside the active workspace and set it active.
    """
    root = _workspace_root()
    env_dir = resolve_in_workspace(root, path)

    py = env_python(env_dir)

    env_rel = str(env_dir.relative_to(root))
    state.set_active_env(root, env_rel)

    audit.append(root, {"tool": "env_use", "env_dir": str(env_dir), "env_rel": env_rel})
    return {"ok": True, "workspace_root": str(root), "env_dir": str(env_dir), "env_rel": env_rel, "python_executable": str(py)}


@mcp.tool()
def pip(
    action: PipAction,
    packages: list[str] | None = None,
    options: list[str] | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """
    Run a restricted pip action inside the active venv.

    Parameters:
      - action: install | uninstall | list | show | check
      - packages: list of packages/specs (e.g. ["requests", "numpy==2.1.0"])
      - options: allowlisted pip options only (see server policy)
      - confirm: required for uninstall (safety)
    """
    packages = packages or []
    options = options or []

    root, env_dir, env_py = _active_env_python()

    if action == "uninstall" and not confirm:
        raise ValueError("Refusing to uninstall without confirm=true")

    try:
        if action == "install":
            r = pip_install(env_py, packages, options)
        elif action == "uninstall":
            r = pip_uninstall(env_py, packages, options)
        elif action == "list":
            r = pip_list(env_py)
        elif action == "show":
            r = pip_show(env_py, packages)
        else:
            r = pip_check(env_py)
    except PipPolicyError as e:
        raise ValueError(str(e)) from e

    audit.append(
        root,
        {
            "tool": "pip",
            "action": action,
            "packages": packages,
            "options": options,
            "exit": r.exit_code,
            "timed_out": r.timed_out,
        },
    )

    return {
        "workspace_root": str(root),
        "env_dir": str(env_dir),
        "python_executable": str(env_py),
        "argv": r.argv,
        "exit_code": r.exit_code,
        "timed_out": r.timed_out,
        "stdout": r.stdout,
        "stderr": r.stderr,
    }


@mcp.tool()
def freeze(path: str = "requirements.txt") -> dict[str, Any]:
    """
    Write pinned requirements from the active venv to a file in the workspace.
    """
    root, env_dir, env_py = _active_env_python()
    out_path = resolve_in_workspace(root, path)

    res = freeze_to_file(env_py, out_path)

    audit.append(root, {"tool": "freeze", "path": str(out_path), "count": res["count"]})
    return {"workspace_root": str(root), "env_dir": str(env_dir), **res}


def main() -> None:
    # STDIO transport for Codex
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
