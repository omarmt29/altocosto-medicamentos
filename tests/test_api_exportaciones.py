"""Contrato de exportaciones y conservación del snapshot ante fallos."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import api_v1
from scrapper import exportaciones_diarias as ex


class ExportacionesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = patch.object(ex, "CACHE", Path(self.tmp.name))
        self.cache.start()

    def tearDown(self):
        self.cache.stop()
        self.tmp.cleanup()

    def test_paginacion_filtros_y_fecha(self):
        ex.publicar("fda", [{"n_lista": 5, "medicamento_lista": "Adalimumab", "fecha_dato": "2026-10-12"},
                           {"n_lista": 6, "medicamento_lista": "Otro", "fecha_dato": "2026-10-12"}])
        pagina = api_v1.listar_exportacion("fda", {"limite": ["1"], "offset": ["1"]})
        self.assertEqual(pagina["total"], 2)
        self.assertEqual(pagina["filas"][0]["n_lista"], 6)
        filtro = api_v1.listar_exportacion("fda", {"n_lista": ["5"], "q": ["ADALI"], "fecha": ["2026-10-12"]})
        self.assertEqual(filtro["total"], 1)
        self.assertFalse(filtro["desactualizado"])

    def test_sin_snapshot_no_finge_exito(self):
        result = api_v1.listar_exportacion("ema", {})
        self.assertFalse(result["ok"])
        self.assertEqual(result["actualizacion"]["estado"], "pendiente")

    def test_fallo_preserva_snapshot_y_publica_error(self):
        ex.publicar("ema", [{"n_lista": 5}])
        snapshot = ex.leer("ema")
        with patch.dict(ex.ACTUALIZADORES, {"ema": lambda: ex.publicar("ema", [])}):
            self.assertEqual(ex.actualizar("ema"), 1)
        self.assertEqual(ex.leer("ema"), snapshot)
        self.assertEqual(api_v1.listar_exportacion("ema", {})["actualizacion"]["estado"], "error")

    def test_catalogo_sin_descargas_y_datos_antiguos(self):
        ex.guardar("tasas", {"actualizado_en": "2000-01-01T00:00:00-04:00", "filas": [{"moneda": "DOP"}]})
        catalogo = api_v1.fuentes_adicionales()
        self.assertEqual(len(catalogo["monedas"]), 19)
        self.assertTrue(catalogo["exportaciones"]["tasas"]["desactualizado"])
        self.assertFalse(catalogo["exportaciones"]["fda"]["disponible"])
        self.assertEqual(len(catalogo["regulatorias"]), 6)

    def test_limites_y_moneda(self):
        ex.publicar("tasas", [{"moneda": "DOP", "valor": 60}, {"moneda": "BRL", "valor": 5}])
        pagina = api_v1.listar_exportacion("tasas", {"moneda": ["DOP"], "limite": ["9999"], "offset": ["-1"]})
        self.assertEqual((pagina["total"], pagina["limite"], pagina["offset"]), (1, 2000, 0))
        json.dumps(pagina)

    def test_bloqueo_no_reemplaza_estado_en_curso(self):
        import fcntl
        ex.guardar("ema-estado", {"estado": "running"})
        with (ex.CACHE / "ema.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(ex.actualizar("ema"), 1)
        self.assertEqual(ex.leer("ema-estado"), {"estado": "running"})

    def test_fda_fallo_de_un_principio_no_publica_resultado_parcial(self):
        from contextlib import ExitStack
        from scrapper import fda_openfda_info as fda
        from scrapper import fda_patentes as pat
        import lista
        ex.publicar("purple-book", [{"n_lista": 5}])
        ex.publicar("fda", [{"n_lista": 1, "indicaciones_uso": "Anterior"}])
        previo = ex.leer("fda")
        def construir(med, *args, **kwargs):
            if med["n"] == 6:
                raise RuntimeError("Falló principio 6")
            return {"n_lista": med["n"], "medicamento_lista": med["nombre"], "patentes_json": []}
        with ExitStack() as stack:
            stack.enter_context(patch.object(lista, "MEDICAMENTOS", [{"n": 5, "nombre": "A"}, {"n": 6, "nombre": "B"}]))
            stack.enter_context(patch.object(fda, "construir_info", side_effect=construir))
            stack.enter_context(patch.object(pat, "asegurar_orange_book"))
            stack.enter_context(patch.object(pat, "asegurar_purple_patents"))
            stack.enter_context(patch.object(pat, "_leer_ob_txt", return_value=[]))
            self.assertEqual(ex.actualizar("fda"), 1)
        self.assertEqual(ex.leer("fda"), previo)
        self.assertEqual(ex.leer("fda-estado")["estado"], "error")


class BancosTest(unittest.TestCase):
    def test_bcrd_fecha_y_tasa_real_sin_valor_fijo(self):
        from scrapper.fx import tasa_dop
        from unittest.mock import Mock
        ses = Mock()
        ses.get.return_value.text = """<a alt='Tipo de cambio'><span>9 de Octubre 2026</span></a>
            <small>Compra</small><h5>61.1168</h5><small>Venta</small><h5>61.8247</h5></table>"""
        tasa = tasa_dop(ses)
        self.assertEqual(tasa["valor"], 61.8247)
        self.assertEqual(tasa["compra"], 61.1168)
        self.assertEqual(tasa["fecha"], "2026-10-09")
        ses.get.return_value.text = "Sin cotización"
        with self.assertRaises(ValueError):
            tasa_dop(ses)

    def test_reserva_no_se_etiqueta_bcrd_y_pab_es_paridad(self):
        from generar_comparativo import tasas, FX_URL
        from scrapper.fx import ER_API
        from unittest.mock import Mock
        ses = Mock()
        respuesta = Mock()
        respuesta.json.return_value = {"rates": {"DOP": 62.5, "MXN": 20, "PAB": 9}, "time_last_update_unix": 1791763200}
        def get(url, **kwargs):
            if url in (FX_URL, ER_API):
                return respuesta
            raise RuntimeError("Fuente bancaria fuera de servicio")
        ses.get.side_effect = get
        datos = tasas(ses)
        self.assertEqual(datos["por_usd"]["DOP"]["fuente"], "open.er-api.com")
        self.assertEqual(datos["por_usd"]["DOP"]["valor"], 62.5)
        self.assertTrue(datos["por_usd"]["DOP"]["fecha"])
        self.assertEqual(datos["por_usd"]["PAB"]["valor"], 1.0)
        self.assertIsNone(datos["bcrd_compra"])

    def test_ema_match_conserva_sufijos_y_marcas(self):
        from scrapper.ema_medicines import _match_ema
        self.assertTrue(_match_ema("adalimumab", "", "Humira", ["adalimumab"]))
        self.assertTrue(_match_ema("adalimumabxxxx", "", "", ["adalimumab"]))
        self.assertFalse(_match_ema("pegfilgrastim", "", "", ["filgrastim"]))
        self.assertTrue(_match_ema("", "", "Humira", ["humira"]))


if __name__ == "__main__":
    unittest.main()
