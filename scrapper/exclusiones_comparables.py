"""Exclusiones manuales de comparaciones cross-país.

Editar ``exclusiones_comparables.json`` para sacar filas/claves/principios
de precios compartidos, gráficos y temas cuando el match automático no
es consistente (precio absurdo, unidad dudosa, etc.).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_JSON = Path(__file__).with_name("exclusiones_comparables.json")


def _norm(s: Any) -> str:
    return " ".join(str(s or "").strip().lower().split())


@lru_cache(maxsize=4)
def _cargar(mtime_ns: int) -> dict[str, Any]:
    if not _JSON.is_file():
        return {"version": 1, "reglas": []}
    try:
        raw = json.loads(_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "reglas": []}
    if not isinstance(raw, dict):
        return {"version": 1, "reglas": []}
    reglas = raw.get("reglas") or []
    if not isinstance(reglas, list):
        reglas = []
    return {"version": raw.get("version", 1), "reglas": reglas, "nota": raw.get("nota")}


def recargar() -> None:
    """Invalida caché (útil tras editar el JSON en caliente)."""
    _cargar.cache_clear()


def reglas_activas() -> list[dict[str, Any]]:
    try:
        mtime = _JSON.stat().st_mtime_ns
    except OSError:
        mtime = 0
    data = _cargar(mtime)
    out = []
    for r in data.get("reglas") or []:
        if not isinstance(r, dict):
            continue
        if r.get("activo", True) is False:
            continue
        out.append(r)
    return out


def _match_regex(pattern: str | None, text: Any) -> bool:
    if not pattern:
        return True
    try:
        return re.search(str(pattern), str(text or "")) is not None
    except re.error:
        return False


def _n_lista_fila(fila: dict[str, Any]) -> int | None:
    try:
        return int(fila.get("n_lista"))
    except (TypeError, ValueError):
        return None


def clave_excluida(clave: str | None) -> bool:
    """True si la clave de presentación está bloqueada por completo."""
    if not clave:
        return False
    c = str(clave)
    for r in reglas_activas():
        ek = r.get("excluir_clave")
        if ek and str(ek) == c:
            return True
        pref = r.get("excluir_clave_prefijo")
        if pref and c.startswith(str(pref)):
            return True
        ep = r.get("excluir_principio")
        if ep is not None:
            try:
                n = int(str(c).split("|", 1)[0])
                if n == int(ep):
                    return True
            except (TypeError, ValueError):
                pass
    return False


def fila_excluida_de_comparacion(fila: dict[str, Any], *, clave: str | None = None) -> bool:
    """True si esta fila no debe entrar a un grupo comparable."""
    if clave_excluida(clave):
        return True

    n = _n_lista_fila(fila)
    pais = str(fila.get("pais") or "")
    nombre = str(fila.get("nombre_comercial") or "")
    med = str(fila.get("medicamento_lista") or "")
    farm = str(fila.get("farmacia") or "")

    for r in reglas_activas():
        # Reglas solo de clave/principio ya cubiertas arriba; aquí filas.
        if r.get("excluir_clave") or r.get("excluir_clave_prefijo") or r.get("excluir_principio") is not None:
            # Si la regla es puramente de clave/principio, no aplica filtro de fila
            # salvo que también traiga campos de fila (entonces AND con la clave).
            solo_clave = not any(
                r.get(k)
                for k in (
                    "n_lista",
                    "pais",
                    "farmacia_regex",
                    "nombre_comercial_regex",
                    "medicamento_lista_regex",
                )
            )
            if solo_clave:
                continue

        if "n_lista" in r and r.get("n_lista") is not None:
            try:
                if n is None or int(r["n_lista"]) != n:
                    continue
            except (TypeError, ValueError):
                continue

        if r.get("pais"):
            if _norm(r["pais"]) != _norm(pais):
                continue

        if not _match_regex(r.get("nombre_comercial_regex"), nombre):
            continue
        if not _match_regex(r.get("medicamento_lista_regex"), med):
            continue
        if not _match_regex(r.get("farmacia_regex"), farm):
            continue

        # Si llegó aquí, la regla tenía al menos un criterio de fila y todos matchearon.
        if any(
            r.get(k)
            for k in (
                "n_lista",
                "pais",
                "farmacia_regex",
                "nombre_comercial_regex",
                "medicamento_lista_regex",
            )
        ):
            return True

    return False


def motivo_exclusion_fila(fila: dict[str, Any], *, clave: str | None = None) -> str | None:
    """Devuelve el motivo de la primera regla que excluye la fila (debug)."""
    if clave and clave_excluida(clave):
        for r in reglas_activas():
            ek = r.get("excluir_clave")
            pref = r.get("excluir_clave_prefijo")
            ep = r.get("excluir_principio")
            c = str(clave)
            if ek and str(ek) == c:
                return str(r.get("motivo") or r.get("id") or "clave excluida")
            if pref and c.startswith(str(pref)):
                return str(r.get("motivo") or r.get("id") or "clave excluida")
            if ep is not None:
                try:
                    if int(str(c).split("|", 1)[0]) == int(ep):
                        return str(r.get("motivo") or r.get("id") or "principio excluido")
                except (TypeError, ValueError):
                    pass

    n = _n_lista_fila(fila)
    pais = str(fila.get("pais") or "")
    nombre = str(fila.get("nombre_comercial") or "")
    med = str(fila.get("medicamento_lista") or "")
    farm = str(fila.get("farmacia") or "")

    for r in reglas_activas():
        if "n_lista" in r and r.get("n_lista") is not None:
            try:
                if n is None or int(r["n_lista"]) != n:
                    continue
            except (TypeError, ValueError):
                continue
        if r.get("pais") and _norm(r["pais"]) != _norm(pais):
            continue
        if not _match_regex(r.get("nombre_comercial_regex"), nombre):
            continue
        if not _match_regex(r.get("medicamento_lista_regex"), med):
            continue
        if not _match_regex(r.get("farmacia_regex"), farm):
            continue
        if any(
            r.get(k)
            for k in (
                "n_lista",
                "pais",
                "farmacia_regex",
                "nombre_comercial_regex",
                "medicamento_lista_regex",
            )
        ):
            return str(r.get("motivo") or r.get("id") or "fila excluida")
    return None
