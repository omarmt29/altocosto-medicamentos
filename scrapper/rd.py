"""Corre los scrapers de República Dominicana (FarmaValue + Carol + Qualipharma + Los Hidalgos)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from scrapper.rd_farmavalue import main as farmavalue
    from scrapper.rd_carol import main as carol
    from scrapper.rd_farmacias_do import main as farmacias_do
    from scrapper.rd_qualipharma import main as qualipharma
    from scrapper.rd_hidalgos import main as hidalgos

    rc = farmavalue()
    if rc:
        return rc
    rc = carol()
    if rc:
        return rc
    rc = farmacias_do()
    if rc:
        return rc
    rc = qualipharma()
    if rc:
        return rc
    return hidalgos()


if __name__ == "__main__":
    raise SystemExit(main())
