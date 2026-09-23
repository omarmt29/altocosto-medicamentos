"""Términos de búsqueda por marcas comerciales y nombres cruzados entre países.

Fase 1 (principio): aliases de lista.py + semillas Digemaps del país.
Fase 2 (marcas): guía marcas.py + nombres comerciales hallados en otros países
                 (prioriza el país con más SKUs para ese principio).
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from lista import MEDICAMENTOS
from marcas import aliases_de_marcas

ROOT = Path(__file__).resolve().parents[1]
CACHE_JSON = ROOT / "cache" / "busqueda_marcas" / "nombres_por_pais.json"

MAX_TERMS_GUIA = 6
MAX_TERMS_CRUZADOS = 6
MIN_TOKEN = 4

_STOP = {
    "acetato",
    "acido",
    "tableta",
    "tabletas",
    "capsula",
    "capsulas",
    "comprimido",
    "comprimidos",
    "solucion",
    "inyectable",
    "frasco",
    "ampolla",
    "vial",
    "mg",
    "ml",
    "gramos",
    "laboratorio",
    "generico",
    "genérico",
    "sandoz",
    "eurofarma",
    "mk",
    "la",
    "de",
    "con",
    "para",
    "x",
    "jeringa",
    "jeringas",
    "prellena",
    "prellenada",
    "precargada",
    "polvo",
    "liofilizado",
    "inyecta",
    "inyectable",
    "suspension",
    "doctor",
    "protectora",
    "accion",
    "prolongada",
    "microsuleas",
    "microsules",
    "inyectabe",
    "perfusion",
    "perfsion",
    "plumas",
    "pluma",
    "caja",
    "sobre",
    "sobres",
    "unidad",
    "unidades",
    "lote",
    "kit",
    # Colores / ruido frecuentes en títulos cruzados (no son marcas)
    "verde",
    "azul",
    "rojo",
    "negro",
    "blanco",
    "blanca",
    "rosa",
    "rosado",
    "lila",
    "gris",
    "amarillo",
    "naranja",
    "violeta",
    "dorado",
    "plateado",
    "crema",
    "forte",
    "plus",
    "maxi",
    "mini",
    "total",
    "simple",
    "original",
}


def _norm(texto: Any) -> str:
    s = unicodedata.normalize("NFKD", str(texto or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower().replace("®", " ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def _agregar(out: list[str], seen: set[str], raw: str) -> None:
    q = str(raw or "").strip()
    if not _parece_marca(q):
        return
    k = _norm(q)
    if k in seen:
        return
    seen.add(k)
    out.append(q)


def _parece_marca(token: str) -> bool:
    t = token.strip()
    if len(t) < MIN_TOKEN or len(t) > 24:
        return False
    if re.search(r"\d", t):
        return False
    k = _norm(t)
    if k in _STOP:
        return False
    letters = sum(ch.isalpha() for ch in t)
    return letters >= MIN_TOKEN


def tokens_de_nombre_comercial(nombre: str) -> list[str]:
    """Extrae 1–2 marcas buscables desde un título de producto de farmacia."""
    if not nombre:
        return []
    s = str(nombre).strip()
    head = re.split(r"\s*[\(\[\-–—|]", s, maxsplit=1)[0].strip()
    out: list[str] = []
    seen: set[str] = set()

    # Primer token alfanumérico del título (suele ser la marca).
    m = re.match(r"^([A-Za-z][A-Za-z0-9\-]{3,})", head)
    if m and _parece_marca(m.group(1)):
        _agregar(out, seen, m.group(1))

    # Marca entre paréntesis si no es solo DCI genérico.
    for inner in re.findall(r"\(([^)]+)\)", s):
        for tok in re.split(r"[\s,/]+", inner):
            tok = tok.strip(" .")
            if _parece_marca(tok):
                _agregar(out, seen, tok)

    return out[:2]


@lru_cache(maxsize=1)
def _indice_nombres_bd() -> dict[int, dict[str, list[str]]]:
    """n_lista → {pais → [nombre_comercial, …]} desde BD o caché JSON."""
    filas: list[dict[str, Any]] = []
    try:
        from scrapper.repositorio import listar_filas

        filas = listar_filas(todos=False)
    except Exception:
        filas = []

    if not filas and CACHE_JSON.exists():
        try:
            data = json.loads(CACHE_JSON.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    int(k): {p: list(v) for p, v in pv.items()}
                    for k, pv in data.items()
                    if str(k).isdigit()
                }
        except (OSError, json.JSONDecodeError, ValueError):
            pass

    idx: dict[int, dict[str, list[str]]] = {}
    for f in filas:
        try:
            n = int(f.get("n_lista") or 0)
        except (TypeError, ValueError):
            continue
        if n <= 0:
            continue
        pais = str(f.get("pais") or "").strip()
        nom = str(f.get("nombre_comercial") or "").strip()
        if not pais or not nom:
            continue
        bucket = idx.setdefault(n, {}).setdefault(pais, [])
        if nom not in bucket:
            bucket.append(nom)

    if idx and not CACHE_JSON.parent.exists():
        CACHE_JSON.parent.mkdir(parents=True, exist_ok=True)
    if idx:
        try:
            CACHE_JSON.write_text(
                json.dumps({str(k): v for k, v in idx.items()}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass
    return idx


@lru_cache(maxsize=1)
def cobertura_por_pais() -> list[tuple[str, int]]:
    """Países ordenados por cantidad de principios distintos con dato."""
    meds: dict[str, set[int]] = {}
    try:
        from scrapper.repositorio import listar_filas

        for f in listar_filas(todos=False):
            pais = str(f.get("pais") or "").strip()
            if not pais:
                continue
            try:
                n = int(f.get("n_lista") or 0)
            except (TypeError, ValueError):
                continue
            if n > 0:
                meds.setdefault(pais, set()).add(n)
    except Exception:
        pass
    return sorted(((p, len(ns)) for p, ns in meds.items()), key=lambda x: (-x[1], x[0]))


def pais_referencia_para_med(n_lista: int, excluir_pais: str | None = None) -> str | None:
    """País con más nombres comerciales para ese principio (excluye el país destino)."""
    idx = _indice_nombres_bd().get(int(n_lista), {})
    excl = _norm(excluir_pais or "")
    ranking = sorted(
        ((p, len(noms)) for p, noms in idx.items() if _norm(p) != excl and noms),
        key=lambda x: (-x[1], x[0]),
    )
    if ranking:
        return ranking[0][0]
    # Sin histórico por molécula: país global con más principios.
    for pais, _n in cobertura_por_pais():
        if _norm(pais) != excl:
            return pais
    return None


def terminos_guia_marcas(med: dict[str, Any]) -> list[str]:
    try:
        n = int(med["n"])
    except (TypeError, ValueError, KeyError):
        return []
    return aliases_de_marcas(n)[:MAX_TERMS_GUIA]


def terminos_desde_otros_paises(pais: str, med: dict[str, Any]) -> list[str]:
    try:
        n_lista = int(med["n"])
    except (TypeError, ValueError, KeyError):
        return []
    idx = _indice_nombres_bd().get(n_lista, {})
    if not idx:
        return []

    excl = _norm(pais)
    # Países fuente ordenados por cantidad de nombres para esta molécula.
    fuentes = sorted(
        ((p, noms) for p, noms in idx.items() if _norm(p) != excl and noms),
        key=lambda x: (-len(x[1]), x[0]),
    )
    if not fuentes:
        return []

    out: list[str] = []
    seen: set[str] = set()
    # Alias ya cubiertos en fase principio (no repetir).
    for a in med.get("aliases") or []:
        seen.add(_norm(a))

    for _pais_fuente, nombres in fuentes[:3]:
        for nom in nombres:
            for tok in tokens_de_nombre_comercial(nom):
                if len(out) >= MAX_TERMS_CRUZADOS:
                    return out
                _agregar(out, seen, tok)
    return out


def queries_respaldo_marcas(pais: str, med: dict[str, Any]) -> list[str]:
    """Términos fase 2: marcas guía + nombres comerciales de otros países."""
    out: list[str] = []
    seen: set[str] = set()
    for t in terminos_guia_marcas(med):
        _agregar(out, seen, t)
    for t in terminos_desde_otros_paises(pais, med):
        if len(out) >= MAX_TERMS_GUIA + MAX_TERMS_CRUZADOS:
            break
        _agregar(out, seen, t)
    return out


def combinar_fases(
    pais: str,
    med: dict[str, Any],
    queries_principio: Callable[[str, dict[str, Any]], list[str]],
) -> list[tuple[str, list[str]]]:
    """Devuelve [('principio', …), ('marcas', …)] sin duplicar términos."""
    prin = queries_principio(pais, med)
    seen = {_norm(q) for q in prin if _norm(q)}
    resp: list[str] = []
    for q in queries_respaldo_marcas(pais, med):
        k = _norm(q)
        if k and k not in seen:
            seen.add(k)
            resp.append(q)
    fases: list[tuple[str, list[str]]] = [("principio", prin)]
    if resp:
        fases.append(("marcas", resp))
    return fases


def refrescar_cache_nombres() -> int:
    """Fuerza recarga desde BD y reescribe cache/busqueda_marcas/nombres_por_pais.json."""
    _indice_nombres_bd.cache_clear()
    cobertura_por_pais.cache_clear()
    return len(_indice_nombres_bd())
