"""Pruebas de equivalencia farmacológica."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scrapper.equivalencia import comparar, perfil_desde_fila  # noqa: E402


def _fila(nombre: str, **kw) -> dict:
    base = {
        "n_lista": 47,
        "medicamento_lista": "Letrozol",
        "nombre_comercial": nombre,
        "tipo_presentacion": "Comprimidos",
        "cantidad_concentracion": "2.5",
        "unidad_concentracion": "mg",
        "cantidad_presentacion": "30",
        "alcance_presentacion": "lote",
        "calidad": "ok",
    }
    base.update(kw)
    return base


def test_letrozol_misma_presentacion_generico():
    a = _fila("Femara 2,5mg 30 Comprimidos Revestidos")
    b = _fila("Letrozol (B) 2.5mg 30 Comprimidos Recubiertos", laboratorio="Mintlab")
    r = comparar(a, b)
    assert r.same_medicine is True
    assert r.same_presentation is True
    assert r.same_product is False
    assert r.match_level == "SAME_MEDICINE"
    assert r.therapeutic_equivalent is False


def test_letrozol_distinta_cantidad():
    a = _fila("Letrozol 2,5 mg x 30")
    b = _fila("Letrozol 2,5 mg x 60", cantidad_presentacion="60")
    r = comparar(a, b)
    assert r.same_medicine is True
    assert r.same_presentation is False
    assert r.match_level == "SAME_MEDICINE"


def test_dosis_distinta_no_match():
    a = _fila("Letrozol 2,5 mg x 30")
    b = _fila("Letrozol 5 mg x 30", cantidad_concentracion="5")
    r = comparar(a, b)
    assert r.same_medicine is False
    assert r.match_level == "NO_MATCH"


def test_info_insuficiente():
    a = _fila("Producto sin datos", cantidad_concentracion=None, unidad_concentracion=None, cantidad_presentacion=None)
    b = _fila("Otro sin datos", cantidad_concentracion=None, unidad_concentracion=None, cantidad_presentacion=None)
    r = comparar(a, b)
    assert r.review_required is True
    assert r.match_level == "REVIEW_REQUIRED"
