"""Corre los scrapers de Colombia (Locatel)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from scrapper.co_locatel import main as locatel

    return locatel()


if __name__ == "__main__":
    raise SystemExit(main())
