"""Compara dos snapshots FDA/EMA y lista moléculas nuevas (sin I/O).

Tipos:
  - primera_aparicion: el principio no estaba en el snapshot anterior
  - referencia_nueva: FDA pasa a tener producto de referencia
  - autorizacion_nueva: EMA Authorised (no genérico/biosimilar) que no existía
"""

from __future__ import annotations

from typing import Any


def _bit(valor: Any) -> bool:
    return valor in (1, True, "1", "true", "True")


def _n(fila: dict[str, Any]) -> int | None:
    try:
        return int(fila["n_lista"])
    except (TypeError, ValueError, KeyError):
        return None


def _mapa_fda(filas: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for fila in filas or []:
        n = _n(fila)
        if n is None:
            continue
        out[n] = fila
    return out


def _referencia_ema(fila: dict[str, Any]) -> bool:
    estado = str(fila.get("medicine_status") or "").strip().lower()
    if estado != "authorised":
        return False
    if _bit(fila.get("es_biosimilar")) or _bit(fila.get("es_generic")):
        return False
    return True


def _clave_ema(fila: dict[str, Any]) -> tuple[int, str] | None:
    n = _n(fila)
    if n is None:
        return None
    codigo = str(fila.get("ema_product_number") or "").strip()
    if not codigo:
        return None
    return n, codigo


def comparar_fda(
    anterior: list[dict[str, Any]] | None,
    actual: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Devuelve alertas candidatas FDA entre dos días."""
    ant = _mapa_fda(anterior or [])
    act = _mapa_fda(actual or [])
    alertas: list[dict[str, Any]] = []
    for n, fila in sorted(act.items()):
        nombre = str(fila.get("medicamento_lista") or "")
        prev = ant.get(n)
        if prev is None:
            alertas.append(
                {
                    "fuente": "FDA",
                    "tipo_alerta": "primera_aparicion",
                    "n_lista": n,
                    "medicamento_lista": nombre,
                    "clave_producto": str(n),
                    "estado_anterior": None,
                    "estado_nuevo": "presente",
                    "detalle": {
                        "resumen_clase": fila.get("resumen_clase"),
                        "tiene_referencia": _bit(fila.get("tiene_referencia")),
                        "fuente_url": fila.get("fuente_url"),
                    },
                }
            )
            continue
        if not _bit(prev.get("tiene_referencia")) and _bit(fila.get("tiene_referencia")):
            alertas.append(
                {
                    "fuente": "FDA",
                    "tipo_alerta": "referencia_nueva",
                    "n_lista": n,
                    "medicamento_lista": nombre,
                    "clave_producto": str(n),
                    "estado_anterior": "sin_referencia",
                    "estado_nuevo": "con_referencia",
                    "detalle": {
                        "resumen_clase": fila.get("resumen_clase"),
                        "fuente_url": fila.get("fuente_url"),
                    },
                }
            )
    return alertas


def comparar_ema(
    anterior: list[dict[str, Any]] | None,
    actual: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Devuelve alertas candidatas EMA entre dos días."""
    ant_filas = anterior or []
    act_filas = actual or []
    ant_n = {_n(f) for f in ant_filas if _n(f) is not None}
    ant_ref = {_clave_ema(f) for f in ant_filas if _referencia_ema(f) and _clave_ema(f)}
    alertas: list[dict[str, Any]] = []
    vistos_primera: set[int] = set()
    for fila in act_filas:
        n = _n(fila)
        if n is None:
            continue
        nombre = str(fila.get("medicamento_lista") or "")
        if n not in ant_n and n not in vistos_primera:
            vistos_primera.add(n)
            alertas.append(
                {
                    "fuente": "EMA",
                    "tipo_alerta": "primera_aparicion",
                    "n_lista": n,
                    "medicamento_lista": nombre,
                    "clave_producto": str(n),
                    "estado_anterior": None,
                    "estado_nuevo": "presente",
                    "detalle": {
                        "nombre_medicamento": fila.get("nombre_medicamento"),
                        "medicine_url": fila.get("medicine_url"),
                    },
                }
            )
        if not _referencia_ema(fila):
            continue
        clave = _clave_ema(fila)
        if clave is None or clave in ant_ref:
            continue
        alertas.append(
            {
                "fuente": "EMA",
                "tipo_alerta": "autorizacion_nueva",
                "n_lista": n,
                "medicamento_lista": nombre,
                "clave_producto": clave[1],
                "estado_anterior": None,
                "estado_nuevo": "Authorised",
                "detalle": {
                    "nombre_medicamento": fila.get("nombre_medicamento"),
                    "ema_product_number": clave[1],
                    "inn": fila.get("inn"),
                    "medicine_url": fila.get("medicine_url"),
                    "marketing_authorisation_date": fila.get("marketing_authorisation_date"),
                },
            }
        )
    return alertas
