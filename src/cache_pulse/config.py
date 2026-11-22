"""Configuration and relative/env path resolution for cache-pulse."""
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = Path(os.environ.get("CACHE_PULSE_OUT_DIR", ROOT_DIR / "out")).expanduser()
