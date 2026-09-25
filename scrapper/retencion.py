"""Borra precios, historial y logs con más de RETENCION_DIAS días."""

from __future__ import annotations

import os
import time

from sqlalchemy import text

from db import engine, resumen_config

DIAS = int(os.getenv("RETENCION_DIAS", "3") or "3")


def purgar() -> dict[str, int]:
    schema = resumen_config()["schema"]
    dias = max(1, DIAS)
    tablas = {
        "precios": (
            f'"{schema}".medicamentos_altos_costos_america',
            "fecha_dato < CURRENT_DATE - make_interval(days => :dias)",
        ),
        "historial": (
            f'"{schema}".medicamentos_precios_historial',
            "fecha_dato < CURRENT_DATE - make_interval(days => :dias)",
        ),
        "jobs": (
            f'"{schema}".medicamentos_scrape_jobs',
            "fecha_registro < CURRENT_TIMESTAMP - make_interval(days => :dias)",
        ),
        "cron_pasos": (
            f'"{schema}".medicamentos_cron_pasos',
            "inicio < CURRENT_TIMESTAMP - make_interval(days => :dias)",
        ),
        "cron_corridas": (
            f'"{schema}".medicamentos_cron_corridas',
            "inicio < CURRENT_TIMESTAMP - make_interval(days => :dias)",
        ),
    }
    out: dict[str, int] = {}
    with engine().begin() as conn:
        for nombre, (tabla, where) in tablas.items():
            res = conn.execute(text(f"DELETE FROM {tabla} WHERE {where}"), {"dias": dias})
            out[nombre] = int(res.rowcount or 0)
    return out


def loop(cada_seg: int = 6 * 3600) -> None:
    while True:
        try:
            print("Retención:", purgar())
        except Exception as exc:
            print("Retención falló:", exc)
        time.sleep(cada_seg)


if __name__ == "__main__":
    print(purgar())
