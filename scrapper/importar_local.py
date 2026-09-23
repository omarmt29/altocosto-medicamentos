#!/usr/bin/env python3
"""
Importa export local (JSON/XLSX) → SQL Server (medicamentos_altos_costos_america).

Uso en el servidor (con .env y acceso a BD):

    python scrapper/importar_local.py export_local/corrida_20260831-1200
    python scrapper/importar_local.py export_local/corrida_20260831-1200/farmacity.xlsx
    python scrapper/importar_local.py export_local/corrida_20260831-1200 --dry-run

Acepta:
  - carpeta con manifest.json + *.json por fuente
  - un solo .json o .xlsx
  - TODAS_las_fuentes.xlsx / .json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.export_local import COLUMNAS_EXPORT  # noqa: E402
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos  # noqa: E402


def _parse_fecha(v: Any) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    s = str(v).strip()
    if not s:
        return None
    return s[:10]


def _parse_precio(v: Any) -> float | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _celda_str(v: Any) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s or None


def fila_desde_dict(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col in COLUMNAS_EXPORT:
        out[col] = raw.get(col)
    out["n_lista"] = int(out["n_lista"]) if out.get("n_lista") not in (None, "") else 0
    out["precio"] = _parse_precio(out.get("precio"))
    out["fecha_dato"] = _parse_fecha(out.get("fecha_dato")) or date.today().isoformat()
    fp = out.get("fecha_publicacion")
    if fp not in (None, ""):
        out["fecha_publicacion"] = _parse_fecha(fp)
    for k in (
        "pais",
        "farmacia",
        "fuente_url",
        "id_producto_farmacia",
        "sku",
        "medicamento_lista",
        "programa",
        "nombre_comercial",
        "principio_activo",
        "concentracion",
        "cantidad_concentracion",
        "unidad_concentracion",
        "presentacion",
        "tipo_presentacion",
        "cantidad_presentacion",
        "alcance_presentacion",
        "laboratorio",
        "moneda",
        "disponibilidad",
        "calidad",
        "observacion",
    ):
        out[k] = _celda_str(out.get(k))
    if not out.get("id_producto_farmacia"):
        raise ValueError("Fila sin id_producto_farmacia")
    if not out.get("pais") or not out.get("farmacia"):
        raise ValueError("Fila sin pais/farmacia")
    return out


def cargar_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path.name}: se esperaba lista JSON")
    return [fila_desde_dict(x) for x in data if isinstance(x, dict)]


def cargar_excel(path: Path) -> list[dict[str, Any]]:
    df = pd.read_excel(path, sheet_name=0)
    filas: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        raw = {col: row[col] if col in df.columns else None for col in COLUMNAS_EXPORT}
        filas.append(fila_desde_dict(raw))
    return filas


def cargar_archivo(path: Path) -> list[dict[str, Any]]:
    suf = path.suffix.lower()
    if suf == ".json":
        return cargar_json(path)
    if suf in (".xlsx", ".xls"):
        return cargar_excel(path)
    raise ValueError(f"Formato no soportado: {path}")


def archivos_en_carpeta(carpeta: Path) -> list[Path]:
    manifest = carpeta / "manifest.json"
    if manifest.exists():
        meta = json.loads(manifest.read_text(encoding="utf-8"))
        out: list[Path] = []
        for fu in meta.get("fuentes") or []:
            j = fu.get("json")
            if j:
                p = carpeta / j
                if p.exists():
                    out.append(p)
        if out:
            return out
    # Sin manifest: todos los JSON sueltos (excepto consolidado si hay individuales)
    jsons = sorted(carpeta.glob("*.json"))
    jsons = [p for p in jsons if p.name not in ("manifest.json", "TODAS_las_fuentes.json")]
    if jsons:
        return jsons
    xlsx = carpeta / "TODAS_las_fuentes.xlsx"
    if xlsx.exists():
        return [xlsx]
    consolidado = carpeta / "TODAS_las_fuentes.json"
    if consolidado.exists():
        return [consolidado]
    raise SystemExit(f"No hay JSON/XLSX importables en {carpeta}")


def importar_filas(filas: list[dict[str, Any]], *, dry_run: bool, purgar: bool) -> dict[str, Any]:
    if not filas:
        return {"filas": 0, "upserts": 0}
    if dry_run:
        por_far: dict[str, int] = {}
        for f in filas:
            k = f"{f['pais']} · {f['farmacia']}"
            por_far[k] = por_far.get(k, 0) + 1
        print("DRY-RUN — no se escribe en BD:")
        for k, n in sorted(por_far.items()):
            print(f"  {n:4d}  {k}")
        return {"filas": len(filas), "upserts": 0, "dry_run": True}

    asegurar_tabla()
    res = guardar_filas(filas)
    borrados = 0
    if purgar:
        grupos: dict[tuple[str, str], list[tuple[str, int]]] = {}
        for f in filas:
            key = (f["pais"], f["farmacia"])
            grupos.setdefault(key, []).append((f["id_producto_farmacia"], f["n_lista"]))
        for (pais, farmacia), vigentes in grupos.items():
            borrados += purgar_obsoletos(pais, farmacia, vigentes)
    return {"filas": len(filas), "upserts": res["upserts"], "obsoletos": borrados, "total_tabla": res["total_tabla"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Importar export local → BD")
    parser.add_argument("ruta", type=Path, help="Carpeta de corrida, .json o .xlsx")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar conteos")
    parser.add_argument("--sin-purgar", action="store_true", help="No borrar SKUs obsoletos por farmacia")
    args = parser.parse_args()

    ruta = args.ruta
    if not ruta.exists():
        print(f"No existe: {ruta}")
        return 1

    paths: list[Path]
    if ruta.is_dir():
        paths = archivos_en_carpeta(ruta)
    else:
        paths = [ruta]

    total_filas: list[dict[str, Any]] = []
    for p in paths:
        try:
            lote = cargar_archivo(p)
            print(f"{p.name}: {len(lote)} filas")
            total_filas.extend(lote)
        except Exception as exc:
            print(f"  omitido {p.name}: {exc}")

    if not total_filas:
        print("Nada que importar.")
        return 1

    stats = importar_filas(total_filas, dry_run=args.dry_run, purgar=not args.sin_purgar)
    if not args.dry_run:
        print(
            f"MERGE {stats.get('upserts', 0)} filas · obsoletos: {stats.get('obsoletos', 0)} · "
            f"total tabla: {stats.get('total_tabla', contar())}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
