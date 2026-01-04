from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from threading import Thread
import time

@dataclass
class RunResult:
    argv: list[str]
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    killed: bool = False
    reason: str | None = None

def _debug(msg: str) -> None:
    if not os.getenv("DEV_ENV_MCP_DEBUG"):
        return
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    line = f"[{ts}] [dev-env-mcp] {msg}\n"
    log_path = Path.cwd() / ".dev-env-mcp" / "debug.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.open("a", encoding="utf-8").write(line)
    
def _read_stream(
    stream,
    buf: list[str],
    buf_len: list[int],
    max_chars: int,
    last_output: list[float],
) -> None:
    while True:
        chunk = stream.read(4096)
        if not chunk:
            break
        last_output[0] = time.monotonic()
        text = chunk.decode("utf-8", errors="replace")
        if buf_len[0] < max_chars:
            remaining = max_chars - buf_len[0]
            buf.append(text[:remaining])
            buf_len[0] += min(len(text), remaining)
    stream.close()

def run(
    argv: list[str],
    timeout_sec: int,
    max_out: int,
    max_err: int,
    idle_timeout_sec: int | None = None,
    success_markers: list[str] | None = None,
    success_grace_sec: int = 5,
) -> RunResult:
    """
    Safe subprocess runner:
    - no shell
    - timeout
    - output truncation
    """
    start = time.monotonic()
    _debug(f"run start timeout={timeout_sec}s argv={argv}")

    p = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=False,
    )
    out_buf: list[str] = []
    err_buf: list[str] = []
    out_len = [0]
    err_len = [0]
    last_output = [start]
    success_time: float | None = None
    killed = False
    reason: str | None = None
    forced_success = False

    t_out = Thread(
        target=_read_stream,
        args=(p.stdout, out_buf, out_len, max_out, last_output),
        daemon=True,
    )
    t_err = Thread(
        target=_read_stream,
        args=(p.stderr, err_buf, err_len, max_err, last_output),
        daemon=True,
    )
    t_out.start()
    t_err.start()

    while True:
        rc = p.poll()
        if rc is not None:
            break

        now = time.monotonic()
        elapsed = now - start

        if success_markers and success_time is None:
            combined = "".join(out_buf) + "".join(err_buf)
            if any(marker in combined for marker in success_markers):
                success_time = now
                _debug("success marker detected; waiting for graceful exit")

        if success_time is not None and (now - success_time) >= success_grace_sec:
            _debug(f"success grace exceeded; killing pid={p.pid}")
            p.kill()
            killed = True
            forced_success = True
            reason = "success_grace_kill"
            break

        if idle_timeout_sec and (now - last_output[0]) >= idle_timeout_sec:
            _debug(f"idle timeout after {now - last_output[0]:.2f}s; killing pid={p.pid}")
            p.kill()
            killed = True
            reason = "idle_timeout"
            break

        if elapsed >= timeout_sec:
            _debug(f"run timeout after {elapsed:.2f}s; killing pid={p.pid}")
            p.kill()
            killed = True
            reason = "timeout"
            break

        time.sleep(0.2)

    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()
        killed = True
        reason = reason or "kill_wait"

    t_out.join(timeout=1)
    t_err.join(timeout=1)

    out = "".join(out_buf)
    err = "".join(err_buf)

    exit_code = 0 if forced_success else (p.returncode if p.returncode is not None else 124)
    timed_out = reason == "timeout"
    if forced_success:
        timed_out = False

    elapsed = time.monotonic() - start
    _debug(f"run done exit={exit_code} elapsed={elapsed:.2f}s killed={killed} reason={reason}")
    return RunResult(
        argv=argv,
        exit_code=exit_code,
        stdout=(out or "")[:max_out],
        stderr=(err or "")[:max_err],
        timed_out=timed_out,
        killed=killed,
        reason=reason,
    )
