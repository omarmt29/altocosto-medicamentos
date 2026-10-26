"""El precio guardado de FarmaValue es el de la ficha, no el neto."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scrapper.farmavalue_precios import resolver_precios_farmavalue  # noqa: E402


def test_letrovitae_chile_separa_lista_e_iva_del_total() -> None:
    # Precio anterior 55.810; el neto 46.899,16 es ese monto sin IVA 19%.
    # dcto 23.327,73 deja el Precio Final en 28.050.
    lista, oferta = resolver_precios_farmavalue(46899.16, 55810, 23327.73, 0.19)
    assert lista == 55810
    assert oferta == 28050


def test_el_neto_sin_descuento_no_se_guarda_como_oferta() -> None:
    lista, oferta = resolver_precios_farmavalue(46899.16, 55810, 0, 0.19)
    assert lista == 55810
    assert oferta is None


def test_descuento_negativo_no_inventa_oferta() -> None:
    lista, oferta = resolver_precios_farmavalue(57478.99, 68400, -319.33, 0.19)
    assert lista == 68400
    assert oferta is None


def test_republica_dominicana_guarda_el_total_como_oferta() -> None:
    # Precio base 10.790, descuento 2.158, ITBIS 0 → total 8.632.
    lista, oferta = resolver_precios_farmavalue(10790, 0, 2158, 0)
    assert lista == 10790
    assert oferta == 8632


def test_costa_rica_sin_descuento_mantiene_el_precio_base() -> None:
    # El IVA va en otra línea y no es un descuento.
    lista, oferta = resolver_precios_farmavalue(14026.55, 0, 0, 0.13)
    assert lista == 14026.55
    assert oferta is None


def test_sin_precio_no_arma_fila() -> None:
    assert resolver_precios_farmavalue(None, 0, 100, 0.19) is None
