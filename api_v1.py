"""API de consumo para el servidor que se lleva los precios.

La data en este host dura RETENCION_DIAS (3). farmacias.do no se sirve.
Autenticación: header X-API-Key o Authorization: Bearer <API_KEY>.
"""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy import text

import db

RETENCION_DIAS = int(os.getenv("RETENCION_DIAS", "3") or "3")


def api_key_ok(header_key: str | None, authorization: str | None) -> bool:
    esperada = (os.getenv("API_KEY") or "").strip()
    if not esperada:
        return False
    if header_key and header_key.strip() == esperada:
        return True
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip() == esperada
    return False


def _excluir_farmacias() -> str:
    return (
        "farmacia <> 'farmacias.do' "
        "AND (fuente_url IS NULL OR lower(fuente_url) NOT LIKE '%farmacias.do%')"
    )


def _pagina(qs: dict, default_limite: int = 500, tope: int = 2000) -> tuple[int, int]:
    def uno(nombre: str) -> str | None:
        vals = qs.get(nombre)
        if not vals:
            return None
        v = str(vals[0]).strip()
        return v or None

    try:
        limite = int(uno("limite") or default_limite)
    except ValueError:
        limite = default_limite
    try:
        offset = int(uno("offset") or 0)
    except ValueError:
        offset = 0
    limite = max(1, min(limite, tope))
    offset = max(0, offset)
    return limite, offset


def listar_precios(qs: dict) -> dict[str, Any]:
    limite, offset = _pagina(qs)
    params: dict[str, Any] = {"limite": limite, "offset": offset}
    where = [_excluir_farmacias()]

    def uno(nombre: str) -> str | None:
        vals = qs.get(nombre)
        if not vals:
            return None
        v = str(vals[0]).strip()
        return v or None

    pais = uno("pais")
    farmacia = uno("farmacia")
    q = uno("q")
    n_lista = uno("n_lista")
    fecha = uno("fecha") or uno("fecha_dato")
    if pais:
        where.append("pais = :pais")
        params["pais"] = pais
    if farmacia:
        where.append("farmacia = :farmacia")
        params["farmacia"] = farmacia
    if n_lista and n_lista.lstrip("-").isdigit():
        where.append("n_lista = :n_lista")
        params["n_lista"] = int(n_lista)
    if fecha:
        where.append("fecha_dato = :fecha")
        params["fecha"] = fecha[:10]
    if q:
        where.append(
            "(lower(medicamento_lista) LIKE :q OR lower(COALESCE(nombre_comercial, '')) LIKE :q "
            "OR lower(COALESCE(principio_activo, '')) LIKE :q)"
        )
        params["q"] = f"%{q.lower()}%"

    clausula = " AND ".join(where)
    schema = db.resumen_config()["schema"]
    tabla = f'"{schema}".medicamentos_altos_costos_america'
    with db.engine().connect() as conn:
        total = conn.execute(
            text(f"SELECT COUNT(*) FROM {tabla} WHERE {clausula}"),
            params,
        ).scalar_one()
        rows = conn.execute(
            text(
                f"SELECT id, pais, farmacia, fuente_url, id_producto_farmacia, sku, "
                f"n_lista, medicamento_lista, programa, nombre_comercial, principio_activo, "
                f"concentracion, presentacion, laboratorio, precio, precio_lista, precio_oferta, "
                f"moneda, disponibilidad, calidad, observacion, fecha_dato, fecha_registro, "
                f"fecha_actualizacion "
                f"FROM {tabla} WHERE {clausula} "
                f"ORDER BY fecha_dato DESC, n_lista, pais, farmacia, id "
                f"LIMIT :limite OFFSET :offset"
            ),
            params,
        ).mappings().all()
    filas = []
    for r in rows:
        item = dict(r)
        for k, v in list(item.items()):
            if hasattr(v, "isoformat"):
                item[k] = v.isoformat()
            elif v is not None and hasattr(v, "as_tuple"):
                item[k] = float(v)
        filas.append(item)
    return {
        "ok": True,
        "total": int(total or 0),
        "limite": limite,
        "offset": offset,
        "retencion_dias": RETENCION_DIAS,
        "filas": filas,
    }


def resumen() -> dict[str, Any]:
    schema = db.resumen_config()["schema"]
    tabla = f'"{schema}".medicamentos_altos_costos_america'
    excl = _excluir_farmacias()
    with db.engine().connect() as conn:
        filas = conn.execute(
            text(
                f"SELECT pais, farmacia, COUNT(*) AS n, MAX(fecha_dato) AS fecha "
                f"FROM {tabla} WHERE {excl} "
                f"GROUP BY pais, farmacia ORDER BY pais, farmacia"
            )
        ).mappings().all()
        total = conn.execute(
            text(f"SELECT COUNT(*) FROM {tabla} WHERE {excl}")
        ).scalar_one()
    fuentes = []
    for r in filas:
        fuentes.append(
            {
                "pais": r["pais"],
                "farmacia": r["farmacia"],
                "filas": int(r["n"] or 0),
                "fecha": r["fecha"].isoformat() if hasattr(r["fecha"], "isoformat") else r["fecha"],
            }
        )
    return {
        "ok": True,
        "total": int(total or 0),
        "retencion_dias": RETENCION_DIAS,
        "fuentes": fuentes,
        **fuentes_adicionales(),
    }


def listar_exportacion(nombre: str, qs: dict) -> dict[str, Any]:
    """Sirve el último snapshot completo publicado por el flujo diario."""
    from scrapper.exportaciones_diarias import leer, ahora, RECURSOS

    if nombre not in RECURSOS:
        raise ValueError("Fuente desconocida")
    snapshot = leer(nombre)
    estado = leer(f"{nombre}-estado") or {"estado": "pendiente"}
    if snapshot is None:
        return {"ok": False, "fuente": nombre, "error": "Sin snapshot; actualización pendiente",
                "actualizacion": estado, "total": 0, "filas": []}
    filas = snapshot["filas"]
    def uno(key):
        return (qs.get(key) or [None])[0]
    for campo in ("pais", "moneda", "n_lista", "fecha_dato"):
        valor = uno(campo) or (uno("fecha") if campo == "fecha_dato" else None)
        if valor is not None:
            campo_fila = "fecha" if nombre == "tasas" and campo == "fecha_dato" else campo
            filas = [f for f in filas if str(f.get(campo_fila)) == str(valor)]
    q = uno("q")
    if q:
        campos = ("medicamento_lista", "nombre_comercial", "nombre_medicamento", "inn", "active_substance")
        filas = [f for f in filas if any(str(f.get(k) or "").lower().find(q.lower()) >= 0 for k in campos)]
    limite, offset = _pagina(qs)
    return {"ok": True, "fuente": nombre, "total": len(filas), "limite": limite, "offset": offset,
            "actualizado_en": snapshot["actualizado_en"],
            "desactualizado": snapshot["actualizado_en"][:10] != ahora().date().isoformat(),
            "actualizacion": estado, "filas": filas[offset:offset + limite]}


def fuentes_adicionales() -> dict[str, Any]:
    from scrapper.fuentes_monedas import FUENTES
    from scrapper.exportaciones_diarias import leer, ahora, RECURSOS
    XLSX_URL = "https://www.ema.europa.eu/en/documents/report/medicines-output-medicines-report_en.xlsx"
    FUENTE_PAGE = "https://www.ema.europa.eu/en/medicines/download-medicine-data"
    ORANGE_ZIP_URL = "https://www.fda.gov/media/76860/download"
    PURPLE_PATENTS_URL = "https://purplebooksearch.fda.gov/index.cfm?event=patentlist"
    DOWNLOADS_URL = "https://purplebooksearch.fda.gov/index.cfm?event=downloads"

    estados = {}
    for nombre in RECURSOS:
        snapshot = leer(nombre)
        estados[nombre] = {"endpoint": f"/api/v1/{nombre}", "disponible": snapshot is not None,
                          "total": len(snapshot["filas"]) if snapshot else 0,
                          "actualizado_en": snapshot["actualizado_en"] if snapshot else None,
                          "desactualizado": not snapshot or snapshot["actualizado_en"][:10] != ahora().date().isoformat(),
                          "actualizacion": leer(f"{nombre}-estado") or {"estado": "pendiente"}}
    return {"monedas": list(FUENTES.values()), "regulatorias": [
        {"nombre": "FDA / openFDA Drug Labels", "url": "https://api.fda.gov/drug/label.json", "endpoint": "/api/v1/fda"},
        {"nombre": "Drugs@FDA", "url": "https://api.fda.gov/drug/drugsfda.json", "endpoint": "/api/v1/fda"},
        {"nombre": "Orange Book", "url": ORANGE_ZIP_URL, "endpoint": "/api/v1/fda"},
        {"nombre": "Purple Book", "url": DOWNLOADS_URL, "endpoint": "/api/v1/purple-book"},
        {"nombre": "Purple Book Patent List", "url": PURPLE_PATENTS_URL, "endpoint": "/api/v1/fda"},
        {"nombre": "EMA medicines", "url": FUENTE_PAGE, "descarga_url": XLSX_URL, "endpoint": "/api/v1/ema"},
    ], "exportaciones": estados}
