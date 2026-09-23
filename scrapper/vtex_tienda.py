"""Búsqueda VTEX compartida (Farmacity, Locatel, Pague Menos)."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
import urllib3

from lista import MEDICAMENTOS
from scrapper.ficha import parse_ficha
from scrapper.matching import clasificar, coincide
from scrapper.report_seeds import extra_terms_for_med, seed_match_for_med
from scrapper.busqueda_marcas import combinar_fases
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos
from scrapper.vtex_urls import (
    base_siman_pdp,
    corregir_url_siman,
    es_farmacia_siman,
    producto_en_tienda_siman,
    resolver_pdp_vtex,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PAUSA = 0.25
PAGE = 50
MAX_PAGINAS = 4
TIMEOUT = 40
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def queries_es(med: dict[str, Any], pais: str | None = None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    extras = extra_terms_for_med(pais, med) if pais else []
    for raw in list(med["aliases"]) + extras:
        q = str(raw).strip()
        if len(q) < 4:
            continue
        k = q.lower()
        if k not in seen:
            seen.add(k)
            out.append(q)
    return out


def queries_br(med: dict[str, Any], pais: str | None = None) -> list[str]:
    """Aliases + variantes frecuentes en catálogos BR (sufijo -e, imuno, interferona)."""
    out: list[str] = []
    seen: set[str] = set()
    extras = extra_terms_for_med(pais or "Brasil", med) if (pais or "Brasil") else []
    for raw in list(med["aliases"]) + extras:
        alias = str(raw).strip()
        if len(alias) < 4:
            continue
        candidatos = [alias]
        low = alias.lower()
        if low.endswith(("mab", "nib", "mib", "lib")) and not low.endswith("e"):
            candidatos.append(alias + "e")
        if low.startswith("inmuno"):
            candidatos.append("imuno" + alias[6:])
        if low.startswith("interferon") and "interferona" not in low:
            candidatos.append(
                alias.replace("interferon", "interferona").replace("Interferon", "Interferona")
            )
        for q in candidatos:
            k = q.lower()
            if k not in seen:
                seen.add(k)
                out.append(q)
    return out


def queries_para(pais: str, med: dict[str, Any]) -> list[str]:
    if str(pais).lower() in ("brasil", "brazil", "br"):
        return queries_br(med, pais)
    return queries_es(med, pais)


def fases_busqueda(pais: str, med: dict[str, Any]) -> list[tuple[str, list[str]]]:
    return combinar_fases(pais, med, queries_para)


def cache_path(cache: Path, alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return cache / f"{safe}.json"


def session(base: str, *, verify: bool = True, accept_language: str | None = None) -> requests.Session:
    s = requests.Session()
    s.verify = verify
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": accept_language
            or "es,es-419;q=0.9,en;q=0.7",
            "Referer": base.rstrip("/") + "/",
        }
    )
    return s


def buscar_vtex(
    s: requests.Session,
    alias: str,
    *,
    base: str,
    cache: Path,
    forzar: bool,
) -> tuple[list[dict[str, Any]], str, str | None]:
    """Devuelve (productos, fecha_dato, error). error no nulo = no se pudo ir a la red."""
    path = cache_path(cache, alias)
    if not forzar and path.exists() and path.stat().st_size >= 2:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            # Caché de www.siman.com mezcla catálogos; forzar re-scrape regional.
            if es_farmacia_siman(None, base) and any(
                "www.siman.com" in str(p.get("link") or "") for p in data[:8]
            ):
                forzar = True
            else:
                fecha = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
                return _filtrar_productos_siman(data, base), fecha, None
    productos: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for pagina in range(MAX_PAGINAS):
        inicio = pagina * PAGE
        fin = inicio + PAGE - 1
        url = (
            f"{base}/api/catalog_system/pub/products/search"
            f"?ft={quote(alias)}&_from={inicio}&_to={fin}"
        )
        time.sleep(PAUSA)
        r = None
        try:
            for intento in range(4):
                r = s.get(url, timeout=TIMEOUT)
                if r.status_code in (429, 500, 502, 503):
                    time.sleep(1.5 * (intento + 1))
                    continue
                break
        except requests.RequestException as exc:
            return [], datetime.now().date().isoformat(), str(exc)
        if r is None:
            break
        if r.status_code in (401, 403, 451):
            return [], datetime.now().date().isoformat(), f"bloqueado HTTP {r.status_code}"
        if r.status_code in (429, 500, 502, 503):
            return [], datetime.now().date().isoformat(), f"temporal HTTP {r.status_code}"
        if r.status_code not in (200, 206):
            return [], datetime.now().date().isoformat(), f"HTTP {r.status_code}"
        try:
            lote = r.json()
        except ValueError:
            return [], datetime.now().date().isoformat(), "respuesta no JSON"
        if not isinstance(lote, list) or not lote:
            break
        for prod in lote:
            pid = str(prod.get("productId") or "")
            if not pid or pid in vistos:
                continue
            vistos.add(pid)
            productos.append(prod)
        if len(lote) < PAGE:
            break
    cache.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(productos, ensure_ascii=False), encoding="utf-8")
    return _filtrar_productos_siman(productos, base), datetime.now().date().isoformat(), None


def _filtrar_productos_siman(productos: list[dict[str, Any]], base: str) -> list[dict[str, Any]]:
    """Solo productos que existen en el catálogo VTEX de esa tienda regional."""
    if not es_farmacia_siman(None, base):
        return productos
    out: list[dict[str, Any]] = []
    for prod in productos:
        pid = str(prod.get("productId") or "").strip()
        if not pid:
            continue
        link = resolver_pdp_vtex(base.rstrip("/"), pid)
        if not link:
            continue
        copia = dict(prod)
        copia["link"] = link
        out.append(copia)
    return out


def precio_item(item: dict[str, Any]) -> tuple[float | None, int]:
    """Precio base (lista) y señal de stock. Compat: retorna (precio_comparacion, qty)."""
    lista, oferta, qty = precios_item(item)
    return (lista or oferta), qty


def precios_item(item: dict[str, Any]) -> tuple[float | None, float | None, int]:
    """Devuelve (precio_lista, precio_oferta, qty).

    En VTEX, ``ListPrice`` es el PVP de lista y ``Price`` suele ser el
    precio con descuento/promo. La oferta solo se informa si es menor.
    """
    mejor_lista: float | None = None
    mejor_oferta: float | None = None
    qty = 0
    disponible = False
    for seller in item.get("sellers") or []:
        offer = seller.get("commertialOffer") or {}
        lista = 0.0
        oferta = 0.0
        try:
            lista = float(offer.get("ListPrice") or 0)
        except (TypeError, ValueError):
            lista = 0.0
        try:
            oferta = float(offer.get("Price") or 0)
        except (TypeError, ValueError):
            oferta = 0.0
        raw_q = offer.get("AvailableQuantity")
        try:
            q = int(raw_q) if raw_q is not None else 0
        except (TypeError, ValueError):
            q = 0
        isa = offer.get("IsAvailable")
        err = str(offer.get("GetInfoErrorMessage") or "").lower()
        sin_stock_msg = any(
            x in err
            for x in ("withoutstock", "no tiene inventario", "não tem estoque", "nao tem estoque", "sin stock")
        )
        if isa is True or q > 0:
            disponible = True
            qty = max(qty, q if q > 0 else 1)
        elif isa is False or sin_stock_msg:
            pass
        elif (lista > 0 or oferta > 0) and isa is None and raw_q is None:
            disponible = True
            qty = max(qty, 1)
        qty = max(qty, q)
        if lista > 0 and (mejor_lista is None or lista < mejor_lista):
            mejor_lista = lista
        if oferta > 0 and (mejor_oferta is None or oferta < mejor_oferta):
            mejor_oferta = oferta
    if not disponible:
        qty = 0
    elif qty <= 0:
        qty = 1
    if mejor_lista and mejor_oferta and mejor_oferta < mejor_lista * 0.999:
        return mejor_lista, mejor_oferta, qty
    base = mejor_lista or mejor_oferta
    return base, None, qty


def _spec_txt(prod: dict[str, Any], *claves: str) -> str:
    partes: list[str] = []
    for k in claves:
        v = prod.get(k)
        if isinstance(v, list):
            partes.extend(str(x) for x in v if x)
        elif v:
            partes.append(str(v))
    return " ".join(partes)


def blob_prod(prod: dict[str, Any], item: dict[str, Any]) -> str:
    return " ".join(
        str(x or "")
        for x in (
            prod.get("productName"),
            item.get("nameComplete") or item.get("name"),
            item.get("complementName"),
            prod.get("brand"),
            _spec_txt(prod, "Principio activo", "Drogas", "principio activo"),
        )
    )


def url_pdp(base: str, prod: dict[str, Any], item: dict[str, Any] | None = None) -> str:
    link = str(prod.get("link") or "").strip()
    if link.startswith("http"):
        return link[:500]
    slug = str(prod.get("linkText") or "").strip()
    if slug:
        return f"{base.rstrip('/')}/{slug}/p"[:500]
    return base


def url_pdp_fila(
    base: str,
    prod: dict[str, Any],
    *,
    pais: str,
    farmacia: str,
    item: dict[str, Any] | None = None,
) -> str:
    base_pdp = base_siman_pdp(pais, farmacia, base)
    if es_farmacia_siman(farmacia, base):
        pid = str(prod.get("productId") or "").strip()
        if pid and not producto_en_tienda_siman(pais, pid, farmacia=farmacia, base=base):
            nombre = str(
                item.get("nameComplete") if item else None
                or item.get("name") if item else None
                or prod.get("productName")
                or ""
            ).strip()
            from scrapper.vtex_urls import url_busqueda_vtex

            busqueda = url_busqueda_vtex(base_pdp, nombre)
            if busqueda:
                return busqueda
    raw = url_pdp(base_pdp, prod, item)
    return corregir_url_siman(raw, pais, farmacia)


def filas_de_productos(
    med: dict[str, Any],
    productos: list[dict[str, Any]],
    fecha_dato: str,
    vistos: set[tuple[str, int]],
    *,
    pais: str,
    farmacia: str,
    moneda: str,
    base: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for prod in productos:
        items = prod.get("items") or [prod]
        for item in items:
            nombre = str(
                item.get("nameComplete")
                or item.get("name")
                or prod.get("productName")
                or ""
            ).strip()
            if not nombre:
                continue
            blob = blob_prod(prod, item)
            seed_match = seed_match_for_med(f"{blob} {nombre}", pais, med)
            if not coincide(blob, med) and not coincide(nombre, med) and not seed_match:
                continue
            precio_lista, precio_oferta, qty = precios_item(item)
            precio = precio_lista or precio_oferta
            if not precio:
                continue
            pid = str(item.get("itemId") or prod.get("productId") or "")
            if not pid:
                continue
            p_fake = {
                "nombre": nombre,
                "principios_activos": [prod.get("brand"), _spec_txt(prod, "Principio activo", "Drogas")],
                "tipo_presentacion": nombre,
                "laboratorio": prod.get("brand"),
            }
            med2, calidad, obs = clasificar(med, p_fake)
            if seed_match and calidad == "ok":
                calidad = "revisar"
            if seed_match:
                extra_obs = f"Coincidencia impulsada por faltantes {pais} del reporte Digemaps"
                obs = f"{obs} | {extra_obs}" if obs else extra_obs
            n_lista = int(med2["n"])
            clave = (pid, n_lista)
            if clave in vistos:
                continue
            vistos.add(clave)
            ficha = parse_ficha(nombre, med2)
            lab = (prod.get("brand") or ficha.get("laboratorio") or "")[:200] or None
            ean = str(item.get("ean") or prod.get("productReference") or pid)[:80]
            out.append(
                {
                    "pais": pais,
                    "farmacia": farmacia,
                    "fuente_url": url_pdp_fila(base, prod, pais=pais, farmacia=farmacia, item=item),
                    "id_producto_farmacia": pid[:80],
                    "sku": ean,
                    "n_lista": n_lista,
                    "medicamento_lista": str(med2["nombre"]),
                    "programa": str(med2["programa"]),
                    "nombre_comercial": nombre[:500],
                    "principio_activo": ficha.get("principio_activo")
                    or (_spec_txt(prod, "Principio activo", "Drogas")[:500] or None),
                    "concentracion": ficha.get("concentracion"),
                    "presentacion": ficha.get("presentacion"),
                    "laboratorio": lab,
                    "precio": precio,
                    "precio_lista": precio_lista or precio,
                    "precio_oferta": precio_oferta,
                    "moneda": moneda,
                    "disponibilidad": "Disponible" if qty > 0 else "Agotado",
                    "calidad": calidad,
                    "observacion": obs,
                    "fecha_publicacion": None,
                    "fecha_dato": fecha_dato,
                }
            )
    return out


def _cargar_todo_cache(cache: Path) -> list[tuple[list[dict[str, Any]], str]]:
    out: list[tuple[list[dict[str, Any]], str]] = []
    if not cache.exists():
        return out
    for path in sorted(cache.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, list) and data:
            fecha = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            out.append((data, fecha))
    return out


def recolectar(
    *,
    pais: str,
    farmacia: str,
    moneda: str,
    base: str,
    cache: Path,
    forzar: bool = False,
    meds: list[dict[str, Any]] | None = None,
    verify: bool = True,
    solo_cache: bool = False,
) -> list[dict[str, Any]]:
    s = session(
        base,
        verify=verify,
        accept_language=(
            "pt-BR,pt;q=0.9,es;q=0.8,en;q=0.7"
            if str(pais).lower() in ("brasil", "brazil", "br")
            else None
        ),
    )
    filas: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    trabajo = meds if meds is not None else MEDICAMENTOS
    red_caida = solo_cache
    aviso_red = False
    for med in trabajo:
        n_antes = len(filas)
        for fase, aliases in fases_busqueda(pais, med):
            if fase == "marcas" and len(filas) > n_antes:
                break
            for alias in aliases:
                if red_caida:
                    path = cache_path(cache, alias)
                    if not path.exists():
                        continue
                    productos, fecha, err = buscar_vtex(
                        s, alias, base=base, cache=cache, forzar=False
                    )
                else:
                    productos, fecha, err = buscar_vtex(
                        s, alias, base=base, cache=cache, forzar=forzar
                    )
                    if err:
                        bloqueado = (
                            err.startswith("bloqueado")
                            or "SSLError" in err
                            or "Blocked site" in err
                            or "Access Denied" in err
                        )
                        if bloqueado:
                            red_caida = True
                            if not aviso_red:
                                print(f"  red no disponible ({err}). Sigo con caché local.")
                                aviso_red = True
                        else:
                            print(f"  aviso {alias}: {err}")
                        continue
                filas.extend(
                    filas_de_productos(
                        med,
                        productos,
                        fecha,
                        vistos,
                        pais=pais,
                        farmacia=farmacia,
                        moneda=moneda,
                        base=base,
                    )
                )
        n_nuevas = len(filas) - n_antes
        marca = "·" if n_nuevas else " "
        print(f"  {marca} {n_nuevas:3d}  {med['nombre']}")
    if red_caida:
        extra = 0
        for productos, fecha in _cargar_todo_cache(cache):
            for med in trabajo:
                n0 = len(filas)
                filas.extend(
                    filas_de_productos(
                        med,
                        productos,
                        fecha,
                        vistos,
                        pais=pais,
                        farmacia=farmacia,
                        moneda=moneda,
                        base=base,
                    )
                )
                extra += len(filas) - n0
        if extra:
            print(f"  +{extra} SKU extra al rematar todo el caché")
        # El tablero vive del snapshot del día: si solo hay caché (proxy/WAF),
        # sellamos fecha_dato = hoy para que el país no “desaparezca”.
        hoy = datetime.now().date().isoformat()
        for f in filas:
            f["fecha_dato"] = hoy
            obs = str(f.get("observacion") or "").strip()
            nota = "PVP rematado desde caché local (red bloqueada)"
            if nota not in obs:
                f["observacion"] = f"{obs} | {nota}" if obs else nota
    return filas


def ejecutar(
    *,
    titulo: str,
    pais: str,
    farmacia: str,
    moneda: str,
    base: str,
    cache: Path,
    argv: list[str],
    verify: bool = True,
) -> int:
    forzar = "--fresh" in argv
    solo_fomac = "--fomac" in argv
    solo_cache = "--cache" in argv
    meds = MEDICAMENTOS
    if solo_fomac:
        meds = [m for m in MEDICAMENTOS if "FOMAC" in str(m["programa"])]
    print("=" * 64)
    print(titulo)
    if solo_fomac:
        print(f" Solo FOMAC ({len(meds)} moléculas)")
    if solo_cache:
        print(" Solo caché local (sin red)")
    print("=" * 64)
    filas = recolectar(
        pais=pais,
        farmacia=farmacia,
        moneda=moneda,
        base=base,
        cache=cache,
        forzar=forzar,
        meds=meds,
        verify=verify,
        solo_cache=solo_cache,
    )
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    revisar = len(filas) - ok
    con_precio = sum(1 for f in filas if f.get("precio"))
    print(f"Lista: {len(meds)} medicamentos")
    print(f"Coincidencias a guardar: {len(filas)}  (ok={ok}, revisar={revisar}, con precio={con_precio})")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    if solo_fomac:
        borrados = 0
    elif not filas:
        # Red bloqueada / sin hits: no borrar el histórico de esa farmacia.
        borrados = 0
        print("  aviso: 0 coincidencias — no se purgan filas existentes")
    else:
        borrados = purgar_obsoletos(
            pais,
            farmacia,
            [(f["id_producto_farmacia"], f["n_lista"]) for f in filas],
        )
    print(
        f"MERGE {res['upserts']} filas · "
        f"obsoletos: {borrados} · "
        f"{pais} {farmacia}: {contar(pais, farmacia)} · "
        f"total tabla: {contar()}"
    )
    by_med: dict[str, int] = {}
    for f in filas:
        by_med[f["medicamento_lista"]] = by_med.get(f["medicamento_lista"], 0) + 1
    for nombre, n in sorted(by_med.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {n:2d}  {nombre}")
    return 0
