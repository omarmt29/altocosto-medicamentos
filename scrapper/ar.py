"""Corre los scrapers de Argentina (Farmacity)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from scrapper.ar_farmacity import main as farmacity

    return farmacity()


if __name__ == "__main__":
    raise SystemExit(main())
