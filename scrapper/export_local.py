"""Exportar filas de scrapers a carpeta local (sin SQL Server).

Usado por run_local_bloqueadas.py e importar_local.py.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

# Columnas que acepta guardar_filas / MERGE en repositorio.py
COLUMNAS_EXPORT = [
    "pais",
    "farmacia",
    "fuente_url",
    "id_producto_farmacia",
    "sku",
    "n_lista",
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
    "precio",
    "moneda",
    "disponibilidad",
    "calidad",
    "observacion",
    "fecha_publicacion",
    "fecha_dato",
]


def _jsonable(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def normalizar_fila(fila: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col in COLUMNAS_EXPORT:
        out[col] = _jsonable(fila.get(col))
    return out


def normalizar_filas(filas: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalizar_fila(f) for f in filas]


def escribir_json(filas: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = normalizar_filas(filas)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def escribir_excel(filas: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = normalizar_filas(filas)
    df = pd.DataFrame(rows, columns=COLUMNAS_EXPORT)
    df.to_excel(path, index=False, sheet_name="filas")


def escribir_corrida(
    *,
    out_dir: Path,
    slug: str,
    pais: str,
    farmacia: str,
    filas: list[dict[str, Any]],
    notas: str | None = None,
) -> dict[str, Any]:
    """Guarda JSON + XLSX de una fuente dentro de out_dir."""
    base = out_dir / slug
    json_path = base.with_suffix(".json")
    xlsx_path = base.with_suffix(".xlsx")
    escribir_json(filas, json_path)
    escribir_excel(filas, xlsx_path)
    ok = sum(1 for f in filas if f.get("calidad") == "ok")
    con_precio = sum(1 for f in filas if f.get("precio"))
    meta = {
        "slug": slug,
        "pais": pais,
        "farmacia": farmacia,
        "filas": len(filas),
        "ok": ok,
        "revisar": len(filas) - ok,
        "con_precio": con_precio,
        "json": json_path.name,
        "xlsx": xlsx_path.name,
        "notas": notas or "",
    }
    return meta
