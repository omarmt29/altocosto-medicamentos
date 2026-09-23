"""Sirve la plataforma y comprueba la conexión a REDATAM."""

from __future__ import annotations

import json
import os
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

import db

load_dotenv()

ROOT = Path(__file__).resolve().parent / "plataforma"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8765"))


def _qs_uno(qs: dict, *nombres: str) -> str | None:
    for n in nombres:
        vals = qs.get(n)
        if vals:
            v = str(vals[0]).strip()
            if v:
                return v
    return None


def _qs_lista(qs: dict, nombre: str) -> list[str]:
    """Acepta ?pais=A&pais=B y ?pais=A,B indistintamente."""
    out: list[str] = []
    for raw in qs.get(nombre) or []:
        for parte in str(raw).split(","):
            v = parte.strip()
            if v and v not in out:
                out.append(v)
    return out


def _qs_num(qs: dict, nombre: str) -> float | None:
    v = _qs_uno(qs, nombre)
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _qs_bool(qs: dict, nombre: str) -> bool:
    return (_qs_uno(qs, nombre) or "").lower() in {"1", "true", "si", "sí", "on"}


def _buscar_precios_args(qs: dict) -> dict:
    n_raw = _qs_uno(qs, "n_lista", "n")
    return {
        "q": _qs_uno(qs, "q", "texto"),
        "n_lista": int(n_raw) if n_raw and n_raw.lstrip("-").isdigit() else None,
        "paises": _qs_lista(qs, "pais") or _qs_lista(qs, "paises"),
        "farmacias": _qs_lista(qs, "farmacia") or _qs_lista(qs, "farmacias"),
        "programas": _qs_lista(qs, "programa") or _qs_lista(qs, "programas"),
        "fecha": _qs_uno(qs, "fecha"),
        "precio_min_usd": _qs_num(qs, "precio_min"),
        "precio_max_usd": _qs_num(qs, "precio_max"),
        "solo_min": _qs_bool(qs, "solo_min"),
        "min_paises": int(_qs_num(qs, "min_paises") or 0),
        "todas_presentaciones": _qs_bool(qs, "todas"),
        "modo_precio": _qs_uno(qs, "modo_precio", "alcance_precio", "modo") or "paquete",
        "orden": _qs_uno(qs, "orden") or "precio_asc",
        "limite": int(_qs_num(qs, "limite") or 300),
    }


def _tendencias_detalle_response(qs: dict, hist) -> tuple[dict, int] | None:
    """Modal de panorama: detalle por principio, país o fecha."""
    detalle = (qs.get("detalle") or qs.get("tipo") or [None])[0]
    if not detalle:
        return None
    if detalle == "principio":
        n_raw = (qs.get("n_lista") or qs.get("n") or [None])[0]
        if n_raw is None:
            return {"ok": False, "error": "Falta n_lista"}, 400
        n = int(n_raw)
        meds = hist.listar_medicamentos_con_historial(n_lista=n, limite=500)
        return {
            "ok": True,
            "tipo": "principio",
            "n_lista": n,
            "medicamentos": meds,
            "total": len(meds),
        }, 200
    if detalle == "pais":
        pais = (qs.get("pais") or [None])[0]
        if not pais:
            return {"ok": False, "error": "Falta pais"}, 400
        fecha = (qs.get("fecha") or [None])[0]
        ind = hist.resumen_indicadores_tendencias()
        fd = fecha or ind.get("ultima_fecha")
        meds = hist.listar_medicamentos_por_pais(str(pais), fecha_dato=fd, limite=500)
        row = next(
            (r for r in (ind.get("por_pais") or []) if str(r.get("pais")) == str(pais)),
            {},
        )
        return {
            "ok": True,
            "tipo": "pais",
            "pais": str(pais),
            "fecha": fd,
            "resumen": row,
            "medicamentos": meds,
            "total": len(meds),
        }, 200
    if detalle == "fecha":
        fecha = (qs.get("fecha") or [None])[0]
        if not fecha:
            return {"ok": False, "error": "Falta fecha"}, 400
        fd = str(fecha).strip()[:10]
        meds = hist.listar_medicamentos_por_fecha(fd, limite=300)
        ind = hist.resumen_indicadores_tendencias()
        row = next(
            (
                r
                for r in (ind.get("puntos_por_fecha") or [])
                if str(r.get("fecha")).startswith(fd)
            ),
            {},
        )
        return {
            "ok": True,
            "tipo": "fecha",
            "fecha": fd,
            "resumen": row,
            "medicamentos": meds,
            "total": len(meds),
        }, 200
    return {"ok": False, "error": "detalle inválido (principio|pais|fecha)"}, 400


def _traducir_ema_payload(info: dict, filas: list, tr) -> tuple[dict, list]:
    """Traduce indicaciones EMA (con caché en disco) antes de devolver al front."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    textos: list[str] = []
    seen: set[str] = set()
    for t in (info or {}).get("indicaciones") or []:
        s = str(t or "").strip()
        if s and s not in seen:
            seen.add(s)
            textos.append(s)
    for f in filas or []:
        s = str(f.get("therapeutic_indication") or "").strip()
        if s and s not in seen:
            seen.add(s)
            textos.append(s)

    # Limitar a 4 textos únicos por request (evita timeouts / 429)
    textos = textos[:4]
    mapa: dict[str, str] = {}
    if textos:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futs = {pool.submit(tr.traducir, t): t for t in textos}
            for fut in as_completed(futs):
                raw = futs[fut]
                try:
                    res = fut.result()
                    mapa[raw] = str((res or {}).get("texto") or raw)
                except Exception:
                    mapa[raw] = raw

    if info is not None:
        inds = list(info.get("indicaciones") or [])
        info = dict(info)
        info["indicaciones_es"] = [mapa.get(str(t).strip(), t) for t in inds]

    out_filas = []
    for f in filas or []:
        row = dict(f)
        raw = str(row.get("therapeutic_indication") or "").strip()
        if raw and raw in mapa:
            row["therapeutic_indication_es"] = mapa[raw]
        out_filas.append(row)
    return info, out_filas


def _traducir_areas_ema(info: dict | None, filas: list, tr) -> tuple[dict | None, list]:
    """Traduce áreas terapéuticas MeSH (glosario; sin saturar Google)."""
    out_filas = []
    for f in filas or []:
        row = dict(f)
        raw = str(row.get("therapeutic_area") or "").strip()
        if raw:
            try:
                row["therapeutic_area_es"] = tr.traducir_areas_terapeuticas(raw, usar_motor=False)
            except Exception:
                row["therapeutic_area_es"] = raw
        out_filas.append(row)

    if info is None:
        return None, out_filas

    info = dict(info)
    areas = list(info.get("therapeutic_areas") or [])
    areas_es: list[str] = []
    seen: set[str] = set()
    for a in areas:
        try:
            es = tr.traducir_termino_area(str(a or "").strip(), usar_motor=False)
        except Exception:
            es = str(a or "").strip()
        if not es:
            continue
        k = es.lower()
        if k in seen:
            continue
        seen.add(k)
        areas_es.append(es)
    info["therapeutic_areas_es"] = areas_es
    return info, out_filas


def _enriquecer_overview_es(info: dict | None, filas: list) -> tuple[dict | None, list]:
    """Preferir Medicine Overview EPAR en español frente a traducción automática."""
    try:
        from scrapper import ema_overview_es as ov

        return ov.enriquecer_filas_ema(filas or [], info)
    except Exception:
        return info, filas or []


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, payload: dict, status: int = 200) -> None:
        cuerpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path in ("/api/salud", "/api/db"):
            estado = db.ping()
            self._json(estado, 200 if estado["ok"] else 503)
            return
        if path == "/api/precios":
            try:
                import importlib

                import scrapper.repositorio as repo

                importlib.reload(repo)
                fd_q = (qs.get("fecha_dato") or [None])[0]
                todos = (qs.get("todos") or ["0"])[0] in ("1", "true", "True")
                snapshot = None if todos else (
                    repo._parse_fecha_dato(fd_q) if fd_q else repo.fecha_snapshot()
                )
                filas = repo.listar_filas(fecha_dato=snapshot, todos=todos)
                try:
                    from scrapper.vtex_urls import normalizar_fila

                    filas = [normalizar_fila(f) for f in filas]
                except Exception:
                    pass
                self._json(
                    {
                        "ok": True,
                        "total": len(filas),
                        "fecha_dato": snapshot.isoformat() if snapshot else None,
                        "snapshot": snapshot.isoformat() if snapshot else None,
                        "todos": todos,
                        "filas": filas,
                    }
                )
            except Exception as exc:
                self._json({"ok": False, "error": str(exc), "filas": []}, 500)
            return
        if path == "/api/tasas":
            try:
                from scrapper.fx import tasas_para_web

                self._json({"ok": True, "tasas": tasas_para_web()})
            except Exception as exc:
                self._json({"ok": False, "error": str(exc), "tasas": []}, 500)
            return
        if path == "/api/purple-book":
            try:
                import importlib

                import scrapper.repositorio_purple as pb

                importlib.reload(pb)
                n_raw = (qs.get("n_lista") or qs.get("n") or [None])[0]
                fd = (qs.get("fecha_dato") or [None])[0]
                if n_raw is None:
                    self._json(
                        {
                            "ok": True,
                            "resumen": pb.resumen_cobertura(fd),
                            "periodos": pb.periodos_disponibles(),
                            "filas": [],
                        }
                    )
                    return
                n_lista = int(n_raw)
                filas = pb.listar_por_n(n_lista, fecha_dato=fd, solo_ultimo=not bool(fd))
                info = None
                try:
                    import scrapper.repositorio_fda_info as fi

                    importlib.reload(fi)
                    info = fi.obtener_info(n_lista, fecha_dato=fd)
                except Exception:
                    info = None
                # Resolver siempre que el snapshot no tenga un PDF FDA directo.
                # DailyMed/openFDA no debe impedir la consulta del Label PDF.
                # Revalidar siempre contra la aplicación de referencia: un snapshot
                # anterior puede tener el PDF de otra marca (p. ej. POSFREA).
                refresh_fda_label = True
                if refresh_fda_label:
                    try:
                        from lista import MEDICAMENTOS
                        from scrapper.fda_openfda_info import (
                            _aliases_busqueda,
                            _session,
                            fetch_latest_drugsfda_label_pdf,
                        )

                        med = next(
                            (m for m in MEDICAMENTOS if int(m.get("n", -1)) == n_lista),
                            None,
                        )
                        if med:
                            productos = list((info or {}).get("productos_fda") or [])
                            activo = str(med.get("nombre") or "").lower().replace("é", "e")
                            def es_activo_exacto(p):
                                ingrediente = str(p.get("ingredient") or p.get("substance") or "").lower().replace("é", "e")
                                if not ingrediente or any(x in ingrediente for x in (" and ", "+", ";")):
                                    return False
                                return activo and activo in ingrediente

                            productos_ref = [
                                p for p in productos
                                if str(p.get("clase") or "").lower() in {"marca_nda", "marca_bla", "referencia"}
                                and es_activo_exacto(p)
                            ]
                            if not productos_ref:
                                productos_ref = [
                                    p for p in productos
                                    if str(p.get("clase") or "").lower() in {"marca_nda", "marca_bla", "referencia"}
                                    and not any(x in str(p.get("ingredient") or p.get("substance") or "").lower() for x in (" and ", "+", ";"))
                                ]
                            filas_ref = [
                                f for f in filas
                                if str(f.get("clase_producto") or f.get("tipo_licencia") or "").lower() in {"referencia", "351(a)", "innovador"}
                                and not any(x in str(f.get("nombre_propio") or "").lower() for x in (" and ", "+", ";"))
                            ]
                            application_numbers = set()
                            for referencia in (productos_ref or productos or filas_ref or filas):
                                at = str(referencia.get("appl_type") or "").strip().upper()
                                an = str(referencia.get("appl_no") or "").strip()
                                bla = str(referencia.get("bla_number") or "").strip()
                                if at and an:
                                    at = {"N": "NDA", "A": "ANDA"}.get(at, at)
                                    application_numbers.add(f"{at}{an}")
                                elif bla:
                                    application_numbers.add(f"BLA{bla}")
                            latest = fetch_latest_drugsfda_label_pdf(
                                _session(),
                                _aliases_busqueda(med),
                                application_numbers=application_numbers or None,
                            )
                            if latest.get("pdf_url"):
                                info = dict(info or {})
                                info["fuente_indicaciones_pdf"] = latest["pdf_url"]
                                info["fuente_indicaciones_drugsfda_date"] = latest.get("action_date")
                                info["fuente_indicaciones_drugsfda_app"] = latest.get("application_number")
                                info["fuente_indicaciones_drugsfda_submission"] = latest.get("submission")
                    except Exception:
                        pass
                # Recalcular estado de patentes a la fecha de hoy (alineado con Alertas).
                if isinstance(info, dict) and isinstance(info.get("patentes"), list):
                    try:
                        from datetime import date as _date

                        from scrapper.fda_patentes import _estado_fecha, _parse_fecha

                        hoy = _date.today()
                        pats = []
                        for p in info["patentes"]:
                            if not isinstance(p, dict):
                                continue
                            row = dict(p)
                            exp = None
                            raw_exp = row.get("expiration_date")
                            if raw_exp:
                                try:
                                    exp = _date.fromisoformat(str(raw_exp)[:10])
                                except ValueError:
                                    exp = _parse_fecha(str(raw_exp))
                            if exp is None:
                                exp = _parse_fecha(row.get("expiration_text"))
                            row["estado_snapshot"] = row.get("estado")
                            row["estado"] = _estado_fecha(exp, hoy)
                            pats.append(row)
                        info = dict(info)
                        info["patentes"] = pats
                    except Exception:
                        pass
                self._json(
                    {
                        "ok": True,
                        "n_lista": n_lista,
                        "total": len(filas),
                        "periodos": pb.periodos_disponibles(n_lista),
                        "info": info,
                        "filas": filas,
                    }
                )
            except Exception as exc:
                self._json({"ok": False, "error": str(exc), "filas": []}, 500)
            return
        if path == "/api/ema":
            try:
                import importlib

                import scrapper.repositorio_ema as ema
                import scrapper.traducir as tr

                # no reload en cada request: el traductor es pesado y satura Google
                n_raw = (qs.get("n_lista") or qs.get("n") or [None])[0]
                fd = (qs.get("fecha_dato") or [None])[0]
                skip_tr = (qs.get("traducir") or ["0"])[0] not in ("1", "true", "yes")
                if n_raw is None:
                    self._json(
                        {
                            "ok": True,
                            "periodos": ema.periodos_disponibles(),
                            "filas": [],
                            "info": None,
                        }
                    )
                    return
                n_lista = int(n_raw)
                filas = ema.listar_por_n(n_lista, fecha_dato=fd, solo_ultimo=not bool(fd))
                info = ema.resumir_info(filas)
                # Áreas terapéuticas: siempre a ES (glosario, barato)
                info, filas = _traducir_areas_ema(info, filas, tr)
                # Medicine Overview EPAR en español (PDF oficial)
                info, filas = _enriquecer_overview_es(info, filas)
                # Traducción automática solo como respaldo si aún falta ES
                if info and not skip_tr:
                    info, filas = _traducir_ema_payload(info, filas, tr)
                self._json(
                    {
                        "ok": True,
                        "n_lista": n_lista,
                        "total": len(filas),
                        "periodos": ema.periodos_disponibles(n_lista),
                        "info": info,
                        "filas": filas,
                    }
                )
            except Exception as exc:
                self._json({"ok": False, "error": str(exc), "filas": []}, 500)
            return
        if path == "/api/tendencias/indicadores":
            try:
                import importlib

                import scrapper.repositorio_historial as hist

                importlib.reload(hist)
                self._json(
                    {
                        "ok": True,
                        "indicadores": hist.resumen_indicadores_tendencias(),
                    }
                )
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/tendencias/buscar":
            try:
                import importlib

                import scrapper.repositorio_historial as hist

                importlib.reload(hist)
                self._json({"ok": True, **hist.buscar_precios(**_buscar_precios_args(qs))})
            except Exception as exc:
                self._json({"ok": False, "error": str(exc), "filas": []}, 500)
            return
        if path == "/api/tendencias/graficos":
            try:
                import importlib

                import scrapper.graficos_tendencias as graf

                importlib.reload(graf)
                self._json(
                    graf.panel_graficos(
                        fecha=_qs_uno(qs, "fecha"),
                        pais_a=_qs_uno(qs, "pais_a", "paisA"),
                        pais_b=_qs_uno(qs, "pais_b", "paisB"),
                        paises_cmp=_qs_lista(qs, "pais") or _qs_lista(qs, "paises"),
                        incluir_figuras=_qs_bool(qs, "figuras"),
                    )
                )
            except Exception as exc:
                self._json({"ok": False, "error": str(exc), "figuras": {}}, 500)
            return
        if path == "/api/tendencias/temas":
            try:
                import importlib

                import scrapper.graficos_tendencias as graf
                import scrapper.repositorio_ema as ema

                importlib.reload(ema)
                importlib.reload(graf)
                tema = _qs_uno(qs, "tema", "tema_id", "id")
                if not tema:
                    self._json(graf.catalogo_temas(fecha=_qs_uno(qs, "fecha")))
                    return
                self._json(
                    graf.panel_tema(
                        tema_id=tema,
                        fecha=_qs_uno(qs, "fecha"),
                        pais_a=_qs_uno(qs, "pais_a", "paisA"),
                        pais_b=_qs_uno(qs, "pais_b", "paisB"),
                        paises_cmp=_qs_lista(qs, "pais") or _qs_lista(qs, "paises"),
                    )
                )
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/tendencias/detalle":
            try:
                import importlib

                import scrapper.repositorio_historial as hist

                importlib.reload(hist)
                det = _tendencias_detalle_response(qs, hist)
                if det is None:
                    self._json({"ok": False, "error": "Falta detalle o tipo"}, 400)
                    return
                payload, status = det
                self._json(payload, status)
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/tendencias":
            try:
                import importlib

                import scrapper.repositorio_historial as hist

                importlib.reload(hist)
                det = _tendencias_detalle_response(qs, hist)
                if det is not None:
                    payload, status = det
                    self._json(payload, status)
                    return
                n_raw = (qs.get("n_lista") or qs.get("n") or [None])[0]
                pk_raw = (qs.get("producto_key") or qs.get("producto") or [None])[0]
                if n_raw is None:
                    self._json(
                        {
                            "ok": True,
                            "fechas": hist.fechas_disponibles(),
                            "medicamentos": hist.listar_medicamentos_con_historial(limite=5000),
                            "principios": hist.listar_principios_con_historial(),
                            "indicadores": hist.resumen_indicadores_tendencias(),
                        }
                    )
                    return
                if not pk_raw:
                    self._json(
                        {"ok": False, "error": "Falta producto_key (seleccione un medicamento concreto)."},
                        400,
                    )
                    return
                data = hist.serie_medicamento(
                    int(n_raw),
                    str(pk_raw),
                    agrupar=(qs.get("agrupar") or ["pais"])[0],
                    paises=(qs.get("paises") or [None])[0],
                    farmacias=(qs.get("farmacias") or [None])[0],
                )
                self._json({"ok": True, **data})
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/alertas/patentes":
            try:
                import importlib

                import scrapper.repositorio_alertas_patentes as ap

                importlib.reload(ap)
                fuente = (qs.get("fuente") or [None])[0]
                tipo = (qs.get("tipo") or [None])[0]
                solo = (qs.get("solo_no_leidas") or ["0"])[0] in ("1", "true", "True")
                desde = (qs.get("desde") or [None])[0]
                hasta = (qs.get("hasta") or [None])[0]
                lim_raw = (qs.get("limite") or ["200"])[0]
                try:
                    limite = int(lim_raw)
                except (TypeError, ValueError):
                    limite = 200
                filas = ap.listar_alertas(
                    fuente=fuente,
                    tipo=tipo,
                    solo_no_leidas=solo,
                    desde=desde,
                    hasta=hasta,
                    limite=limite,
                )
                resumen = ap.resumen_alertas()
                configs = ap.listar_configs()
                resumen["configs_activas"] = sum(1 for c in configs if c.get("activo") in (1, True, "1"))
                resumen["configs_total"] = len(configs)
                resumen["horizonte_max_config"] = ap.horizonte_max_configs()
                self._json(
                    {
                        "ok": True,
                        "total": len(filas),
                        "resumen": resumen,
                        "filas": filas,
                        "configs": configs,
                        "opciones_criterios": ap.opciones_criterios_patentes(),
                    }
                )
            except Exception as exc:
                self._json({"ok": False, "error": str(exc), "filas": []}, 500)
            return
        if path == "/api/alertas/patentes/configs":
            try:
                import importlib

                import scrapper.repositorio_alertas_patentes as ap

                importlib.reload(ap)
                self._json(
                    {
                        "ok": True,
                        "configs": ap.listar_configs(),
                        "opciones": ap.opciones_criterios_patentes(),
                        "horizonte_max": ap.horizonte_max_configs(),
                    }
                )
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/alertas/patentes/resumen":
            try:
                import importlib

                import scrapper.repositorio_alertas_patentes as ap

                importlib.reload(ap)
                self._json({"ok": True, "resumen": ap.resumen_alertas()})
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/alertas/precios":
            try:
                import importlib

                import scrapper.repositorio_alertas_precios as ap

                importlib.reload(ap)
                tipo = (qs.get("tipo") or [None])[0]
                solo = (qs.get("solo_no_leidas") or ["0"])[0] in ("1", "true", "True")
                cfg_raw = (qs.get("config_id") or [None])[0]
                lim_raw = (qs.get("limite") or ["200"])[0]
                try:
                    limite = int(lim_raw)
                except (TypeError, ValueError):
                    limite = 200
                config_id = None
                if cfg_raw not in (None, ""):
                    try:
                        config_id = int(cfg_raw)
                    except (TypeError, ValueError):
                        config_id = None
                filas = ap.listar_alertas(
                    config_id=config_id,
                    tipo=tipo,
                    solo_no_leidas=solo,
                    limite=limite,
                )
                self._json(
                    {
                        "ok": True,
                        "total": len(filas),
                        "resumen": ap.resumen_alertas(),
                        "configs": ap.listar_configs(),
                        "filas": filas,
                    }
                )
            except Exception as exc:
                self._json({"ok": False, "error": str(exc), "filas": [], "configs": []}, 500)
            return
        if path == "/api/alertas/precios/configs":
            try:
                import importlib

                import scrapper.repositorio_alertas_precios as ap

                importlib.reload(ap)
                solo = (qs.get("solo_activas") or ["0"])[0] in ("1", "true", "True")
                self._json({"ok": True, "configs": ap.listar_configs(solo_activas=solo)})
            except Exception as exc:
                self._json({"ok": False, "error": str(exc), "configs": []}, 500)
            return
        if path == "/api/alertas/precios/opciones":
            try:
                import importlib

                import scrapper.repositorio_alertas_precios as ap

                importlib.reload(ap)
                n_raw = (qs.get("n_lista") or [None])[0]
                n_lista = None
                if n_raw not in (None, ""):
                    try:
                        n_lista = int(n_raw)
                    except (TypeError, ValueError):
                        n_lista = None
                opts = ap.opciones_filtros(
                    pais=(qs.get("pais") or [None])[0] or None,
                    farmacia=(qs.get("farmacia") or [None])[0] or None,
                    producto_key=(qs.get("producto_key") or [None])[0] or None,
                    n_lista=n_lista,
                    presentacion=(qs.get("presentacion") or [None])[0] or None,
                )
                self._json({"ok": True, **opts})
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/alertas/precios/resumen":
            try:
                import importlib

                import scrapper.repositorio_alertas_precios as ap

                importlib.reload(ap)
                self._json({"ok": True, "resumen": ap.resumen_alertas()})
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/fuentes-jobs":
            try:
                import importlib

                import scrapper.jobs_cola as jobs
                import scrapper.repositorio_cron_log as cronlog

                importlib.reload(jobs)
                importlib.reload(cronlog)
                self._json(
                    {
                        "ok": True,
                        "fuentes": jobs.listar_fuentes(),
                        "estados": jobs.estados_por_fuente(),
                        "recientes": jobs.listar_jobs(limite=30),
                        "cron": cronlog.ultima_corrida_completa(),
                        "cron_corridas": cronlog.listar_corridas(limite=10),
                    }
                )
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/cron-log":
            try:
                import importlib

                import scrapper.repositorio_cron_log as cronlog

                importlib.reload(cronlog)
                lim_raw = (qs.get("limite") or ["20"])[0]
                try:
                    limite = max(1, min(100, int(lim_raw)))
                except (TypeError, ValueError):
                    limite = 20
                self._json(
                    {
                        "ok": True,
                        "corridas": cronlog.listar_corridas(limite=limite),
                        "ultima": cronlog.ultima_corrida_completa(),
                    }
                )
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path.startswith("/api/cron-log/"):
            try:
                import importlib

                import scrapper.repositorio_cron_log as cronlog

                importlib.reload(cronlog)
                cid = int(path.rsplit("/", 1)[-1])
                corrida = cronlog.obtener_corrida(cid)
                if not corrida:
                    self._json({"ok": False, "error": "Corrida no encontrada"}, 404)
                    return
                corrida = dict(corrida)
                corrida["pasos"] = cronlog.listar_pasos(cid)
                self._json({"ok": True, "corrida": corrida})
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path.startswith("/api/jobs/"):
            try:
                import importlib

                import scrapper.jobs_cola as jobs

                importlib.reload(jobs)
                job_id = int(path.rsplit("/", 1)[-1])
                row = jobs.obtener(job_id)
                if not row:
                    self._json({"ok": False, "error": "Job no encontrado"}, 404)
                    return
                self._json({"ok": True, "job": row})
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/jobs":
            try:
                import importlib

                import scrapper.jobs_cola as jobs

                importlib.reload(jobs)
                fuente = (qs.get("fuente") or [None])[0]
                self._json({"ok": True, "jobs": jobs.listar_jobs(limite=50, fuente_id=fuente)})
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return

        relativo = path.lstrip("/") or "index.html"
        destino = ROOT / relativo
        if not destino.exists():
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/traducir":
            try:
                import scrapper.traducir as tr

                body = self._read_json_body()
                texto = body.get("texto") or ""
                textos = body.get("textos")
                fuente = str(body.get("fuente") or "en")
                destino = str(body.get("destino") or "es")
                if isinstance(textos, list):
                    # máximo 4 por request para no saturar Google
                    lote = [str(x or "") for x in textos[:4]]
                    out = tr.traducir_lista(lote, fuente=fuente, destino=destino)
                    self._json({"ok": True, "textos": out})
                    return
                res = tr.traducir(str(texto), fuente=fuente, destino=destino)
                self._json(res)
            except Exception as exc:
                self._json({"ok": False, "error": str(exc), "texto": ""}, 500)
            return
        if path == "/api/jobs":
            try:
                import importlib

                import scrapper.jobs_cola as jobs

                importlib.reload(jobs)
                body = self._read_json_body()
                fuente = str(body.get("fuente") or body.get("fuente_id") or "").strip()
                force = bool(body.get("force"))
                if not fuente:
                    self._json({"ok": False, "error": "Falta fuente"}, 400)
                    return
                job = jobs.encolar(fuente, solicitado_por="ui", force=force)
                self._json({"ok": True, "job": job})
            except ValueError as exc:
                self._json({"ok": False, "error": str(exc)}, 400)
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/alertas/patentes/detectar":
            try:
                import importlib

                import scrapper.alertas_patentes as det

                importlib.reload(det)
                body = self._read_json_body()
                fuente = str(body.get("fuente") or "todas").strip().lower()
                if fuente == "fda":
                    r = det.detectar_fda()
                    crit = det.evaluar_criterios_config()
                    r = {
                        **r,
                        "criterios": crit,
                        "insertadas": int(r.get("insertadas") or 0) + int(crit.get("insertadas") or 0),
                        "mensaje": f"{r.get('mensaje')} {crit.get('mensaje')}",
                    }
                elif fuente == "ema":
                    r = det.detectar_ema()
                else:
                    r = det.detectar_todas()
                self._json(r)
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/alertas/patentes/configs":
            try:
                import importlib

                import scrapper.repositorio_alertas_patentes as ap

                importlib.reload(ap)
                body = self._read_json_body()
                accion = str(body.get("accion") or "guardar").strip().lower()
                if accion == "eliminar":
                    cid = body.get("id")
                    if cid is None:
                        self._json({"ok": False, "error": "Falta id"}, 400)
                        return
                    ok = ap.eliminar_config(int(cid))
                    self._json({"ok": ok})
                    return
                if accion == "activar":
                    cid = body.get("id")
                    if cid is None:
                        self._json({"ok": False, "error": "Falta id"}, 400)
                        return
                    ok = ap.set_config_activa(int(cid), bool(body.get("activo", True)))
                    self._json({"ok": ok})
                    return
                if accion == "evaluar":
                    import scrapper.alertas_patentes as det

                    importlib.reload(det)
                    r = det.evaluar_criterios_config()
                    self._json(r)
                    return
                if accion == "marcar_notificado":
                    ids = body.get("ids") or []
                    if body.get("id") is not None:
                        ids = list(ids) + [body.get("id")]
                    n = ap.marcar_notificacion_configs(ids)
                    self._json({"ok": True, "actualizadas": n})
                    return
                if accion == "reasaltar":
                    ids = body.get("ids") or []
                    if body.get("id") is not None:
                        ids = list(ids) + [body.get("id")]
                    n_alertas = ap.marcar_no_leidas_por_criterios(ids)
                    n_cfg = ap.marcar_notificacion_configs(ids)
                    self._json({
                        "ok": True,
                        "alertas_reasaltadas": n_alertas,
                        "configs_marcadas": n_cfg,
                    })
                    return
                row = ap.guardar_config(body)
                self._json({"ok": True, "config": row})
            except ValueError as exc:
                self._json({"ok": False, "error": str(exc)}, 400)
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/alertas/patentes/leer":
            try:
                import importlib

                import scrapper.repositorio_alertas_patentes as ap

                importlib.reload(ap)
                body = self._read_json_body()
                if body.get("todas"):
                    n = ap.marcar_todas_leidas(fuente=body.get("fuente"))
                    self._json({"ok": True, "actualizadas": n})
                    return
                aid = body.get("id")
                if aid is None:
                    self._json({"ok": False, "error": "Falta id o todas=true"}, 400)
                    return
                ok = ap.marcar_leida(int(aid), leida=bool(body.get("leida", True)))
                self._json({"ok": ok})
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/alertas/precios/configs":
            try:
                import importlib

                import scrapper.repositorio_alertas_precios as ap

                importlib.reload(ap)
                body = self._read_json_body()
                accion = str(body.get("accion") or "guardar").strip().lower()
                if accion == "eliminar":
                    cid = body.get("id")
                    if cid is None:
                        self._json({"ok": False, "error": "Falta id"}, 400)
                        return
                    ok = ap.eliminar_config(int(cid))
                    self._json({"ok": ok})
                    return
                if accion == "activar":
                    cid = body.get("id")
                    if cid is None:
                        self._json({"ok": False, "error": "Falta id"}, 400)
                        return
                    ok = ap.set_config_activa(int(cid), bool(body.get("activo", True)))
                    self._json({"ok": ok})
                    return
                if accion == "reasaltar":
                    ids = body.get("ids") or []
                    if body.get("id") is not None:
                        ids = list(ids) + [body.get("id")]
                    n_alertas = ap.marcar_no_leidas_por_configs(ids)
                    n_cfg = ap.marcar_notificacion_configs(ids)
                    self._json({
                        "ok": True,
                        "alertas_reasaltadas": n_alertas,
                        "configs_marcadas": n_cfg,
                    })
                    return
                row = ap.guardar_config(body)
                self._json({"ok": True, "config": row})
            except ValueError as exc:
                self._json({"ok": False, "error": str(exc)}, 400)
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/alertas/precios/detectar":
            try:
                import importlib

                import scrapper.alertas_precios as det

                importlib.reload(det)
                r = det.detectar_todas()
                self._json(r)
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/alertas/precios/registrar":
            try:
                import importlib

                import scrapper.repositorio_alertas_precios as ap

                importlib.reload(ap)
                body = self._read_json_body()
                ok = ap.registrar_alerta(body)
                self._json({"ok": True, "insertada": ok})
            except ValueError as exc:
                self._json({"ok": False, "error": str(exc)}, 400)
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        if path == "/api/alertas/precios/leer":
            try:
                import importlib

                import scrapper.repositorio_alertas_precios as ap

                importlib.reload(ap)
                body = self._read_json_body()
                if body.get("todas"):
                    n = ap.marcar_todas_leidas()
                    self._json({"ok": True, "actualizadas": n})
                    return
                aid = body.get("id")
                if aid is None:
                    self._json({"ok": False, "error": "Falta id o todas=true"}, 400)
                    return
                ok = ap.marcar_leida(int(aid), leida=bool(body.get("leida", True)))
                self._json({"ok": ok})
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
            return
        self._json({"ok": False, "error": "Not found"}, 404)

    def log_message(self, fmt: str, *args) -> None:
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


if __name__ == "__main__":
    estado = db.ping()
    cfg = db.resumen_config()
    print(f"SQL Server: {cfg['host']}:{cfg['port']} / {cfg['database']}.{cfg.get('schema', 'dbo')} ({cfg['user']})")
    if estado["ok"]:
        print(f"  OK — {estado.get('servidor')} · {estado.get('db')} · {estado.get('usuario')}")
    else:
        print(f"  ERROR — {estado['mensaje']}")

    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print(f"Plataforma: {url}")
    if os.getenv("OPEN_BROWSER", "").lower() in ("1", "true", "yes"):
        webbrowser.open(url)
    httpd.serve_forever()
