# dev-env-mcp

A local MCP (Model Context Protocol) server that exposes safe, structured tools to inspect your development environment (OS, Python env, installed packages, basic diagnostics).  
It helps coding agents make correct decisions based on **real machine facts** instead of guesses.

---

## ✅ Features (MVP)

- **`system_summary`** — OS, architecture, CPU, basic memory info  
- **`python_env`** — Python executable path, version, venv/conda detection  
- **`installed_packages`** — installed Python packages (JSON output)  
- **`import_check`** — test imports and return errors/tracebacks  
- **`env_vars`** — *allowlisted* environment variables only (safe by default)

---

## 📦 Requirements

- Python **3.10+**
- `uv` (recommended) or `pip`
- Node.js (only for running the Inspector)

---

## 🚀 Installation

### Option A: Using `uv` (recommended)

```bash
uv init dev-env-mcp
cd dev-env-mcp
uv add "mcp[cli]" httpx pydantic
```

### Option B: Using `pip`

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install "mcp[cli]" httpx pydantic
```

---

## ▶️ Run the server

```bash
uv run server.py
```

By default (Streamable HTTP), the MCP endpoint is:

- `http://localhost:8000/mcp`

---

## 🧪 Test with MCP Inspector

```bash
npx -y @modelcontextprotocol/inspector
```

In the Inspector UI, connect to:

- `http://localhost:8000/mcp`

Then try tools like:
- `system_summary`
- `python_env`
- `installed_packages`
- `import_check`

---

## 🔒 Security notes

This server is designed to be safe by default:

- ✅ No arbitrary command execution  
- ✅ No dumping all environment variables  
- ✅ `env_vars` returns only an **allowlist** (example: `PATH`, `VIRTUAL_ENV`, `PYTHONPATH`, proxy variables)

If you add more tools, keep outputs:
- structured (JSON-friendly)
- minimal
- secret-safe

---

## 🗂️ Project structure

```text
dev-env-mcp/
  server.py
  pyproject.toml
  README.md
```

---

## 🧭 Roadmap (optional)

- Add **`gpu_info`** (CUDA / `nvidia-smi` / torch GPU availability)
- Add dependency/vulnerability mode (OSV / PyPI) as optional third-party tools
- Add caching for faster repeated queries
- Add a single **`diagnose()`** tool that bundles everything into one report
