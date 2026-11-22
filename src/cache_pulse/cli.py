"""Thin CLI entrypoint for cache-pulse."""
import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cache_pulse import inspector
from cache_pulse.config import OUT_DIR
from cache_pulse.renderer import render_report


def _inspect(args: argparse.Namespace) -> int:
    data = inspector.build_report_data()
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        c = data["container"]
        print(
            f"hf={data['hf']['total_size']}B torch={data['torch']['total_size']}B "
            f"container={c['name'] or 'none'} disk_free={data['disk']['free']}B"
        )
    return 0


def _report(args: argparse.Namespace) -> int:
    data = inspector.build_report_data()
    out = render_report(data, Path(args.output))
    print(f"report: {out}")
    cfg = inspector.load_config(args.config)
    disk = data["disk"]
    used_frac = disk["used"] / disk["total"] if disk["total"] else 0.0
    if used_frac >= float(cfg.get("disk_threshold", 0.9)) and cfg.get("webhook_url"):
        payload = {"type": "disk_threshold", "host": data["host"], **disk}
        sent = inspector.send_alert(cfg["webhook_url"], cfg.get("api_token"), payload)
        print(f"alert sent: {sent}")
    if args.json:
        print(json.dumps(data, indent=2))
    return 0


def _serve(args: argparse.Namespace) -> int:
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    if not (out / "latest.html").exists():
        render_report(inspector.build_report_data(), out)
    handler = partial(SimpleHTTPRequestHandler, directory=str(out))
    httpd = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"serving {out} on http://{args.host}:{args.port}")
    httpd.serve_forever()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="cache-pulse",
        description="Inspect AI model caches and container runtime; render an HTML report.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("inspect", help="print cache/runtime data (JSON with --json)")
    pi.add_argument("--json", action="store_true")
    pi.set_defaults(fn=_inspect)

    pr = sub.add_parser("report", help="render the HTML report into the output folder")
    pr.add_argument("--output", default=str(OUT_DIR), help="output directory (default: out/)")
    pr.add_argument("--config", help="path to JSON config (webhook_url, api_token, disk_threshold)")
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(fn=_report)

    ps = sub.add_parser("serve", help="serve the report folder over HTTP")
    ps.add_argument("--host", default="127.0.0.1")
    ps.add_argument("--port", type=int, default=8080)
    ps.add_argument("--output", default=str(OUT_DIR))
    ps.set_defaults(fn=_serve)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
