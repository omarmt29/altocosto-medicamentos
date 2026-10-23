from __future__ import annotations

import json

from scrapper.us_healthwarehouse import parsear_busqueda
from scrapper.us_honeybee import parsear_producto, urls_sitemap
from scrapper.us_pharmacy_common import next_flight_text


def _flight(payload: str) -> str:
    return f'<script>self.__next_f.push({json.dumps([1, payload])})</script>'


def test_next_flight_decodifica_payload() -> None:
    assert next_flight_text(_flight('1:{"ok":true}\n')) == '1:{"ok":true}\n'


def test_healthwarehouse_extrae_solo_productos_de_farmacia() -> None:
    productos = [
        {
            "__typename": "Product",
            "defaultQty": None,
            "id": 5993,
            "imageUrl": "x",
            "inStock": True,
            "isActive": True,
            "minPrice": 2.55,
            "name": "Abiraterone 250mg Tablet",
            "pharmacy": True,
            "sku": "*ABIRAT25030",
            "specialOtc": False,
            "taxClassId": None,
            "thumbnailUrl": "x",
            "url": "abiraterone-250mg-tablet",
        },
        {
            "__typename": "Product",
            "id": 1,
            "inStock": True,
            "isActive": True,
            "minPrice": 10,
            "name": "No farmacia",
            "pharmacy": False,
            "sku": "NO",
            "url": "no",
        },
    ]
    doc = _flight("1:" + "".join(json.dumps(p, separators=(",", ":")) for p in productos))
    rows = parsear_busqueda(doc)
    assert len(rows) == 1
    assert rows[0]["sku"] == "*ABIRAT25030"
    assert rows[0]["precio"] == 2.55
    assert rows[0]["url"].endswith("/abiraterone-250mg-tablet")


def test_honeybee_extrae_variantes_con_precio() -> None:
    producto = {
        "id": 579,
        "product_name": "Casodex",
        "full_name": "Bicalutamide (Casodex)",
        "generic_product": {"generic_name": "Bicalutamide"},
        "product_variants": [
            {
                "id": 30107,
                "details_page_url": "/drugs/details/casodex?variant=30107",
                "price": "24.0",
                "manufacturer": {"name": "Manufacturer Varies"},
                "in_stock": 1,
                "package_size": 30,
                "unit_abbr": "ct",
                "strength": {
                    "id": 109,
                    "name": "50 mg",
                    "formulation": {"id": 51, "name": "Tablet"},
                },
            },
            {"id": 30108, "price": None},
        ],
    }
    payload = '1:{"productData":{"product":' + json.dumps(producto, separators=(",", ":")) + "}}"
    rows = parsear_producto(_flight(payload), "https://honeybeehealth.com/drugs/casodex")
    assert len(rows) == 1
    assert rows[0]["precio"] == "24.0"
    assert rows[0]["concentracion"] == "50 mg"
    assert rows[0]["presentacion"] == "Tablet x 30 ct"


def test_honeybee_sitemap_solo_lista_medicamentos() -> None:
    xml = """<urlset>
      <url><loc>https://honeybeehealth.com/drugs/casodex</loc></url>
      <url><loc>https://example.com/drugs/falso</loc></url>
    </urlset>"""
    assert urls_sitemap(xml) == ["https://honeybeehealth.com/drugs/casodex"]
