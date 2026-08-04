"""
EdgeDash entry point.

    python run_cycle.py

Loads config, runs one full cycle through the orchestrator.
"""
from __future__ import annotations

import sys

from edgedash.config import load_config
from edgedash.orchestrator import run_cycle


def main() -> None:
    config = load_config()
    results = run_cycle(config)
    failed = [r for r in results if r.status == "failed"]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
