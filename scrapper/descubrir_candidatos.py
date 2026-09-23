"""
Escanea cachés de farmacias buscando productos de alto costo no presentes en lista.py.

Uso:
    python scrapper/descubrir_candidatos.py
    python scrapper/descubrir_candidatos.py --pais Honduras
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.matching import coincide, medicamentos_que_pegan  # noqa: E402

CACHE_ROOT = ROOT / "cache" / "farmacias"
TARGET_PAISES = {
    "Guatemala",
    "Nicaragua",
    "Costa Rica",
    "El Salvador",
    "Perú",
    "Peru",
    "Colombia",
    "Honduras",
}

ALTO_COSTO = re.compile(
    r"\b("
    r"mab|nib|mib|lib|zumab|tuzumab|"
    r"trastuzumab|bevacizumab|rituximab|infliximab|adalimumab|"
    r"pembrolizumab|nivolumab|atezolizumab|daratumumab|"
    r"imatinib|dasatinib|nilotinib|bortezomib|lenalidomida|"
    r"interferon|inmunoglobulina|filgrastim|pegfilgrastim|"
    r"epclusa|sofosbuvir|velpatasvir|"
    r"biosimilar|oncol|quimioterap|inmunosupresor"
    r")\b",
    re.I,
)


def norm(s: str) -> str:
    t = unicodedata.normalize("NFKD", s)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t.lower()).split())


def nombre_producto(prod: dict) -> str:
    for k in (
        "productName",
        "name",
        "nombre",
        "title",
        "displayName",
        "nameComplete",
    ):
        v = prod.get(k)
        if v:
            return str(v).strip()
    items = prod.get("items")
    if isinstance(items, list) and items:
        return nombre_producto(items[0])
    return ""


def iter_productos(data) -> list[dict]:
    if isinstance(data, list):
        if not data:
            return []
        if isinstance(data[0], dict) and (
            "productName" in data[0] or "name" in data[0] or "items" in data[0]
        ):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data[0], str):
            return []
    if isinstance(data, dict):
        for k in ("products", "results", "items", "data"):
            v = data.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def pais_de_cache(path: Path) -> str | None:
    name = path.parts[-2] if len(path.parts) >= 2 else ""
    mapping = {
        "siman_gt": "Guatemala",
        "batres_gt": "Guatemala",
        "galeno_gt": "Guatemala",
        "siman_ni": "Nicaragua",
        "kielsa_ni": "Nicaragua",
        "fahorro_ni": "Nicaragua",
        "siman_cr": "Costa Rica",
        "kolbi_cr": "Costa Rica",
        "fischel_cr": "Costa Rica",
        "siman_sv": "El Salvador",
        "inkafarma_pe": "Perú",
        "boticasperu_pe": "Perú",
        "cruzverde_co": "Colombia",
        "larebaja_co": "Colombia",
        "cafam_co": "Colombia",
        "locatel_co": "Colombia",
        "farmatodo_co": "Colombia",
        "carulla_co": "Colombia",
        "siman_hn": "Honduras",
        "kielsa_hn": "Honduras",
        "fahorro_hn": "Honduras",
        "mifarmacia_hn": "Honduras",
    }
    return mapping.get(name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pais", default="")
    args = ap.parse_args()
    filtro = args.pais.strip()
    vistos: set[tuple[str, str]] = set()
    candidatos: list[tuple[str, str, str]] = []
    for path in sorted(CACHE_ROOT.glob("*/*.json")):
        pais = pais_de_cache(path)
        if not pais:
            continue
        if filtro and norm(pais) != norm(filtro):
            continue
        if pais not in TARGET_PAISES:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for prod in iter_productos(data):
            nombre = nombre_producto(prod)
            if len(nombre) < 6:
                continue
            blob = nombre
            if not ALTO_COSTO.search(blob):
                continue
            if medicamentos_que_pegan(blob):
                continue
            key = (pais, norm(nombre))
            if key in vistos:
                continue
            vistos.add(key)
            candidatos.append((pais, nombre, path.parts[-2]))
    candidatos.sort()
    print(f"Candidatos alto costo fuera de lista ({len(candidatos)}):")
    for pais, nombre, cache in candidatos[:80]:
        print(f"  [{pais}] {nombre}  ({cache})")
    if len(candidatos) > 80:
        print(f"  ... +{len(candidatos)-80} más")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
