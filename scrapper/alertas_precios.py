"""Detecta alertas de precio según criterios guardados en config."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from db import engine, resumen_config
from scrapper.repositorio_alertas_precios import (
    asegurar_tablas,
    listar_configs,
    registrar_alerta,
)
from scrapper.repositorio_historial import TABLA as TABLA_HIST


def _q(tabla: str) -> tuple[str, str]:
    schema = resumen_config()["schema"]
    return f"[{schema}]", f"[{tabla}]"


def _variacion_pct(antes: float, nuevo: float) -> float | None:
    if antes is None or nuevo is None:
        return None
    if antes <= 0:
        return None
    return round(((nuevo - antes) / antes) * 100.0, 4)


def _filas_comparables(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Últimas dos observaciones por producto (país+farmacia+producto_key) que matchean el criterio.

    Campos vacíos en el criterio = sin filtro (todos).
    """
    qschema, qtabla = _q(TABLA_HIST)
    where = [
        "h.precio_usd IS NOT NULL",
        "h.precio_usd > 0",
        "h.producto_key IS NOT NULL",
        "h.producto_key <> N''",
    ]
    params: dict[str, Any] = {}
    if cfg.get("n_lista") is not None and cfg.get("n_lista") != "":
        where.append("h.n_lista = :n_lista")
        params["n_lista"] = int(cfg["n_lista"])
    if cfg.get("pais"):
        where.append("h.pais = :pais")
        params["pais"] = cfg["pais"]
    if cfg.get("farmacia"):
        where.append("h.farmacia = :farmacia")
        params["farmacia"] = cfg["farmacia"]
    if cfg.get("producto_key"):
        where.append("h.producto_key = :producto_key")
        params["producto_key"] = cfg["producto_key"]
    if cfg.get("presentacion"):
        where.append("h.presentacion = :presentacion")
        params["presentacion"] = cfg["presentacion"]
    if cfg.get("concentracion"):
        where.append("h.concentracion = :concentracion")
        params["concentracion"] = cfg["concentracion"]

    # Dos fechas más recientes por llave de producto
    sql = f"""
    WITH base AS (
        SELECT
            h.n_lista,
            h.medicamento_lista,
            h.pais,
            h.farmacia,
            h.presentacion,
            h.concentracion,
            h.producto_key,
            h.fecha_dato,
            h.precio_usd,
            ROW_NUMBER() OVER (
                PARTITION BY h.pais, h.farmacia, h.producto_key
                ORDER BY h.fecha_dato DESC, h.id DESC
            ) AS rn
        FROM {qschema}.{qtabla} h
        WHERE {' AND '.join(where)}
    ),
    pares AS (
        SELECT
            a.n_lista,
            COALESCE(a.medicamento_lista, b.medicamento_lista) AS medicamento_lista,
            a.pais,
            a.farmacia,
            COALESCE(a.presentacion, b.presentacion) AS presentacion,
            COALESCE(a.concentracion, b.concentracion) AS concentracion,
            a.producto_key,
            b.fecha_dato AS fecha_dato_anterior,
            a.fecha_dato AS fecha_dato_nuevo,
            CAST(b.precio_usd AS FLOAT) AS precio_anterior_usd,
            CAST(a.precio_usd AS FLOAT) AS precio_nuevo_usd
        FROM base a
        INNER JOIN base b
            ON a.pais = b.pais
           AND a.farmacia = b.farmacia
           AND a.producto_key = b.producto_key
           AND a.rn = 1
           AND b.rn = 2
        WHERE a.fecha_dato > b.fecha_dato
    )
    SELECT * FROM pares
    """
    with engine().connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def evaluar_config(cfg: dict[str, Any], *, hoy: date | None = None) -> dict[str, Any]:
    hoy = hoy or date.today()
    insertadas = 0
    revisadas = 0
    por_tipo: dict[str, int] = {}
    baja = cfg.get("umbral_baja_pct")
    sube = cfg.get("umbral_sube_pct")
    try:
        baja_n = float(baja) if baja is not None else None
    except (TypeError, ValueError):
        baja_n = None
    try:
        sube_n = float(sube) if sube is not None else None
    except (TypeError, ValueError):
        sube_n = None

    for row in _filas_comparables(cfg):
        revisadas += 1
        antes = float(row["precio_anterior_usd"])
        nuevo = float(row["precio_nuevo_usd"])
        var = _variacion_pct(antes, nuevo)
        if var is None:
            continue
        eventos: list[tuple[str, float]] = []
        if baja_n is not None and var <= -abs(baja_n):
            eventos.append(("baja", abs(baja_n)))
        if sube_n is not None and var >= abs(sube_n):
            eventos.append(("sube", abs(sube_n)))
        for tipo, umbral in eventos:
            ok = registrar_alerta(
                {
                    "config_id": cfg.get("id"),
                    "fecha_alerta": hoy,
                    "tipo_alerta": tipo,
                    "n_lista": row.get("n_lista") if row.get("n_lista") is not None else cfg.get("n_lista"),
                    "medicamento_lista": row.get("medicamento_lista") or cfg.get("medicamento_lista"),
                    "pais": row.get("pais"),
                    "farmacia": row.get("farmacia"),
                    "presentacion": row.get("presentacion"),
                    "concentracion": row.get("concentracion"),
                    "producto_key": row.get("producto_key"),
                    "precio_anterior_usd": antes,
                    "precio_nuevo_usd": nuevo,
                    "variacion_pct": var,
                    "umbral_pct": umbral,
                    "fecha_dato_anterior": row.get("fecha_dato_anterior"),
                    "fecha_dato_nuevo": row.get("fecha_dato_nuevo"),
                    "detalle_json": {
                        "config_id": cfg.get("id"),
                        "config_nombre": cfg.get("nombre"),
                        "umbral_baja_pct": baja_n,
                        "umbral_sube_pct": sube_n,
                    },
                }
            )
            if ok:
                insertadas += 1
                por_tipo[tipo] = por_tipo.get(tipo, 0) + 1

    return {
        "config_id": cfg.get("id"),
        "revisadas": revisadas,
        "insertadas": insertadas,
        "por_tipo": por_tipo,
    }


def detectar_todas(*, hoy: date | None = None) -> dict[str, Any]:
    asegurar_tablas()
    hoy = hoy or date.today()
    configs = listar_configs(solo_activas=True)
    insertadas = 0
    revisadas = 0
    detalle = []
    for cfg in configs:
        r = evaluar_config(cfg, hoy=hoy)
        insertadas += int(r.get("insertadas") or 0)
        revisadas += int(r.get("revisadas") or 0)
        detalle.append(r)
    return {
        "ok": True,
        "fecha_alerta": hoy.isoformat(),
        "configs": len(configs),
        "revisadas": revisadas,
        "insertadas": insertadas,
        "detalle": detalle,
        "mensaje": (
            f"Precios: {insertadas} alerta(s) nueva(s) "
            f"en {len(configs)} criterio(s) activo(s)."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Detectar alertas de precios")
    p.parse_args(argv)
    r = detectar_todas()
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
