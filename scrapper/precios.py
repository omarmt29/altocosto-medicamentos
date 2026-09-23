"""Normalización de precio base (lista) vs precio oferta (descuento).

Convención del proyecto:
- ``precio`` / comparativo USD → PVP de **lista**
- ``precio_lista`` → mismo PVP base en moneda local
- ``precio_oferta`` → solo si la farmacia publica un precio menor al de lista
"""

from __future__ import annotations

from typing import Any


def as_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def pares_lista_oferta(
    lista: Any,
    oferta: Any,
) -> tuple[float | None, float | None]:
    """Devuelve (precio_lista, precio_oferta). Oferta solo si es menor que lista."""
    li = as_float(lista)
    of = as_float(oferta)
    if li and of and of < li * 0.999:
        return li, of
    base = li or of
    return base, None


def normalizar_fila_precios(fila: dict[str, Any]) -> dict[str, Any]:
    """Garantiza precio_lista (y oferta válida) en cualquier fila antes de persistir.

    Si el scraper solo mandó ``precio``, se usa como base.
    Si mandó oferta inválida (>= lista), se descarta.
    ``precio`` queda alineado al PVP de lista para el comparativo.
    """
    precio = as_float(fila.get("precio"))
    lista = as_float(fila.get("precio_lista"))
    oferta = as_float(fila.get("precio_oferta"))

    if lista is None and oferta is not None and precio is not None and oferta < precio * 0.999:
        # Caso raro: mandaron precio=lista implícito y oferta aparte
        lista = precio
    elif lista is None:
        lista = precio

    lista, oferta = pares_lista_oferta(lista, oferta if oferta is not None else None)
    # Si no había oferta explícita pero precio < lista (scraper viejo), no inventamos:
    # solo usamos precio_oferta cuando viene marcado.

    if lista is not None:
        fila["precio"] = lista
        fila["precio_lista"] = lista
    else:
        fila["precio_lista"] = None

    fila["precio_oferta"] = oferta
    return fila


def _wc_minor(raw: Any, prices: dict[str, Any]) -> float | None:
    if raw in (None, ""):
        return None
    raw_s = str(raw).strip().replace(",", "")
    try:
        n = float(raw_s)
    except ValueError:
        return None
    if n <= 0:
        return None
    minor = int(prices.get("currency_minor_unit") or 0)
    if "." not in raw_s and minor > 0:
        n = n / (10 ** minor)
    return n if n > 0 else None


def precios_woocommerce(prod: dict[str, Any]) -> tuple[float | None, float | None]:
    """WooCommerce Store API: regular_price = lista, sale/price = oferta."""
    prices = prod.get("prices") or {}
    lista = _wc_minor(prices.get("regular_price"), prices)
    venta = _wc_minor(prices.get("sale_price") or prices.get("price"), prices)
    if lista is None:
        lista = venta
        venta = None
    return pares_lista_oferta(lista, venta)


def precios_magento(item: dict[str, Any]) -> tuple[float | None, float | None]:
    """Magento GraphQL: regular_price = lista, final_price = oferta si es menor."""
    try:
        mini = (item.get("price_range") or {}).get("minimum_price") or {}
        lista = as_float((mini.get("regular_price") or {}).get("value"))
        final = as_float((mini.get("final_price") or {}).get("value"))
    except (TypeError, ValueError, AttributeError):
        return None, None
    return pares_lista_oferta(lista, final)
