"""Búsqueda Shopify Storefront compartida (suggest.json + ficha producto)."""

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
from scrapper.report_seeds import seed_match_for_med
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos
from scrapper.vtex_tienda import fases_busqueda

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PAUSA = 0.3
TIMEOUT = 40
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def cache_path(cache: Path, alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return cache / f"{safe}.json"


def session(base: str, *, verify: bool = True) -> requests.Session:
    s = requests.Session()
    s.verify = verify
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "es,es-419;q=0.9,en;q=0.7",
            "Referer": base.rstrip("/") + "/",
            "Origin": base.rstrip("/"),
        }
    )
    return s


def precio_variant(v: dict[str, Any]) -> float | None:
    lista, oferta = precios_variant(v)
    return lista or oferta


def precios_variant(v: dict[str, Any]) -> tuple[float | None, float | None]:
    """Devuelve (precio_lista, precio_oferta). Oferta solo si es menor que lista."""
    lista = None
    oferta = None
    for key in ("compare_at_price", "compare_at_price_max", "compare_at_price_min"):
        raw = v.get(key)
        if raw is None or raw == "" or raw == "0.00":
            continue
        try:
            p = float(str(raw).replace(",", ""))
        except (TypeError, ValueError):
            continue
        if p > 0:
            lista = p
            break
    for key in ("price", "price_min"):
        raw = v.get(key)
        if raw is None or raw == "" or raw == "0.00":
            continue
        try:
            p = float(str(raw).replace(",", ""))
        except (TypeError, ValueError):
            continue
        if p > 0:
            oferta = p
            break
    if lista and oferta and oferta < lista * 0.999:
        return lista, oferta
    base = lista or oferta
    return base, None


def enriquecer(s: requests.Session, base: str, cache: Path, handle: str) -> dict[str, Any] | None:
    if not handle:
        return None
    path = cache / f"p_{re.sub(r'[^a-z0-9]+', '_', handle.lower())[:80]}.json"
    if path.exists() and path.stat().st_size >= 2:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("product"):
                return data["product"]
        except Exception:
            pass
    time.sleep(PAUSA)
    try:
        r = s.get(f"{base.rstrip('/')}/products/{quote(handle)}.json", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if r.status_code != 200 or not (r.text or "").startswith("{"):
        return None
    try:
        data = r.json()
    except ValueError:
        return None
    prod = data.get("product")
    if not isinstance(prod, dict):
        return None
    cache.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return prod


def buscar_shopify(
    s: requests.Session,
    alias: str,
    *,
    base: str,
    cache: Path,
    forzar: bool,
) -> tuple[list[dict[str, Any]], str, str | None]:
    path = cache_path(cache, alias)
    if not forzar and path.exists() and path.stat().st_size >= 2:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            fecha = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            return data, fecha, None

    time.sleep(PAUSA)
    url = (
        f"{base.rstrip('/')}/search/suggest.json?q={quote(alias)}"
        f"&resources[type]=product&resources[limit]=10"
        f"&resources[options][unavailable_products]=last"
    )
    try:
        r = s.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return [], datetime.now().date().isoformat(), str(exc)
    if r.status_code in (401, 403, 451):
        return [], datetime.now().date().isoformat(), f"bloqueado HTTP {r.status_code}"
    if r.status_code == 429:
        return [], datetime.now().date().isoformat(), "HTTP 429"
    if r.status_code != 200:
        return [], datetime.now().date().isoformat(), f"HTTP {r.status_code}"
    try:
        data = r.json()
    except ValueError:
        return [], datetime.now().date().isoformat(), "respuesta no JSON"
    prods = ((data.get("resources") or {}).get("results") or {}).get("products") or []
    if not isinstance(prods, list):
        prods = []

    enriquecidos: list[dict[str, Any]] = []
    for p in prods:
        if not isinstance(p, dict):
            continue
        handle = str(p.get("handle") or "").strip()
        full = enriquecer(s, base, cache, handle) if handle else None
        enriquecidos.append(full or p)

    cache.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(enriquecidos, ensure_ascii=False), encoding="utf-8")
    return enriquecidos, datetime.now().date().isoformat(), None


def filas_de_hits(
    med: dict[str, Any],
    hits: list[dict[str, Any]],
    fecha_dato: str,
    vistos: set[tuple[str, int]],
    *,
    pais: str,
    farmacia: str,
    moneda: str,
    public_base: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for h in hits:
        nombre = str(h.get("title") or h.get("name") or "").strip()
        if not nombre:
            continue
        vendor = str(h.get("vendor") or "").strip()
        tags = h.get("tags") or []
        tag_txt = " ".join(str(t) for t in tags) if isinstance(tags, list) else str(tags)
        blob = " ".join(x for x in (nombre, vendor, tag_txt, str(h.get("body_html") or h.get("body") or "")) if x)
        seed_match = seed_match_for_med(blob, pais, med)
        if not coincide(blob, med) and not coincide(nombre, med) and not seed_match:
            continue

        variants = h.get("variants") if isinstance(h.get("variants"), list) else []
        if variants:
            v0 = variants[0] if isinstance(variants[0], dict) else {}
            precio_lista, precio_oferta = precios_variant(v0)
            disponible = bool(v0.get("available", True))
            vid = str(v0.get("id") or h.get("id") or "")
            sku = str(v0.get("sku") or h.get("handle") or vid)
        else:
            precio_lista, precio_oferta = precios_variant(h)
            disponible = bool(h.get("available", True))
            vid = str(h.get("id") or "")
            sku = str(h.get("handle") or vid)
        precio = precio_lista or precio_oferta
        if not precio or not vid:
            continue

        handle = str(h.get("handle") or "").strip()
        fuente = f"{public_base.rstrip('/')}/products/{handle}" if handle else public_base
        p_fake = {
            "nombre": nombre,
            "principios_activos": [vendor],
            "tipo_presentacion": nombre,
            "laboratorio": vendor,
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and calidad == "ok":
            calidad = "revisar"
        n_lista = int(med2["n"])
        clave = (vid, n_lista)
        if clave in vistos:
            continue
        vistos.add(clave)
        ficha = parse_ficha(nombre, med2)
        out.append(
            {
                "pais": pais,
                "farmacia": farmacia,
                "fuente_url": fuente[:500],
                "id_producto_farmacia": vid[:80],
                "sku": sku[:80],
                "n_lista": n_lista,
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": ficha.get("principio_activo"),
                "concentracion": ficha.get("concentracion"),
                "presentacion": ficha.get("presentacion"),
                "laboratorio": (vendor or ficha.get("laboratorio") or "")[:200] or None,
                "precio": precio,
                "precio_lista": precio_lista or precio,
                "precio_oferta": precio_oferta,
                "moneda": moneda,
                "disponibilidad": "Disponible" if disponible else "Agotado",
                "calidad": calidad,
                "observacion": obs,
                "fecha_publicacion": None,
                "fecha_dato": fecha_dato,
            }
        )
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
    public_base: str | None = None,
) -> list[dict[str, Any]]:
    pub = (public_base or base).rstrip("/")
    s = session(base, verify=verify)
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
                path = cache_path(cache, alias)
                if red_caida and not path.exists():
                    continue
                hits, fecha, err = buscar_shopify(
                    s, alias, base=base, cache=cache, forzar=False if red_caida else forzar
                )
                if err and not red_caida:
                    bloqueado = (
                        err.startswith("bloqueado")
                        or "timed out" in err.lower()
                        or "timeout" in err.lower()
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
                    filas_de_hits(
                        med,
                        hits,
                        fecha,
                        vistos,
                        pais=pais,
                        farmacia=farmacia,
                        moneda=moneda,
                        public_base=pub,
                    )
                )
        n_nuevas = len(filas) - n_antes
        marca = "·" if n_nuevas else " "
        print(f"  {marca} {n_nuevas:3d}  {med['nombre']}")
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
    public_base: str | None = None,
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
        public_base=public_base,
    )
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    revisar = len(filas) - ok
    print(f"Lista: {len(meds)} medicamentos")
    print(f"Coincidencias a guardar: {len(filas)}  (ok={ok}, revisar={revisar})")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    if solo_fomac or not filas:
        borrados = 0
        if not filas:
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
    return 0
