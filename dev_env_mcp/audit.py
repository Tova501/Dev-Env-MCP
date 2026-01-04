from __future__ import annotations

from pathlib import Path
import json
import time

from . import config

def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def append(workspace_root: Path, event: dict) -> None:
    """
    Append one JSON line to <workspace>/.dev-env-mcp/audit.log
    """
    d = workspace_root / config.APP_DIRNAME
    d.mkdir(parents=True, exist_ok=True)

    p = d / config.AUDIT_FILENAME

    payload = dict(event)
    payload["ts_utc"] = _utc_now()

    p.open("a", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False) + "\n")
