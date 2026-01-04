from __future__ import annotations

from pathlib import Path
import os

from .pip_ops import pip_freeze

def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)

def freeze_to_file(env_py: Path, out_path: Path) -> dict:
    r = pip_freeze(env_py)
    content = (r.stdout or "").strip() + "\n"
    _atomic_write(out_path, content)
    return {"written_to": str(out_path), "count": len([ln for ln in content.splitlines() if ln.strip()])}
