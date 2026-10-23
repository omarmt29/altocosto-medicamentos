"""Retira la fuente historica NADAC: es un indice CMS, no una farmacia."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.repositorio import asegurar_tabla, purgar_obsoletos  # noqa: E402


def main() -> int:
    asegurar_tabla()
    borrados = purgar_obsoletos("Estados Unidos", "NADAC (CMS)", [])
    print(f"NADAC (CMS) retirado: {borrados} filas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
