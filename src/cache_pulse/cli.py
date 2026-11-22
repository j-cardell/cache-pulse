"""Thin CLI entrypoint for cache-pulse."""
from cache_pulse.core import run


def main() -> int:
    print(run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
