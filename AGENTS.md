# AGENTS.md — cache-pulse

## Architecture & Anti-Monolith Rules

- Keep source files **<= 350 lines** and functions **<= 50 lines** (split by responsibility before a file grows past 350 lines).
- Keep the entrypoint thin (config + wiring only); separate domain logic, I/O, and UI/templates into distinct modules.
- Use relative paths (`__file__` / `BASH_SOURCE[0]`) for intra-repo files; use env vars + `.env.example` only for external paths or secrets.
- Put rendered outputs, screenshots, and temp files in `out/` (gitignored).
- When parallel agents work on this repo at the same time (`HERDR_ENV=1`, subagent, or another task has uncommitted edits), automatically isolate work in `/tmp/wt-cache-pulse-<task>` (`git worktree add /tmp/wt-cache-pulse-<task> -b <branch>`) and run `git worktree remove` after merging.

## Verification

- Secret scan: `command -v gitleaks >/dev/null && gitleaks dir . --no-banner --redact || true`
- Hardcoded-path gate: `! grep -rnE '(/home/[A-Za-z0-9._-]+/|/Users/[A-Za-z0-9._-]+/|/mnt/[A-Za-z0-9._-]+/|/media/[A-Za-z0-9._-]+/|/run/media/[A-Za-z0-9._-]+/|~/development/)' . --exclude-dir=.git --exclude-dir=tests --exclude-dir=docs --exclude-dir=out --exclude-dir=__pycache__ --exclude-dir=.ruff_cache --exclude-dir=.pytest_cache --exclude='*.md' --exclude='.env.example' --exclude='compose.override*' 2>/dev/null`
- File line gate (any language): `find src scripts lib -type f 2>/dev/null | while IFS= read -r f; do n=$(wc -l < "$f"); [ "$n" -gt 350 ] && echo "$f: $n lines" && exit 1; done; true`
- Stack lint/test: `uvx ruff check . && uvx --with pytest pytest -q`
