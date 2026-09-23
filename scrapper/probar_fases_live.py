#!/usr/bin/env python3
"""Prueba en vivo fase principio vs marcas para PE, EC y CO.

    python scrapper/probar_fases_live.py
    python scrapper/probar_fases_live.py --fresh
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.busqueda_marcas import refrescar_cache_nombres  # noqa: E402


def _stats(filas: list[dict[str, Any]]) -> dict[str, Any]:
    meds = {int(f["n_lista"]) for f in filas}
    return {
        "filas": len(filas),
        "principios": len(meds),
        "con_precio": sum(1 for f in filas if f.get("precio")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    argv = ["--fresh"] if args.fresh else []

    refrescar_cache_nombres()

    pruebas: list[tuple[str, str, Callable[[], list[dict[str, Any]]]]] = []

    from scrapper.pe_inkafarma import recolectar as pe_inkafarma  # noqa: E402
    from scrapper.pe_boticasperu import recolectar as pe_boticas  # noqa: E402
    from scrapper.ec_pharmacys import CACHE as EC_PH_CACHE, BASE as EC_PH_BASE  # noqa: E402
    from scrapper.ec_cruzazul import CACHE as EC_CA_CACHE, BASE as EC_CA_BASE  # noqa: E402
    from scrapper.co_locatel import CACHE as CO_LO_CACHE, BASE as CO_LO_BASE  # noqa: E402
    from scrapper.co_carulla import CACHE as CO_CAR_CACHE, BASE as CO_CAR_BASE  # noqa: E402
    from scrapper.co_farmatodo import recolectar as co_farmatodo  # noqa: E402
    from scrapper.vtex_tienda import recolectar as vtex_recolectar  # noqa: E402

    def vtex(pais: str, farmacia: str, moneda: str, base: str, cache: Path) -> list[dict[str, Any]]:
        return vtex_recolectar(
            pais=pais,
            farmacia=farmacia,
            moneda=moneda,
            base=base,
            cache=cache,
            forzar=args.fresh,
            verify=False,
        )

    pruebas = [
        ("Perú", "Inkafarma", lambda: pe_inkafarma(forzar=args.fresh)),
        ("Perú", "Boticas Perú", lambda: pe_boticas(forzar=args.fresh)),
        ("Ecuador", "Pharmacy's", lambda: vtex("Ecuador", "Pharmacy's", "USD", EC_PH_BASE, EC_PH_CACHE)),
        ("Ecuador", "Cruz Azul", lambda: vtex("Ecuador", "Cruz Azul", "USD", EC_CA_BASE, EC_CA_CACHE)),
        ("Colombia", "Locatel", lambda: vtex("Colombia", "Locatel", "COP", CO_LO_BASE, CO_LO_CACHE)),
        ("Colombia", "Farmatodo", lambda: co_farmatodo(forzar=args.fresh)),
        ("Colombia", "Carulla", lambda: vtex("Colombia", "Carulla", "COP", CO_CAR_BASE, CO_CAR_CACHE)),
    ]

    print("=" * 72)
    print(" Prueba búsqueda ampliada (principio + marcas cruzadas)")
    print(f" Modo: {'--fresh' if args.fresh else 'caché + red'} · {len(MEDICAMENTOS)} principios")
    print("=" * 72)

    totales_pais: dict[str, dict[str, int]] = {}
    filas_global: list[dict[str, Any]] = []

    for pais, farmacia, fn in pruebas:
        print(f"\n>>> {pais} · {farmacia}")
        print("-" * 72)
        try:
            filas = fn()
        except Exception as exc:
            print(f"  ERROR: {exc}")
            continue
        st = _stats(filas)
        filas_global.extend(filas)
        tp = totales_pais.setdefault(pais, {"filas": 0, "principios": set()})
        tp["filas"] += st["filas"]
        tp["principios"].update({int(f["n_lista"]) for f in filas})
        print(
            f"  → {st['filas']} filas · {st['principios']} principios · "
            f"{st['con_precio']} con precio"
        )
        by_med: dict[str, int] = {}
        for f in filas:
            by_med[f["medicamento_lista"]] = by_med.get(f["medicamento_lista"], 0) + 1
        top = sorted(by_med.items(), key=lambda x: (-x[1], x[0]))[:8]
        if top:
            print("  Top principios:")
            for nombre, n in top:
                print(f"    {n:2d}  {nombre}")

    print("\n" + "=" * 72)
    print(" Resumen por país")
    print("=" * 72)
    for pais, tp in totales_pais.items():
        print(f"  {pais}: {tp['filas']} filas · {len(tp['principios'])} principios distintos")

    meds_g = {int(f["n_lista"]) for f in filas_global}
    print(f"\nTotal combinado: {len(filas_global)} filas · {len(meds_g)} principios distintos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
