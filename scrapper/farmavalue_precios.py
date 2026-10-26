"""Precio que muestra FarmaValue, no el neto cifrado del catálogo.

La ficha calcula el total así:

    (precio_sin_impuesto - descuento) * (1 + isv)

`precio_marcado`, cuando viene, es el precio anterior con impuesto.
El neto no es una oferta: la diferencia con el marcado es el impuesto.
"""

from __future__ import annotations

import math
from typing import Any


def numero_farmavalue(valor: Any) -> float | None:
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        n = float(valor)
        return n if math.isfinite(n) else None
    texto = str(valor).strip().replace(",", "")
    if not texto:
        return None
    try:
        n = float(texto)
    except ValueError:
        return None
    return n if math.isfinite(n) else None


def _redondeo_sitio(valor: float) -> float:
    """Math.round(100 * Number(bruto.toFixed(3))) / 100, para montos positivos."""
    miles = math.floor(valor * 1000 + 0.5) / 1000
    return math.floor(miles * 100 + 0.5) / 100


def _descuento_sitio(dcto: float | None, neto: float) -> float:
    if dcto is None or dcto <= 0 or dcto >= neto:
        return 0.0
    return math.floor(dcto * 100 + 0.5) / 100


def resolver_precios_farmavalue(
    neto: float | None,
    marcado: float | None,
    dcto: float | None,
    isv: float | None,
) -> tuple[float, float | None] | None:
    """Devuelve (precio_lista, precio_oferta).

    precio_lista es el precio anterior o el precio base de la ficha.
    precio_oferta es el total que paga el cliente cuando queda por debajo.
    """
    neto_ok = neto is not None and neto > 0
    marcado_ok = marcado is not None and marcado > 0
    if not neto_ok and not marcado_ok:
        return None
    if not neto_ok:
        return float(marcado), None

    impuesto = isv if isv is not None and 0 < isv <= 1 else 0.0
    descuento = _descuento_sitio(dcto, float(neto))
    pagable = _redondeo_sitio((float(neto) - descuento) * (1 + impuesto))
    lista = float(marcado) if marcado_ok else float(neto)
    if pagable > 0 and pagable < lista * 0.999:
        return lista, pagable
    return lista, None
