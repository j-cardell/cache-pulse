"""Inspect local AI model caches and container runtime status."""
import json
import os
import shutil
import socket
import subprocess
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


def get_cache_dirs() -> dict:
    return {
        "hf": Path(os.environ.get("HF_HOME", "~/.cache/huggingface")).expanduser(),
        "torch": Path(os.environ.get("TORCH_HOME", "~/.cache/torch")).expanduser(),
    }


def repo_size(path: Path) -> int:
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for name in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass
    return total


def count_files(path: Path) -> int:
    return sum(len(filenames) for _dirpath, _dirnames, filenames in os.walk(path))


def list_hf_models(hf_dir: Path) -> list[dict]:
    for base in (hf_dir / "hub", hf_dir):
        if base.is_dir():
            models = [
                {
                    "name": d.name[8:].replace("--", "/"),
                    "size": repo_size(d),
                    "files": count_files(d),
                }
                for d in base.iterdir()
                if d.is_dir() and d.name.startswith("models--")
            ]
            if models:
                return sorted(models, key=lambda m: m["name"])
    return []


def list_torch_caches(torch_dir: Path) -> list[dict]:
    if not torch_dir.is_dir():
        return []
    caches = [
        {"name": d.name, "size": repo_size(d), "files": count_files(d)}
        for d in torch_dir.iterdir()
        if d.is_dir()
    ]
    return sorted(caches, key=lambda c: c["name"])


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, capture_output=True, timeout=10)


def _podman_rootless(info: dict) -> bool | None:
    # podman >= 6 emits lowercase JSON keys; older releases use title case.
    host = info.get("Host") or info.get("host") or {}
    sec = host.get("Security") or host.get("security") or {}
    return sec.get("Rootless", sec.get("rootless"))


def check_container_runtime() -> dict:
    errors: list[str] = []
    try:
        v = _run(["podman", "--version"])
        if v.returncode == 0:
            version = v.stdout.strip().removeprefix("podman version ")
            rootless = None
            try:
                info = json.loads(_run(["podman", "info", "--format", "json"]).stdout)
                rootless = _podman_rootless(info)
            except (subprocess.SubprocessError, json.JSONDecodeError, AttributeError):
                rootless = None
            return {
                "available": True,
                "name": "podman",
                "version": version,
                "rootless": rootless,
                "error": None,
            }
        errors.append(f"podman --version: {v.stderr.strip() or 'no output'}")
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        errors.append(f"podman: {exc}")

    try:
        v = _run(["docker", "version", "--format", "{{.Server.Version}}"])
        if v.returncode == 0:
            return {
                "available": True,
                "name": "docker",
                "version": v.stdout.strip(),
                "rootless": None,
                "error": None,
            }
        errors.append(f"docker version: {v.stderr.strip() or 'no output'}")
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        errors.append(f"docker: {exc}")

    return {
        "available": False,
        "name": None,
        "version": None,
        "rootless": None,
        "error": "; ".join(errors),
    }


def build_report_data() -> dict:
    dirs = get_cache_dirs()
    hf = list_hf_models(dirs["hf"])
    tc = list_torch_caches(dirs["torch"])
    base = dirs["hf"] if dirs["hf"].exists() else Path.home()
    du = shutil.disk_usage(base)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "host": socket.gethostname(),
        "hf": {
            "dir": str(dirs["hf"]),
            "models": hf,
            "total_size": sum(m["size"] for m in hf),
        },
        "torch": {
            "dir": str(dirs["torch"]),
            "caches": tc,
            "total_size": sum(c["size"] for c in tc),
        },
        "container": check_container_runtime(),
        "disk": {
            "path": str(base),
            "total": du.total,
            "used": du.used,
            "free": du.free,
        },
    }


def load_config(path: str | Path | None = None) -> dict:
    candidates: list[Path] = []
    if path is not None:
        candidates.append(Path(path).expanduser())
    env = os.environ.get("CACHE_PULSE_CONFIG")
    if env:
        candidates.append(Path(env).expanduser())
    candidates.append(Path.home() / ".config" / "cache-pulse" / "config.json")
    for cand in candidates:
        try:
            return json.loads(cand.read_text())
        except (OSError, json.JSONDecodeError):
            continue
    return {}


def send_alert(webhook_url: str, token: str | None, payload: dict) -> bool:
    # config is user-local, but only http(s) may reach the network
    if not webhook_url.lower().startswith(("http://", "https://")):
        return False
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        webhook_url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False
