"""Render the cache-pulse HTML dashboard report."""
import html
from pathlib import Path
from string import Template


def human_size(n: int) -> str:
    """Format a byte count as a human-readable string (binary steps)."""
    if n < 1024:
        return f"{n} B"
    size = float(n)
    for unit in ("KB", "MB", "GB", "TB"):
        size /= 1024
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
    return f"{size:.1f} TB"


def _rows(entries: list[dict], empty: str) -> str:
    if not entries:
        return f'<tr><td colspan="3">{html.escape(empty)}</td></tr>'
    return "\n".join(
        f"<tr><td>{html.escape(str(e['name']))}</td>"
        f"<td>{html.escape(str(e['files']))}</td>"
        f"<td>{human_size(e['size'])}</td></tr>"
        for e in entries
    )


def _container(c: dict) -> str:
    if c.get("available"):
        name = html.escape(str(c.get("name", "")))
        version = html.escape(str(c.get("version", "")))
        rootless = " (rootless)" if c.get("rootless") else ""
        return f"{name} {version}{rootless}"
    err = c.get("error")
    return "unavailable: " + (html.escape(str(err)) if err else "no runtime found")


def _disk(d: dict) -> str:
    used, total = d.get("used", 0), d.get("total", 0)
    pct = round(used / total * 100) if total else 0
    bar = f'<div class="bar"><div class="fill" style="width:{pct}%"></div></div>'
    return f"{human_size(used)} / {human_size(total)} ({pct}% used) {bar}"


def render_report(
    data: dict, output_dir: str | Path, template_dir: str | Path | None = None
) -> Path:
    """Render the report data dict into output_dir/latest.html and return the path."""
    default = Path(__file__).resolve().parents[2] / "templates"
    tdir = Path(template_dir) if template_dir else default
    tpl = (tdir / "dashboard.html").read_text(encoding="utf-8")

    hf, torch_ = data["hf"], data["torch"]
    total = hf["total_size"] + torch_["total_size"]
    fields = {
        "TITLE": "cache-pulse",
        "GENERATED_AT": html.escape(data["generated_at"]),
        "HOST": html.escape(data["host"]),
        "HF_DIR": html.escape(hf["dir"]),
        "HF_TOTAL": human_size(hf["total_size"]),
        "HF_MODELS": _rows(hf["models"], "no cached models found"),
        "TORCH_DIR": html.escape(torch_["dir"]),
        "TORCH_TOTAL": human_size(torch_["total_size"]),
        "TORCH_CACHES": _rows(torch_["caches"], "no torch caches found"),
        "CONTAINER": _container(data["container"]),
        "DISK": _disk(data["disk"]),
        "TOTAL_SIZE": human_size(total),
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "latest.html"
    path.write_text(Template(tpl).safe_substitute(fields), encoding="utf-8")
    return path
