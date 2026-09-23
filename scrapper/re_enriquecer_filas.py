"""
Re-aplica enriquecer_fila_estructurada a filas ya guardadas (p. ej. tras mejorar el parser).

Uso:
    python scrapper/re_enriquecer_filas.py
    python scrapper/re_enriquecer_filas.py --pais Ecuador
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.estructura_producto import enriquecer_fila_estructurada  # noqa: E402
from scrapper.repositorio import guardar_filas, listar_filas  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Re-enriquecer filas en tabla consolidada")
    ap.add_argument("--pais", default="", help="Filtrar por país (ej. Ecuador)")
    ap.add_argument("--todos", action="store_true", help="Incluir snapshots antiguos")
    args = ap.parse_args()

    filas = listar_filas(todos=args.todos)
    if args.pais:
        filas = [f for f in filas if str(f.get("pais") or "") == args.pais]
    if not filas:
        print("Sin filas para re-enriquecer.")
        return 1

    out = [enriquecer_fila_estructurada(dict(f)) for f in filas]
    res = guardar_filas(out)
    print(f"Re-enriquecidas {res.get('upserts', len(out))} filas" + (f" ({args.pais})" if args.pais else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
