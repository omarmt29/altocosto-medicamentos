"""Scraper GT · Meykos (API /api/search)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.next_search_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "meykos_gt"
BASE = "https://meykos.com"


def main() -> int:
    return ejecutar(
        titulo=" GT Meykos → medicamentos_altos_costos_america",
        pais="Guatemala",
        farmacia="Meykos",
        moneda="GTQ",
        base=BASE,
        cache=CACHE,
        api_path="/api/search",
        search_param="q",
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
