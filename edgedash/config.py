"""
Load project configuration from config.yaml at the repo root.

All user-specific values (role, city, skills, etc.) live here.
No other module should read config files or environment variables directly
for these settings — import `load_config()` instead.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# PyYAML is the only sensible choice for YAML parsing in the stdlib-free world.
# `tomllib` (stdlib, 3.11+) only handles TOML; `configparser` is INI-only.
# PyYAML saves real work here.
try:
    import yaml
except ImportError as exc:
    raise ImportError(
        "PyYAML is required. Install it with: pip install pyyaml"
    ) from exc

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_FILE = _REPO_ROOT / "config.yaml"

_DEFAULTS: dict[str, Any] = {
    "target_role": "Data Analyst",
    "target_city": "Bengaluru",
    "keywords": ["SQL", "Python", "data analysis"],
    "my_skills": [],
    "experience_years": 0,
    "db_path": "edgedash.db",
    "min_fit_score": 50,
}


@dataclass
class Config:
    target_role: str
    target_city: str
    keywords: list[str]
    my_skills: list[str]
    experience_years: int
    db_path: str
    min_fit_score: int


def load_config(path: Path | None = None) -> Config:
    """Read config.yaml and return a validated Config instance.

    Raises FileNotFoundError with a clear message if the file is absent.
    Missing individual fields fall back to sensible defaults.
    """
    config_path = path or _CONFIG_FILE

    if not config_path.exists():
        raise FileNotFoundError(
            f"config.yaml not found at {config_path}.\n"
            "Copy config.yaml.example to config.yaml and fill in your details."
        )

    with config_path.open("r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    merged = {**_DEFAULTS, **raw}

    return Config(
        target_role=str(merged["target_role"]),
        target_city=str(merged["target_city"]),
        keywords=_as_str_list(merged["keywords"], "keywords"),
        my_skills=_as_str_list(merged["my_skills"], "my_skills"),
        experience_years=_as_int(merged["experience_years"], "experience_years"),
        db_path=str(merged["db_path"]),
        min_fit_score=_as_int(merged["min_fit_score"], "min_fit_score"),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _as_str_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise TypeError(f"config.yaml: '{field_name}' must be a list, got {type(value).__name__}")
    return [str(item) for item in value]


def _as_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            f"config.yaml: '{field_name}' must be an integer, got {value!r}"
        ) from exc


if __name__ == "__main__":
    cfg = load_config()
    print(cfg)
    sys.exit(0)
