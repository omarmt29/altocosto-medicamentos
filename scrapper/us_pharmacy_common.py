"""Utilidades compartidas por las farmacias online de Estados Unidos."""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urljoin

import requests

from scrapper.ficha import parse_ficha
from scrapper.matching import clasificar, coincide
from scrapper.report_seeds import seed_match_for_med
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos

PAIS = "Estados Unidos"
MONEDA = "USD"
TIMEOUT = 60
PAUSA = 0.35
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def session(*, accept: str = "text/html,application/xhtml+xml") -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return s


def normalizar_slug(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-")


def terminos_busqueda(med: dict[str, Any], *, limite: int = 4) -> list[str]:
    """Prioriza alias en ingles/marca y evita consultas duplicadas."""
    candidatos = [*(med.get("aliases") or []), med.get("nombre")]
    unicos: list[str] = []
    vistos: set[str] = set()
    for raw in candidatos:
        term = str(raw or "").strip()
        key = normalizar_slug(term)
        if len(key) < 3 or key in vistos:
            continue
        vistos.add(key)
        unicos.append(term)
    # Los alias ASCII suelen ser el INN en ingles o una marca estadounidense.
    unicos.sort(key=lambda x: (any(ord(c) > 127 for c in x), len(x)))
    return unicos[:limite]


def cache_texto(
    s: requests.Session,
    url: str,
    cache: Path,
    *,
    forzar: bool,
    minimo: int = 200,
) -> str:
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    path = cache / f"{key}.html"
    if not forzar and path.exists() and path.stat().st_size >= minimo:
        return path.read_text(encoding="utf-8")
    time.sleep(PAUSA)
    r = s.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    texto = r.text
    if len(texto) < minimo:
        raise RuntimeError(f"respuesta demasiado corta ({len(texto)} bytes): {url}")
    cache.mkdir(parents=True, exist_ok=True)
    path.write_text(texto, encoding="utf-8")
    return texto


def next_flight_text(documento: str) -> str:
    """Decodifica los fragmentos de React/Next ``self.__next_f.push``."""
    partes: list[str] = []
    patron = re.compile(r"self\.__next_f\.push\((\[.*?\])\)</script>", re.S)
    for match in patron.finditer(documento):
        try:
            payload = json.loads(html.unescape(match.group(1)))
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(payload, list) and len(payload) > 1 and isinstance(payload[1], str):
            partes.append(payload[1])
    return "\n".join(partes)


def json_despues_de(texto: str, marcador: str) -> Any | None:
    pos = texto.find(marcador)
    if pos < 0:
        return None
    inicio = pos + len(marcador)
    try:
        valor, _ = json.JSONDecoder().raw_decode(texto[inicio:])
    except json.JSONDecodeError:
        return None
    return valor


def objetos_json(texto: str, inicio_objeto: str) -> list[dict[str, Any]]:
    """Extrae objetos JSON planos identificados por su prefijo."""
    salida: list[dict[str, Any]] = []
    pos = 0
    decoder = json.JSONDecoder()
    while True:
        pos = texto.find(inicio_objeto, pos)
        if pos < 0:
            break
        try:
            valor, consumidos = decoder.raw_decode(texto[pos:])
        except json.JSONDecodeError:
            pos += len(inicio_objeto)
            continue
        if isinstance(valor, dict):
            salida.append(valor)
        pos += max(consumidos, 1)
    return salida


def url_absoluta(base: str, raw: Any) -> str:
    return urljoin(base.rstrip("/") + "/", str(raw or "").lstrip("/"))


def construir_fila(
    *,
    farmacia: str,
    med: dict[str, Any],
    producto: dict[str, Any],
    fecha_dato: str,
) -> dict[str, Any] | None:
    nombre = str(producto.get("nombre") or "").strip()
    sku = str(producto.get("sku") or producto.get("id") or "").strip()
    try:
        precio = float(producto.get("precio") or 0)
    except (TypeError, ValueError):
        precio = 0
    if not nombre or not sku or precio <= 0:
        return None

    blob = " ".join(
        str(producto.get(k) or "")
        for k in ("nombre", "principio_activo", "concentracion", "presentacion", "laboratorio")
    )
    seed = seed_match_for_med(blob, PAIS, med)
    if not coincide(blob, med) and not seed:
        return None
    p_fake = {
        "nombre": nombre,
        "principios_activos": [producto.get("principio_activo"), nombre],
        "tipo_presentacion": producto.get("presentacion"),
        "laboratorio": producto.get("laboratorio"),
    }
    med2, calidad, obs = clasificar(med, p_fake)
    if seed and calidad == "ok":
        calidad = "revisar"
    if producto.get("forzar_revision") and calidad == "ok":
        calidad = "revisar"
    nota = str(producto.get("observacion") or "").strip()
    obs = "; ".join(x for x in (obs, nota) if x) or None
    ficha = parse_ficha(nombre, med2)
    return {
        "pais": PAIS,
        "farmacia": farmacia,
        "fuente_url": str(producto.get("url") or "")[:500],
        "id_producto_farmacia": sku[:80],
        "sku": sku[:80],
        "n_lista": int(med2["n"]),
        "medicamento_lista": str(med2["nombre"]),
        "programa": str(med2["programa"]),
        "nombre_comercial": nombre[:500],
        "principio_activo": (
            ficha.get("principio_activo")
            or str(producto.get("principio_activo") or med2["nombre"])
        )[:500],
        "concentracion": ficha.get("concentracion") or producto.get("concentracion"),
        "presentacion": ficha.get("presentacion") or producto.get("presentacion"),
        "laboratorio": ficha.get("laboratorio") or producto.get("laboratorio"),
        "precio": round(precio, 4),
        "precio_lista": producto.get("precio_lista") or round(precio, 4),
        "precio_oferta": producto.get("precio_oferta"),
        "moneda": MONEDA,
        "disponibilidad": producto.get("disponibilidad") or "Disponible",
        "calidad": calidad,
        "observacion": obs,
        "fecha_publicacion": producto.get("fecha_publicacion"),
        "fecha_dato": fecha_dato,
    }


def recolectar_productos(
    *,
    farmacia: str,
    meds: Iterable[dict[str, Any]],
    proveedor: Callable[[dict[str, Any]], Iterable[dict[str, Any]]],
) -> list[dict[str, Any]]:
    fecha = datetime.now().date().isoformat()
    filas: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    for med in meds:
        n_antes = len(filas)
        for producto in proveedor(med):
            fila = construir_fila(
                farmacia=farmacia,
                med=med,
                producto=producto,
                fecha_dato=fecha,
            )
            if not fila:
                continue
            clave = (fila["id_producto_farmacia"], fila["n_lista"])
            if clave in vistos:
                continue
            vistos.add(clave)
            filas.append(fila)
        print(f"  {'·' if len(filas) > n_antes else ' '} {len(filas) - n_antes:3d}  {med['nombre']}")
    return filas


def persistir(*, farmacia: str, filas: list[dict[str, Any]]) -> int:
    asegurar_tabla()
    res = guardar_filas(filas)
    borrados = 0
    # Nunca borrar la ultima foto buena por una respuesta vacia/bloqueada.
    if filas:
        borrados = purgar_obsoletos(
            PAIS,
            farmacia,
            [(f["id_producto_farmacia"], f["n_lista"]) for f in filas],
        )
    else:
        print("  aviso: 0 coincidencias; se conservan las filas existentes")
    print(
        f"MERGE {res['upserts']} filas · obsoletos: {borrados} · "
        f"{PAIS} {farmacia}: {contar(PAIS, farmacia)} · total tabla: {contar()}"
    )
    return 0
