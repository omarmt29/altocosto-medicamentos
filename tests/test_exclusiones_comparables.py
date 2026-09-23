"""Pruebas de exclusiones manuales de comparación."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scrapper.exclusiones_comparables import (  # noqa: E402
    fila_excluida_de_comparacion,
    recargar,
)


def test_osimert_rd_excluido():
    recargar()
    bad = {
        "n_lista": 56,
        "pais": "República Dominicana",
        "nombre_comercial": "Osimert (Osimertinib) Frasco",
        "farmacia": "Qualipharma",
        "precio_usd": 259.46,
    }
    ok_tagrisso = {
        "n_lista": 56,
        "pais": "República Dominicana",
        "nombre_comercial": "TAGRISSO 80 MG 30 COMPRIMIDOS RECUBIERTOS",
        "farmacia": "Qualipharma",
        "precio_usd": 9340.0,
    }
    co = {
        "n_lista": 56,
        "pais": "Colombia",
        "nombre_comercial": "Tagrisso Tabletas 80mg X 30",
        "farmacia": "Locatel",
        "precio_usd": 8859.0,
    }
    assert fila_excluida_de_comparacion(bad) is True
    assert fila_excluida_de_comparacion(ok_tagrisso) is False
    assert fila_excluida_de_comparacion(co) is False


if __name__ == "__main__":
    test_osimert_rd_excluido()
    print("ok")
