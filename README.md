# cache-pulse

cache-pulse inspects your local AI model caches (Hugging Face, PyTorch) and your
container runtime, then renders a self-contained HTML dashboard of what is cached,
how big it is, and what is running. It is strictly read-only: it never downloads
models, never mutates caches, and has zero pip dependencies (stdlib Python 3.11+).

![cache-pulse dashboard](docs/assets/dashboard.png)

## Quickstart

```bash
PYTHONPATH=src python3 -m cache_pulse inspect --json   # print cache + runtime data
PYTHONPATH=src python3 -m cache_pulse report           # write out/latest.html
PYTHONPATH=src python3 -m cache_pulse serve --port 8080  # serve the dashboard
```

Cache locations come from `HF_HOME` / `TORCH_HOME` (defaults
`~/.cache/huggingface`, `~/.cache/torch`). Paths under `$HOME` are shown as `~/...`
in the report, so the dashboard is privacy-clean out of the box.

## Features

- HF + PyTorch inventory: per-repo file counts and sizes from `HF_HOME` / `TORCH_HOME`
- Container runtime probe: rootless Podman first, Docker fallback, version + rootless status
- Disk pressure card: used/total on the cache filesystem with a usage bar
- One-file HTML dashboard (`out/latest.html`) plus an HTTP `serve` mode that renders on start
- Optional webhook alert: Bearer-token JSON POST when disk usage crosses a threshold

## Container (Podman and Docker)

```bash
cp .env.example .env        # adjust if your caches live elsewhere
mkdir -p out
podman compose up --build   # dashboard on http://localhost:8080/latest.html
```

Docker users run `docker compose up --build` from the same `compose.yml` (plain OCI
image, no pip step). The Podman rootless socket mount lives in `compose.override.yml`
(gitignored); enable it with `cp compose.override.yml.example compose.override.yml`,
or skip overrides with `podman compose -f compose.yml up --build`.

## Alerts (optional)

Create `~/.config/cache-pulse/config.json` (or pass `report --config <path>`):

```json
{"webhook_url": "https://example.com/hook", "api_token": "***", "disk_threshold": 0.9}
```

`report` POSTs a JSON alert (Bearer `api_token`) to `webhook_url` when disk usage
of the cache filesystem crosses `disk_threshold` (0..1, default 0.9).

## Layout

- `src/cache_pulse/inspector.py`: cache dirs, repo sizes, podman/docker probe, config, webhook
- `src/cache_pulse/renderer.py`: HTML rendering to `out/latest.html`
- `src/cache_pulse/cli.py`: argparse entrypoint (`inspect` / `report` / `serve`)
- `templates/dashboard.html`: self-contained dashboard template
- `tests/`: pytest suite

## Development

```bash
uvx ruff check .
uvx --with pytest pytest -q
```
