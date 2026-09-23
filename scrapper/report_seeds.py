"""Semillas dirigidas desde docs/faltantes_digemaps_fuentes.csv."""

from __future__ import annotations

import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from lista import MEDICAMENTOS

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "faltantes_digemaps_fuentes.csv"


def _norm(texto: Any) -> str:
    s = unicodedata.normalize("NFKD", str(texto or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower().replace("®", " ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


@lru_cache(maxsize=1)
def _rows() -> list[dict[str, str]]:
    if not REPORT_PATH.exists():
        return []
    meds_por_nombre = {_norm(m["nombre"]): m for m in MEDICAMENTOS}
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    with REPORT_PATH.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            pais = (row.get("pais_faltante") or "").strip()
            dci_lista = (row.get("dci_lista") or "").strip()
            med = meds_por_nombre.get(_norm(dci_lista))
            if not pais or not med:
                continue
            csv_marca = (row.get("csv_marca") or "").strip()
            csv_dci = (row.get("csv_dci") or "").strip()
            key = (pais, dci_lista, csv_marca, csv_dci)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "pais": pais,
                    "dci_lista": dci_lista,
                    "csv_marca": csv_marca,
                    "csv_dci": csv_dci,
                    "n_lista": str(med["n"]),
                    "med_nombre": str(med["nombre"]),
                }
            )
    return out


def seeds_for_country(pais: str) -> list[dict[str, str]]:
    return [r for r in _rows() if r["pais"] == pais]


def extra_terms_for_med(pais: str, med: dict[str, Any]) -> list[str]:
    n_lista = str(med["n"])
    out: list[str] = []
    seen: set[str] = set()
    for row in seeds_for_country(pais):
        if row["n_lista"] != n_lista:
            continue
        for raw in (row.get("csv_marca"), row.get("csv_dci"), row.get("dci_lista")):
            t = _norm(raw)
            if len(t) < 4 or t in seen:
                continue
            seen.add(t)
            out.append(str(raw).strip())
    return out


def seed_match_for_med(texto: str, pais: str, med: dict[str, Any]) -> str | None:
    blob = _norm(texto)
    n_lista = str(med["n"])
    for row in seeds_for_country(pais):
        if row["n_lista"] != n_lista:
            continue
        for raw in (row.get("csv_marca"), row.get("csv_dci"), row.get("dci_lista")):
            t = _norm(raw)
            if len(t) >= 4 and re.search(rf"(^| ){re.escape(t)}( |$)", blob):
                return str(raw).strip()
    return None


def meds_por_reporte(texto: str, pais: str) -> list[dict[str, Any]]:
    blob = _norm(texto)
    meds_por_n = {int(m["n"]): m for m in MEDICAMENTOS}
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for row in seeds_for_country(pais):
        try:
            n_lista = int(row["n_lista"])
        except Exception:
            continue
        if n_lista in seen:
            continue
        for raw in (row.get("csv_marca"), row.get("csv_dci"), row.get("dci_lista")):
            t = _norm(raw)
            if len(t) >= 4 and re.search(rf"(^| ){re.escape(t)}( |$)", blob):
                med = meds_por_n.get(n_lista)
                if med:
                    seen.add(n_lista)
                    out.append(med)
                break
    return out
