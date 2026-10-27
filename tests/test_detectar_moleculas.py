"""Pruebas de comparación de moléculas FDA/EMA sin base de datos."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scrapper.detectar_moleculas import comparar_ema, comparar_fda  # noqa: E402


class DetectarMoleculasTests(unittest.TestCase):
    def test_fda_primera_aparicion_y_referencia_nueva(self):
        anterior = [
            {"n_lista": 1, "medicamento_lista": "Abiraterona", "tiene_referencia": 0},
            {"n_lista": 5, "medicamento_lista": "Adalimumab", "tiene_referencia": 1},
        ]
        actual = [
            {"n_lista": 1, "medicamento_lista": "Abiraterona", "tiene_referencia": 1, "fuente_url": "https://fda"},
            {"n_lista": 5, "medicamento_lista": "Adalimumab", "tiene_referencia": 1},
            {"n_lista": 47, "medicamento_lista": "Letrozol", "tiene_referencia": 1},
        ]
        alertas = comparar_fda(anterior, actual)
        tipos = {(a["n_lista"], a["tipo_alerta"]) for a in alertas}
        self.assertIn((1, "referencia_nueva"), tipos)
        self.assertIn((47, "primera_aparicion"), tipos)
        self.assertNotIn((5, "referencia_nueva"), tipos)
        self.assertNotIn((5, "primera_aparicion"), tipos)

    def test_fda_sin_anterior_no_inventa_referencia(self):
        actual = [{"n_lista": 6, "medicamento_lista": "X", "tiene_referencia": 1}]
        alertas = comparar_fda([], actual)
        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0]["tipo_alerta"], "primera_aparicion")

    def test_ema_autorizacion_nueva_ignora_biosimilar_y_generico(self):
        anterior = [
            {
                "n_lista": 5,
                "medicamento_lista": "Adalimumab",
                "nombre_medicamento": "Humira",
                "ema_product_number": "EMEA/H/C/000481",
                "medicine_status": "Authorised",
                "es_biosimilar": 0,
                "es_generic": 0,
            }
        ]
        actual = anterior + [
            {
                "n_lista": 5,
                "medicamento_lista": "Adalimumab",
                "nombre_medicamento": "Amgevita",
                "ema_product_number": "EMEA/H/C/004212",
                "medicine_status": "Authorised",
                "es_biosimilar": 1,
                "es_generic": 0,
            },
            {
                "n_lista": 47,
                "medicamento_lista": "Letrozol",
                "nombre_medicamento": "Femara",
                "ema_product_number": "EMEA/H/C/000230",
                "medicine_status": "Authorised",
                "es_biosimilar": 0,
                "es_generic": 0,
                "medicine_url": "https://ema",
            },
            {
                "n_lista": 47,
                "medicamento_lista": "Letrozol",
                "nombre_medicamento": "Genérico X",
                "ema_product_number": "EMEA/H/C/999",
                "medicine_status": "Authorised",
                "es_biosimilar": 0,
                "es_generic": 1,
            },
        ]
        alertas = comparar_ema(anterior, actual)
        tipos = {(a["tipo_alerta"], a.get("clave_producto")) for a in alertas}
        self.assertIn(("primera_aparicion", "47"), tipos)
        self.assertIn(("autorizacion_nueva", "EMEA/H/C/000230"), tipos)
        self.assertNotIn(("autorizacion_nueva", "EMEA/H/C/004212"), tipos)
        self.assertNotIn(("autorizacion_nueva", "EMEA/H/C/999"), tipos)

    def test_ema_no_repite_autorizacion_existente(self):
        filas = [
            {
                "n_lista": 5,
                "medicamento_lista": "Adalimumab",
                "nombre_medicamento": "Humira",
                "ema_product_number": "EMEA/H/C/000481",
                "medicine_status": "Authorised",
                "es_biosimilar": 0,
                "es_generic": 0,
            }
        ]
        self.assertEqual(comparar_ema(filas, filas), [])


if __name__ == "__main__":
    unittest.main()
