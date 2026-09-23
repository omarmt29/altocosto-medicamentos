#!/usr/bin/env python3
"""Muestra términos de búsqueda fase 1 vs fase 2 (marcas cruzadas).

    python scrapper/probar_busqueda_marcas.py
    python scrapper/probar_busqueda_marcas.py --pais Colombia --solo Bortezomib
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.busqueda_marcas import (  # noqa: E402
    cobertura_por_pais,
    pais_referencia_para_med,
    refrescar_cache_nombres,
)
from scrapper.vtex_tienda import fases_busqueda  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pais", default="Colombia")
    parser.add_argument("--solo", default="", help="Filtrar por nombre de principio")
    args = parser.parse_args()

    n = refrescar_cache_nombres()
    print(f"Índice nombres comerciales: {n} principios con histórico en BD\n")
    print("Cobertura por país (principios distintos):")
    for pais, cnt in cobertura_por_pais()[:8]:
        print(f"  {cnt:3d}  {pais}")
    print()

    filtro = args.solo.strip().lower()
    meds = [m for m in MEDICAMENTOS if not filtro or filtro in m["nombre"].lower()]
    con_respaldo = 0
    for med in meds:
        fases = fases_busqueda(args.pais, med)
        prin = next((t for f, t in fases if f == "principio"), [])
        marcas = next((t for f, t in fases if f == "marcas"), [])
        if not marcas:
            continue
        con_respaldo += 1
        ref = pais_referencia_para_med(int(med["n"]), args.pais)
        print(f"{med['nombre']}")
        print(f"  fase principio ({len(prin)}): {', '.join(prin[:5])}{'…' if len(prin) > 5 else ''}")
        print(f"  fase marcas ({len(marcas)}), ref={ref or '—'}: {', '.join(marcas)}")
        print()

    print(f"Principios con búsqueda de respaldo en {args.pais}: {con_respaldo}/{len(meds)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
