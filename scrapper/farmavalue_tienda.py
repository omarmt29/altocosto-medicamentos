"""FarmaValue multi-país (API 3c.group por host de país).

RD ya usa scrapper/rd_farmavalue.py (fd-app). Este módulo parametriza
host/país/moneda/URL para CR/GT/SV y otros.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from lista import MEDICAMENTOS
from scrapper.matching import (
    blob_producto,
    clasificar,
    dosaje_txt,
    medicamentos_que_pegan,
    principios_txt,
)
from scrapper.ficha import parse_ficha
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos

_AES_PARTES = ("128", "48", "99", "402")


def slug_farmavalue(nombre: Any) -> str:
    s = str(nombre or "")
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.replace("+", " ").replace("µ", "u").replace("μ", "u")
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-+", "-", s)
    return s.lower().strip("-")


def _bearer() -> str:
    token = (os.getenv("FARMAVALUE_BEARER") or "").strip()
    if token:
        return token
    return (
        "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo0Njc1Mzd9."
        "n_crdmiAYiG3qcwGrGBwv2gYIxeOQh3WwfS1IIeaDvs"
    )


def fecha_clave(ahora: datetime | None = None) -> str:
    d = ahora or datetime.now()
    return f"{d.day:02d}/{d.month:02d}/{str(d.year)[-2:]}"


def aes_key_desde_fecha(fecha_slash: str) -> bytes:
    dd, mm, yy = fecha_slash.split("/")
    a = _AES_PARTES
    key_str = a[0] + dd + a[1] + yy + a[2] + mm + a[3]
    return bytes(ord(ch) for ch in key_str)


def desencriptar_precio(cipher_b64: Any, key: bytes) -> float | None:
    if cipher_b64 is None or cipher_b64 == "":
        return None
    if isinstance(cipher_b64, (int, float)):
        return float(cipher_b64) if float(cipher_b64) > 0 else None
    texto = str(cipher_b64).strip()
    try:
        if len(texto) < 16 and "/" not in texto and "+" not in texto:
            n = float(texto)
            return n if n > 0 else None
    except ValueError:
        pass
    try:
        from Crypto.Cipher import AES
    except ImportError as exc:
        raise RuntimeError("Falta pycryptodome (pip install pycryptodome)") from exc
    try:
        raw = base64.b64decode(texto)
        if len(raw) < 16:
            return None
        iv, ct = raw[:16], raw[16:]
        pt_bytes = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
        pt_str = pt_bytes.decode("latin-1").rstrip(
            "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\t\r\n "
        )
        n = float(pt_str)
        return n if n > 0 else None
    except Exception:
        return None


def bajar_catalogo(api: str, cache_path: Path, *, forzar: bool = False) -> list[dict[str, Any]]:
    if cache_path.exists() and cache_path.stat().st_size > 1000 and not forzar:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        print(f"Catálogo en caché: {len(data)} productos")
        return data
    print(f"Descargando catálogo FarmaValue ({api}) …")
    r = requests.get(
        api,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Authorization": f"Bearer {_bearer()}",
            "Accept": "application/json",
        },
        timeout=(15, 300),
        verify=False,
    )
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Respuesta inesperada: {type(data)}")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"Catálogo vivo: {len(data)} productos")
    return data


def url_producto(url_base: str, pid: Any, nombre: Any) -> str:
    slug = slug_farmavalue(nombre)
    base = url_base.rstrip("/")
    if slug:
        return f"{base}/{pid}-{slug}"
    return f"{base}/{pid}"


def filas_para_db(
    catalogo: list[dict[str, Any]],
    *,
    pais: str,
    farmacia: str,
    moneda: str,
    url_base: str,
) -> list[dict[str, Any]]:
    key = aes_key_desde_fecha(fecha_clave())
    fecha_dato = datetime.now().date().isoformat()
    out: list[dict[str, Any]] = []
    vistos: set[tuple[Any, int]] = set()

    for i, p in enumerate(catalogo, start=1):
        if i % 2000 == 0:
            print(f"  cruzando catálogo {i}/{len(catalogo)}")
        gondola = desencriptar_precio(p.get("precio"), key)
        marcado = desencriptar_precio(p.get("precio_marcado"), key)
        precio_lista: float | None = None
        precio_oferta: float | None = None
        if marcado and marcado > 0 and gondola and gondola > 0 and gondola < marcado * 0.999:
            precio_lista = float(marcado)
            precio_oferta = float(gondola)
            precio = precio_lista
        elif marcado and marcado > 0:
            precio_lista = float(marcado)
            precio = precio_lista
        elif gondola and gondola > 0:
            precio_lista = float(gondola)
            precio = precio_lista
        else:
            continue
        texto = blob_producto(p)
        hits = medicamentos_que_pegan(texto)
        if not hits:
            continue
        for med0 in hits:
            med, calidad, obs = clasificar(med0, p)
            n_lista = int(med["n"])
            clave = (p.get("id"), n_lista)
            if clave in vistos:
                continue
            vistos.add(clave)
            ficha = parse_ficha(p.get("nombre") or "", med)
            pa = ficha["principio_activo"] or principios_txt(p)
            conc = ficha["concentracion"] or dosaje_txt(p)
            pres = ficha["presentacion"] or p.get("tipo_presentacion")
            lab = p.get("laboratorio") or ficha["laboratorio"]
            if precio_oferta is not None and precio_lista is not None:
                pct = round((1 - precio_oferta / precio_lista) * 100, 1)
                nota_desc = (
                    f"Oferta FarmaValue {pct}% "
                    f"(lista {precio_lista:g} → {precio_oferta:g} {moneda})"
                )
                obs = f"{obs}; {nota_desc}" if obs else nota_desc
            out.append(
                {
                    "pais": pais,
                    "farmacia": farmacia,
                    "fuente_url": url_producto(url_base, p.get("id"), p.get("nombre"))[:500],
                    "id_producto_farmacia": str(p.get("id") or ""),
                    "sku": str(p.get("barcode") or p.get("id") or "")[:80],
                    "n_lista": n_lista,
                    "medicamento_lista": str(med["nombre"]),
                    "programa": str(med["programa"]),
                    "nombre_comercial": (p.get("nombre") or "")[:500],
                    "principio_activo": (pa or None) and str(pa)[:500],
                    "concentracion": (conc or None) and str(conc)[:300],
                    "presentacion": (pres or None) and str(pres)[:120],
                    "laboratorio": lab,
                    "precio": precio,
                    "precio_lista": precio_lista,
                    "precio_oferta": precio_oferta,
                    "moneda": moneda,
                    "disponibilidad": (
                        "Agotado"
                        if p.get("agotado") in (1, "1", True, "true", "True")
                        else ("Disponible" if precio else "Consultar")
                    ),
                    "calidad": calidad,
                    "observacion": obs,
                    "fecha_publicacion": None,
                    "fecha_dato": fecha_dato,
                }
            )
    return out


def _prefiltrar_fomac(catalogo: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claves: list[str] = []
    for med in MEDICAMENTOS:
        if "FOMAC" not in str(med["programa"]):
            continue
        for alias in med["aliases"]:
            a = unicodedata.normalize("NFKD", str(alias)).encode("ascii", "ignore").decode("ascii").lower()
            a = re.sub(r"[^a-z0-9]+", " ", a).strip()
            if len(a) >= 4:
                claves.append(a)
    out: list[dict[str, Any]] = []
    for p in catalogo:
        blob = blob_producto(p).lower()
        if any(k in blob for k in claves):
            out.append(p)
    return out


def ejecutar(
    *,
    titulo: str,
    pais: str,
    farmacia: str,
    moneda: str,
    api: str,
    url_base: str,
    cache_path: Path,
    argv: list[str] | None = None,
) -> int:
    argv = argv or sys.argv
    forzar = "--fresh" in argv
    solo_fomac = "--fomac" in argv
    print("=" * 64)
    print(titulo)
    if solo_fomac:
        print(" Solo FOMAC (prefiltro de catálogo)")
    print("=" * 64)
    catalogo = bajar_catalogo(api, cache_path, forzar=forzar)
    if solo_fomac:
        n0 = len(catalogo)
        catalogo = _prefiltrar_fomac(catalogo)
        print(f"Catálogo FOMAC: {len(catalogo)} / {n0}")
    filas = filas_para_db(
        catalogo, pais=pais, farmacia=farmacia, moneda=moneda, url_base=url_base
    )
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    revisar = len(filas) - ok
    print(f"Lista DAMAC/FOMAC: {len(MEDICAMENTOS)} medicamentos")
    print(f"Coincidencias a guardar: {len(filas)}  (ok={ok}, revisar={revisar})")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    if solo_fomac or not filas:
        borrados = 0
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
