from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from typing import Any

import psutil
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("dev-env-mcp", json_response=True)


@mcp.tool()
def system_summary() -> dict[str, Any]:
    vm = psutil.virtual_memory()
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "os": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "arch": platform.architecture()[0],
        "hostname": platform.node(),
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "ram_gb": round(vm.total / (1024**3), 2),
    }


@mcp.tool()
def python_env() -> dict[str, Any]:
    return {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "prefix": sys.prefix,
        "base_prefix": getattr(sys, "base_prefix", None),
        "sys_path_has_site_packages": any("site-packages" in p for p in sys.path),
    }


@mcp.tool()
def installed_packages(limit: int = 200) -> dict[str, Any]:
    pkgs = sorted(
        [{"name": d.metadata.get("Name", ""), "version": d.version} for d in metadata.distributions()],
        key=lambda x: x["name"].lower(),
    )
    return {"count": len(pkgs), "packages": pkgs[: max(0, limit)]}


@mcp.tool()
def gpu_info() -> dict[str, Any]:
    out: dict[str, Any] = {"nvidia_smi_present": shutil.which("nvidia-smi") is not None}

    if out["nvidia_smi_present"]:
        try:
            r = subprocess.run(
                ["nvidia-smi", "-L"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            out["nvidia_smi_devices"] = (r.stdout or "").strip().splitlines()
        except Exception as e:
            out["nvidia_smi_error"] = repr(e)

    # Optional: Torch (only if installed)
    try:
        import torch  # type: ignore

        out["torch_present"] = True
        out["torch_version"] = getattr(torch, "__version__", None)
        out["cuda_available"] = bool(torch.cuda.is_available())
        if out["cuda_available"]:
            out["cuda_device_count"] = torch.cuda.device_count()
            out["cuda_runtime_version"] = getattr(torch.version, "cuda", None)
            out["cuda_device_name"] = torch.cuda.get_device_name(0)
    except Exception:
        out["torch_present"] = False

    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
