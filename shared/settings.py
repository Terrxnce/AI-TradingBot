from __future__ import annotations

import os
from pathlib import Path
from typing import Dict


# Resolve project root: one level up from this file's parent (shared/ -> project root)
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]


def env(key: str, default: str | None = None) -> str | None:
    """Read environment variable with default."""
    return os.getenv(key, default)


def get_user_paths(user_id: str) -> Dict[str, Path]:
    """Return per-user directories and ensure they exist.

    Structure under var/<user_id>/:
      - config/
      - logs/
      - state/
      - results/
    """
    base = PROJECT_ROOT / "var" / user_id
    paths: Dict[str, Path] = {
        "base": base,
        "config": base / "config",
        "logs": base / "logs",
        "state": base / "state",
        "results": base / "results",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def get_current_user_paths() -> Dict[str, Path] | None:
    """Helper to get paths using DEVI_USER_ID env if present."""
    user_id = env("DEVI_USER_ID")
    if not user_id:
        return None
    return get_user_paths(user_id)


