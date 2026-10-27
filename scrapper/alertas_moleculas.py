"""Detecta moléculas nuevas FDA/EMA comparando los dos últimos snapshots en SQL."""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db import engine, resumen_config
from scrapper.detectar_moleculas import comparar_ema, comparar_fda
from scrapper.repositorio_alertas_moleculas import asegurar_tabla, registrar_alerta
from scrapper.repositorio_ema import TABLA as TABLA_EMA
from scrapper.repositorio_fda_info import TABLA as TABLA_FDA


def _q(tabla: str) -> tuple[str, str]:
    schema = resumen_config()["schema"]
    return f"[{schema}]", f"[{tabla}]"


def _parse_fd(v: Any) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def periodos(tabla: str) -> list[date]:
    qschema, qtabla = _q(tabla)
    with engine().connect() as conn:
        rows = conn.execute(
            text(f"SELECT DISTINCT fecha_dato FROM {qschema}.{qtabla} ORDER BY fecha_dato DESC")
        ).scalars().all()
    out = []
    for r in rows:
        d = _parse_fd(r)
        if d:
            out.append(d)
    return out


def cargar(tabla: str, fecha: date) -> list[dict[str, Any]]:
    qschema, qtabla = _q(tabla)
    with engine().connect() as conn:
        rows = conn.execute(
            text(f"SELECT * FROM {qschema}.{qtabla} WHERE fecha_dato = :fd ORDER BY n_lista, id"),
            {"fd": fecha},
        ).mappings().all()
    return [dict(r) for r in rows]


def _guardar(candidatos: list[dict[str, Any]], *, hoy: date, actual: date, anterior: date | None) -> int:
    insertadas = 0
    for item in candidatos:
        detalle = dict(item.get("detalle") or {})
        detalle["snapshot_actual"] = actual.isoformat()
        detalle["snapshot_anterior"] = anterior.isoformat() if anterior else None
        ok = registrar_alerta(
            {
                "fecha_alerta": hoy,
                "fuente": item["fuente"],
                "tipo_alerta": item["tipo_alerta"],
                "n_lista": item["n_lista"],
                "medicamento_lista": item.get("medicamento_lista"),
                "clave_producto": item.get("clave_producto"),
                "estado_anterior": item.get("estado_anterior"),
                "estado_nuevo": item.get("estado_nuevo"),
                "detalle": detalle,
            }
        )
        if ok:
            insertadas += 1
    return insertadas


def detectar_fda(*, hoy: date | None = None) -> dict[str, Any]:
    asegurar_tabla()
    hoy = hoy or date.today()
    fechas = periodos(TABLA_FDA)
    if not fechas:
        return {"ok": True, "fuente": "FDA", "insertadas": 0, "mensaje": "Sin snapshots FDA."}
    actual = fechas[0]
    anterior = fechas[1] if len(fechas) > 1 else None
    candidatos = comparar_fda(
        cargar(TABLA_FDA, anterior) if anterior else [],
        cargar(TABLA_FDA, actual),
    )
    n = _guardar(candidatos, hoy=hoy, actual=actual, anterior=anterior)
    return {
        "ok": True,
        "fuente": "FDA",
        "insertadas": n,
        "candidatos": len(candidatos),
        "fecha_actual": actual.isoformat(),
        "fecha_anterior": anterior.isoformat() if anterior else None,
    }


def detectar_ema(*, hoy: date | None = None) -> dict[str, Any]:
    asegurar_tabla()
    hoy = hoy or date.today()
    fechas = periodos(TABLA_EMA)
    if not fechas:
        return {"ok": True, "fuente": "EMA", "insertadas": 0, "mensaje": "Sin snapshots EMA."}
    actual = fechas[0]
    anterior = fechas[1] if len(fechas) > 1 else None
    candidatos = comparar_ema(
        cargar(TABLA_EMA, anterior) if anterior else [],
        cargar(TABLA_EMA, actual),
    )
    n = _guardar(candidatos, hoy=hoy, actual=actual, anterior=anterior)
    return {
        "ok": True,
        "fuente": "EMA",
        "insertadas": n,
        "candidatos": len(candidatos),
        "fecha_actual": actual.isoformat(),
        "fecha_anterior": anterior.isoformat() if anterior else None,
    }


def detectar_todas(**kwargs: Any) -> dict[str, Any]:
    fda = detectar_fda(**kwargs)
    ema = detectar_ema(**kwargs)
    return {
        "ok": True,
        "insertadas": int(fda.get("insertadas") or 0) + int(ema.get("insertadas") or 0),
        "fda": fda,
        "ema": ema,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detectar moléculas nuevas FDA/EMA")
    parser.add_argument("--fuente", choices=("fda", "ema", "todas"), default="todas")
    args = parser.parse_args(argv)
    if args.fuente == "fda":
        r = detectar_fda()
    elif args.fuente == "ema":
        r = detectar_ema()
    else:
        r = detectar_todas()
    print(r)
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
