"""
Scraper MX · Farmacias San Pablo → P_aguila.medicamentos_altos_costos_america

La tienda (https://www.farmaciasanpablo.com.mx/) está detrás de Akamai.
Desde este servidor suele responder 403; se intenta Magento GraphQL y VTEX
y, si hay caché local, se remata igual que Farmacity.

Uso:
    python scrapper/mx_sanpablo.py
    python scrapper/mx_sanpablo.py --fresh
    python scrapper/mx_sanpablo.py --cache
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.magento_tienda import ejecutar as ejecutar_magento  # noqa: E402
from scrapper.vtex_tienda import ejecutar as ejecutar_vtex  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "sanpablo"
BASE = "https://www.farmaciasanpablo.com.mx"
PAIS = "México"
FARMACIA = "Farmacias San Pablo"
MONEDA = "MXN"


def _parece_vtex() -> bool:
    try:
        r = requests.get(
            f"{BASE}/api/catalog_system/pub/products/search",
            params={"ft": "metformina", "_from": 0, "_to": 1},
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Accept-Language": "es-MX,es;q=0.9",
            },
            timeout=20,
        )
        if r.status_code in (200, 206):
            data = r.json()
            return isinstance(data, list)
    except Exception:
        return False
    return False


def main() -> int:
    kwargs = dict(
        titulo=" MX Farmacias San Pablo → medicamentos_altos_costos_america",
        pais=PAIS,
        farmacia=FARMACIA,
        moneda=MONEDA,
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
    )
    if _parece_vtex():
        return ejecutar_vtex(**kwargs, verify=True)
    return ejecutar_magento(**kwargs)


if __name__ == "__main__":
    raise SystemExit(main())
