from __future__ import annotations

from dataclasses import dataclass
import subprocess
from threading import Thread
import time
from typing import Callable

import psutil


@dataclass
class RunResult:
    argv: list[str]
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    killed: bool = False
    reason: str | None = None


def _read_stream(stream, buf: list[str], buf_len: list[int], max_chars: int, last_output: list[float]) -> None:
    try:
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
    finally:
        try:
            stream.close()
        except Exception:
            pass


def _terminate_process_tree(pid: int, kill_after_sec: float = 5.0) -> None:
    try:
        proc = psutil.Process(pid)
    except Exception:
        return

    try:
        children = proc.children(recursive=True)
    except Exception:
        children = []

    for c in children:
        try:
            c.terminate()
        except Exception:
            pass
    try:
        proc.terminate()
    except Exception:
        pass

    gone, alive = psutil.wait_procs([*children, proc], timeout=kill_after_sec)

    for p in alive:
        try:
            p.kill()
        except Exception:
            pass


def run(
    argv: list[str],
    timeout_sec: int,
    max_out: int,
    max_err: int,
    idle_timeout_sec: int | None = None,
    # --- soft verified exit ---
    soft_verify: Callable[[], bool] | None = None,
    soft_verify_start_after_sec: int = 0,
    soft_verify_every_sec: int = 10,
    soft_verify_fast_every_sec: int = 2,
    soft_verify_grace_sec: int = 10,
    soft_verify_kill_if_no_exit_after_sec: int = 15,
    soft_success_hints: list[str] | None = None,
) -> RunResult:
    """
    Safe subprocess runner:
    - no shell
    - total timeout
    - optional idle timeout (ONLY for short commands)
    - output truncation
    - kills process TREE on timeout (important on Windows)

    Soft verified-exit:
    If soft_verify is provided and returns True while the process is still running,
    we wait a short grace period for natural exit, then terminate the process tree
    and return success (reason="verified_early_exit").
    """
    start = time.monotonic()
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

    killed = False
    reason: str | None = None
    forced_success = False

    # soft verify state
    verified_at: float | None = None
    next_verify_at = start + max(0, soft_verify_start_after_sec)
    fast_mode = False
    last_hint_scan_at = start

    t_out = Thread(target=_read_stream, args=(p.stdout, out_buf, out_len, max_out, last_output), daemon=True)
    t_err = Thread(target=_read_stream, args=(p.stderr, err_buf, err_len, max_err, last_output), daemon=True)
    t_out.start()
    t_err.start()

    while True:
        rc = p.poll()
        if rc is not None:
            break

        now = time.monotonic()
        elapsed = now - start

        # Optional: scan output for success hints to verify more frequently
        if soft_verify and soft_success_hints and (now - last_hint_scan_at) >= 1.0:
            last_hint_scan_at = now
            combined = "".join(out_buf[-10:]) + "".join(err_buf[-10:])
            if any(h in combined for h in soft_success_hints):
                fast_mode = True

        # Soft verify: if desired state achieved, allow grace then terminate if still stuck
        if soft_verify and verified_at is None and now >= next_verify_at:
            interval = soft_verify_fast_every_sec if fast_mode else soft_verify_every_sec
            next_verify_at = now + max(1, interval)

            try:
                ok = soft_verify()
            except Exception:
                ok = False

            if ok:
                verified_at = now

        if verified_at is not None:
            # give pip time to exit naturally
            if (now - verified_at) >= soft_verify_grace_sec:
                # if still not exited after longer window, terminate
                if (now - verified_at) >= soft_verify_kill_if_no_exit_after_sec:
                    reason = "verified_early_exit"
                    _terminate_process_tree(p.pid)
                    killed = True
                    forced_success = True
                    break

        if idle_timeout_sec and (now - last_output[0]) >= idle_timeout_sec:
            reason = "idle_timeout"
            _terminate_process_tree(p.pid)
            killed = True
            break

        if elapsed >= timeout_sec:
            reason = "timeout"
            _terminate_process_tree(p.pid)
            killed = True
            break

        time.sleep(0.2)

    # Ensure ended
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        reason = reason or "kill_wait"
        _terminate_process_tree(p.pid)
        killed = True
        p.wait()

    t_out.join(timeout=2)
    t_err.join(timeout=2)

    out = "".join(out_buf)[:max_out]
    err = "".join(err_buf)[:max_err]

    exit_code = 0 if forced_success else (p.returncode if p.returncode is not None else 124)
    timed_out = (reason == "timeout") and not forced_success

    return RunResult(
        argv=argv,
        exit_code=exit_code,
        stdout=out,
        stderr=err,
        timed_out=timed_out,
        killed=killed,
        reason=reason,
    )
