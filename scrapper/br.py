"""Corre los scrapers de Brasil (Pague Menos)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from scrapper.br_paguemenos import main as paguemenos

    return paguemenos()


if __name__ == "__main__":
    raise SystemExit(main())
