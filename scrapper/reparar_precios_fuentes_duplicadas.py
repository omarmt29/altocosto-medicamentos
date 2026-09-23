#!/usr/bin/env python3
"""Dry-run / apply: aplanar precios hist dañados al unificar fuentes → precio vivo PDP."""
from __future__ import annotations

import argparse
import re
from typing import Any

from sqlalchemy import text

from db import engine
from scrapper import repositorio as r
from scrapper import repositorio_historial as rh

FARMACIAS = ("FarmaValue", "Carol", "Los Hidalgos", "Qualipharma")
EPS = 0.05


def _url_key(url: str | None) -> str | None:
    u = str(url or "").strip().lower()
    if not u.startswith(("http://", "https://")):
        return None
    if "farmacias.do" in u:
        return None
    # FarmaValue: país + product id
    m = re.search(r"farmavalue\.com/([a-z]{2})/products/(\d+)", u)
    if m:
        return f"fv:{m.group(1)}:{m.group(2)}"
    # Carol
    m = re.search(r"farmaciacarol\.com/([^/?#]+)", u)
    if m:
        return f"carol:{m.group(1)}"
    # Hidalgos
    m = re.search(r"farmaciasloshidalgos\.com[^/]*/producto/([^/?#]+)", u)
    if m:
        return f"hid:{m.group(1)}"
    # Qualipharma
    m = re.search(r"qualipharma[^/]*/([^/?#]+)", u)
    if m:
        return f"qp:{m.group(1)}"
    # fallback: path sin query
    return "url:" + re.sub(r"[?#].*$", "", u).rstrip("/")


def collect_targets() -> list[dict[str, Any]]:
    qs, qt, _, _ = rh._ids()
    schema = rh.resumen_config()["schema"]
    qlive = f"[{schema}].[{r.TABLA}]"
    farms_sql = ", ".join(f"N'{f}'" for f in FARMACIAS)

    with engine().connect() as c:
        live_rows = [
            dict(x)
            for x in c.execute(
                text(
                    f"""
                SELECT n_lista, pais, farmacia, precio, moneda, precio_lista, precio_oferta,
                       fuente_url, nombre_comercial, concentracion, presentacion
                FROM {qlive}
                WHERE farmacia IN ({farms_sql})
                  AND precio IS NOT NULL
                  AND fuente_url IS NOT NULL
                  AND fuente_url NOT LIKE N'%farmacias.do%'
            """
                )
            ).mappings()
        ]

        by_url: dict[tuple, dict] = {}
        by_pk: dict[tuple, dict] = {}
        for f in live_rows:
            n = int(f["n_lista"] or 0)
            pais = str(f["pais"] or "").strip()
            far = rh._norm_farmacia(f.get("farmacia"))
            uk = _url_key(f.get("fuente_url"))
            pk = rh.producto_key_fila(f)
            payload = {
                "n_lista": n,
                "pais": pais,
                "farmacia": far,
                "precio": round(float(f["precio"]), 4),
                "moneda": str(f.get("moneda") or "USD").upper(),
                "precio_lista": float(f["precio_lista"]) if f.get("precio_lista") is not None else None,
                "precio_oferta": float(f["precio_oferta"]) if f.get("precio_oferta") is not None else None,
                "fuente_url": str(f.get("fuente_url") or "").strip() or None,
                "nombre": f.get("nombre_comercial"),
                "url_key": uk,
                "producto_key": pk,
            }
            if uk:
                by_url[(n, pais, far, uk)] = payload
            by_pk[(n, pais, far, pk)] = payload

        hist = [
            dict(x)
            for x in c.execute(
                text(
                    f"""
                SELECT id, n_lista, pais, farmacia, producto_key, fecha_dato,
                       precio, moneda, precio_usd, precio_lista, precio_oferta,
                       fuente_url, nombre_comercial
                FROM {qs}.{qt}
                WHERE farmacia IN ({farms_sql})
                  AND precio IS NOT NULL
            """
                )
            ).mappings()
        ]

    # Agrupar hist por (n,pais,far, match_key) donde match_key es url_key o pk
    groups: dict[tuple, dict[str, Any]] = {}
    for h in hist:
        n = int(h["n_lista"] or 0)
        pais = str(h["pais"] or "").strip()
        far = rh._norm_farmacia(h.get("farmacia"))
        uk = _url_key(h.get("fuente_url"))
        pk = str(h.get("producto_key") or "")
        live = None
        gkey = None
        if uk and (n, pais, far, uk) in by_url:
            live = by_url[(n, pais, far, uk)]
            gkey = ("url", n, pais, far, uk)
        elif (n, pais, far, pk) in by_pk:
            live = by_pk[(n, pais, far, pk)]
            gkey = ("pk", n, pais, far, pk)
        if not live or not gkey:
            continue
        g = groups.setdefault(
            gkey,
            {"live": live, "rows": [], "precios": set(), "nombre": h.get("nombre_comercial")},
        )
        g["rows"].append(h)
        g["precios"].add(round(float(h["precio"]), 4))

    targets = []
    for gkey, g in groups.items():
        live_p = g["live"]["precio"]
        precios = sorted(g["precios"])
        # Solo series con salto real (el “cambio” falso en el gráfico).
        if len(precios) <= 1:
            continue
        if max(precios) - min(precios) <= EPS:
            continue

        bad = [h for h in g["rows"] if abs(round(float(h["precio"]), 4) - live_p) > EPS]
        if not bad:
            continue
        targets.append(
            {
                "key": gkey,
                "live": g["live"],
                "nombre": g["nombre"] or g["live"].get("nombre"),
                "precios_hist": precios,
                "filas_totales": len(g["rows"]),
                "filas_a_corregir": len(bad),
                "ids": [int(h["id"]) for h in bad],
                "rows_bad": bad,
            }
        )
    return targets


def aplicar(targets: list[dict[str, Any]], *, dry_run: bool) -> dict[str, int]:
    qs, qt, _, _ = rh._ids()
    stats = {"series": len(targets), "filas": 0}
    if dry_run:
        for t in targets:
            stats["filas"] += t["filas_a_corregir"]
        return stats

    with engine().begin() as conn:
        for t in targets:
            live = t["live"]
            for h in t["rows_bad"]:
                old_p = float(h["precio"])
                new_p = float(live["precio"])
                old_usd = h.get("precio_usd")
                new_usd = None
                if old_usd is not None and old_p:
                    try:
                        new_usd = float(old_usd) * (new_p / old_p)
                    except Exception:
                        new_usd = None
                conn.execute(
                    text(
                        f"""
                        UPDATE {qs}.{qt}
                        SET precio = :precio,
                            moneda = :moneda,
                            precio_usd = COALESCE(:precio_usd, precio_usd),
                            precio_lista = COALESCE(:precio_lista, precio_lista),
                            precio_oferta = :precio_oferta,
                            fuente_url = COALESCE(:fuente_url, fuente_url)
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": int(h["id"]),
                        "precio": new_p,
                        "moneda": live["moneda"],
                        "precio_usd": new_usd,
                        "precio_lista": live.get("precio_lista"),
                        "precio_oferta": live.get("precio_oferta"),
                        "fuente_url": live.get("fuente_url"),
                    },
                )
                stats["filas"] += 1
    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    rh.asegurar_tabla()
    targets = collect_targets()
    print(f"series a reparar: {len(targets)}")
    for t in sorted(targets, key=lambda x: (-x["filas_a_corregir"], str(x["nombre"]))):
        live = t["live"]
        print(
            f"- {live['farmacia']} | {live['pais']} | {t['nombre']}\n"
            f"  hist {t['precios_hist']} → live {live['precio']} {live['moneda']} "
            f"({t['filas_a_corregir']}/{t['filas_totales']} filas)"
        )
    stats = aplicar(targets, dry_run=not args.apply)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"\n{mode}: series={stats['series']} filas={stats['filas']}")


if __name__ == "__main__":
    main()
