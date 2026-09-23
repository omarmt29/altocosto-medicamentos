"""Corre los scrapers de México (Macrofarmacias + Similares + Ahorro + San Pablo)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from scrapper.mx_macrofarmacias import main as macrofarmacias
    from scrapper.mx_similares import main as similares
    from scrapper.mx_fahorro import main as fahorro
    from scrapper.mx_sanpablo import main as sanpablo

    for paso in (macrofarmacias, similares, fahorro, sanpablo):
        rc = paso()
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
