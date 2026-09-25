"""Corrida diaria de scrapers RD + BR + MX + CO + AR + CL + PA + PE + UY + SV + PY + VE + GY + TT + BO (cron).

Hidalgos (Cloudflare/Playwright) corre **al final**, en otra imagen.

Uso recomendado (host, una sola corrida secuencial):
    bash scrapper/run_cron_diario.sh
    bash scrapper/run_cron_diario.sh --fresh

Equivalente Python en el host (orquesta los dos contenedores):
    python scrapper/cron_diario.py --fresh

Dentro del contenedor principal (sin Playwright) solo corren los scrapers
livianos; Hidalgos se omite salvo que pases --con-hidalgos y exista Playwright,
o uses el script bash de arriba.

Crontab (ejemplo, 06:15 America/Santo_Domingo):
    15 6 * * * /bin/bash /home/dev/medicamentos_alto_costo/scrapper/run_cron_diario.sh --fresh >> /var/log/alto-costo-cron.log 2>&1

Sin --fresh reanuda caché y solo busca aliases nuevos.
El cron diario debe ser corrida completa (sin --fomac) para actualizar todas las moléculas.
RD: FarmaValue, Carol, farmacias.do, Qualipharma; Hidalgos al final (Playwright).
México: Macrofarmacias, Similares (VTEX), Ahorro (Magento). San Pablo suele ir bloqueado por Akamai.
Brasil: Pague Menos, Drogasil, Droga Raia, Panvel (VTEX; Drogasil/Raia/Panvel pueden fallar por WAF/proxy).
Colombia: Locatel, Farmatodo (Algolia), Carulla (VTEX); Cruz Verde / La Rebaja / Cafam (proxy puede bloquear).
Argentina: Farmacity.
Chile: Salcobrand (Algolia), Farmacias Ahumada (Demandware).
Panamá: Arrocha (Shopify; especialidad online limitada), Pan Am Farma y Farmacias Julios (WooCommerce especialidad).
Perú: Inkafarma (Algolia), Boticas Perú (Demandware), Farmacia Universal (VTEX).
Uruguay: Pigalle, Farmacity UY, Antártida, Goes; Farmashop (VTEX; proxy suele bloquear).
El Salvador: Siman (VTEX); El Farmacéutico (Woo); FarmaValue (API fe-app).
Ecuador: Pharmacy's, Cruz Azul, Fybeca (VTEX DIFARE; Fybeca puede ir bloqueada).
Honduras: Siman, Kielsa (buscador+DDP), Farmacias del Ahorro (SPA).
Guatemala: Siman, Batres, Galeno; Meykos (/api/search); Cruz Verde GT; FarmaValue (fg-app).
Nicaragua: Siman, Kielsa (buscador+DDP), Farmacias del Ahorro (SPA).
Costa Rica: Siman, Kölbi, Fischel; FarmaValue (API cr-app).
Paraguay: Punto Farma (SSR search), Prosalud Farma (Woo Store API).
Bolivia: FSA Tienda Online; Farmacorp (Shopify vía farmacorp.myshopify.com).
Venezuela: Farmacia SAAS (VTEX); Locatel (VTEX, VES).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

IMG_MAIN = os.environ.get("ALTO_COSTO_IMG_MAIN", "medicamentos-alto-costo")
IMG_HIDALGOS = os.environ.get(
    "ALTO_COSTO_IMG_HIDALGOS", "extraccion-medicamentos_extraccion-medicamentos"
)


def _en_contenedor() -> bool:
    return Path("/.dockerenv").exists() or bool(os.environ.get("RUNNING_IN_CONTAINER"))


def _flags_scraper() -> list[str]:
    """Flags que entienden los scrapers individuales (--fresh, --fomac, …)."""
    skip = {"--sin-hidalgos", "--con-hidalgos", "--registrar-hidalgos"}
    out: list[str] = []
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--registrar-hidalgos":
            i += 2
            continue
        if a in skip:
            i += 1
            continue
        out.append(a)
        i += 1
    return out


def _correr_scrapers() -> int:
    from scrapper.rd_farmavalue import main as farmavalue
    from scrapper.rd_carol import main as carol
    from scrapper.rd_qualipharma import main as qualipharma
    from scrapper.br_paguemenos import main as paguemenos
    from scrapper.br_drogasil import main as drogasil
    from scrapper.br_drogaraia import main as drogaraia
    from scrapper.br_panvel import main as panvel
    from scrapper.mx_macrofarmacias import main as macrofarmacias
    from scrapper.mx_similares import main as similares
    from scrapper.mx_fahorro import main as fahorro
    from scrapper.mx_sanpablo import main as sanpablo
    from scrapper.co_locatel import main as locatel
    from scrapper.co_farmatodo import main as farmatodo
    from scrapper.co_cruzverde import main as cruzverde
    from scrapper.co_larebaja import main as larebaja
    from scrapper.co_cafam import main as cafam
    from scrapper.co_carulla import main as carulla
    from scrapper.ar_farmacity import main as farmacity
    from scrapper.ar_alfabeta import main as alfabeta
    from scrapper.cl_salcobrand import main as salcobrand
    from scrapper.cl_ahumada import main as ahumada
    from scrapper.pa_arrocha import main as arrocha
    from scrapper.pa_panamfarma import main as panamfarma
    from scrapper.pa_julios import main as julios
    from scrapper.mx_fesa import main as fesa
    from scrapper.pe_inkafarma import main as inkafarma
    from scrapper.pe_boticasperu import main as boticasperu
    from scrapper.uy_farmashop import main as farmashop
    from scrapper.uy_pigalle import main as pigalle
    from scrapper.uy_farmacity import main as farmacity_uy
    from scrapper.uy_antartida import main as antartida
    from scrapper.uy_goes import main as goes
    from scrapper.sv_siman import main as siman
    from scrapper.sv_sannicolas import main as sv_sannicolas
    from scrapper.ec_pharmacys import main as ec_pharmacys
    from scrapper.ec_cruzazul import main as ec_cruzazul
    from scrapper.ec_fybeca import main as ec_fybeca
    from scrapper.hn_siman import main as hn_siman
    from scrapper.hn_kielsa import main as hn_kielsa
    from scrapper.hn_fahorro import main as hn_fahorro
    from scrapper.hn_mifarmacia import main as hn_mifarmacia
    from scrapper.gt_siman import main as gt_siman
    from scrapper.gt_batres import main as gt_batres
    from scrapper.gt_galeno import main as gt_galeno
    from scrapper.ni_siman import main as ni_siman
    from scrapper.ni_kielsa import main as ni_kielsa
    from scrapper.ni_fahorro import main as ni_fahorro
    from scrapper.cr_siman import main as cr_siman
    from scrapper.cr_kolbi import main as cr_kolbi
    from scrapper.cr_fischel import main as cr_fischel
    from scrapper.py_puntofarma import main as py_puntofarma
    from scrapper.py_prosalud import main as py_prosalud
    from scrapper.ve_saas import main as ve_saas
    from scrapper.gy_pharmax import main as gy_pharmax
    from scrapper.gy_poonai import main as gy_poonai
    from scrapper.tt_trinipharma import main as tt_trinipharma
    from scrapper.bo_fsa import main as bo_fsa
    from scrapper.bo_farmacorp import main as bo_farmacorp
    from scrapper.ve_locatel import main as ve_locatel
    from scrapper.pe_universal import main as pe_universal
    from scrapper.gt_meykos import main as gt_meykos
    from scrapper.gt_cruzverde import main as gt_cruzverde
    from scrapper.sv_elfarmaceutico import main as sv_elfarmaceutico
    from scrapper.cr_farmavalue import main as cr_farmavalue
    from scrapper.gt_farmavalue import main as gt_farmavalue
    from scrapper.sv_farmavalue import main as sv_farmavalue
    from scrapper.py_biggie import main as py_biggie
    from scrapper.pa_farmavalue import main as pa_farmavalue
    from scrapper.hn_farmavalue import main as hn_farmavalue
    from scrapper.ni_farmavalue import main as ni_farmavalue
    from scrapper.cl_farmavalue import main as cl_farmavalue
    from scrapper.mx_farmavalue import main as mx_farmavalue
    from scrapper.tt_cva import main as tt_cva

    pasos: list[tuple[str, Any]] = [
        ("farmavalue", farmavalue),
        ("carol", carol),
        ("qualipharma", qualipharma),
        ("paguemenos", paguemenos),
        ("drogasil", drogasil),
        ("drogaraia", drogaraia),
        ("panvel", panvel),
        ("macrofarmacias", macrofarmacias),
        ("similares", similares),
        ("fahorro", fahorro),
        ("sanpablo", sanpablo),
        ("locatel", locatel),
        ("farmatodo", farmatodo),
        ("cruzverde", cruzverde),
        ("larebaja", larebaja),
        ("cafam", cafam),
        ("carulla", carulla),
        ("farmacity", farmacity),
        ("alfabeta", alfabeta),
        ("salcobrand", salcobrand),
        ("ahumada", ahumada),
        ("arrocha", arrocha),
        ("panamfarma", panamfarma),
        ("julios", julios),
        ("fesa", fesa),
        ("inkafarma", inkafarma),
        ("boticasperu", boticasperu),
        ("farmashop", farmashop),
        ("pigalle", pigalle),
        ("farmacity_uy", farmacity_uy),
        ("antartida", antartida),
        ("goes", goes),
        ("siman", siman),
        ("sv_sannicolas", sv_sannicolas),
        ("ec_pharmacys", ec_pharmacys),
        ("ec_cruzazul", ec_cruzazul),
        ("ec_fybeca", ec_fybeca),
        ("hn_siman", hn_siman),
        ("hn_kielsa", hn_kielsa),
        ("hn_fahorro", hn_fahorro),
        ("hn_mifarmacia", hn_mifarmacia),
        ("gt_siman", gt_siman),
        ("gt_batres", gt_batres),
        ("gt_galeno", gt_galeno),
        ("ni_siman", ni_siman),
        ("ni_kielsa", ni_kielsa),
        ("ni_fahorro", ni_fahorro),
        ("cr_siman", cr_siman),
        ("cr_kolbi", cr_kolbi),
        ("cr_fischel", cr_fischel),
        ("py_puntofarma", py_puntofarma),
        ("py_prosalud", py_prosalud),
        ("ve_saas", ve_saas),
        ("gy_pharmax", gy_pharmax),
        ("gy_poonai", gy_poonai),
        ("tt_trinipharma", tt_trinipharma),
        ("bo_fsa", bo_fsa),
        ("bo_farmacorp", bo_farmacorp),
        ("ve_locatel", ve_locatel),
        ("pe_universal", pe_universal),
        ("gt_meykos", gt_meykos),
        ("gt_cruzverde", gt_cruzverde),
        ("sv_elfarmaceutico", sv_elfarmaceutico),
        ("cr_farmavalue", cr_farmavalue),
        ("gt_farmavalue", gt_farmavalue),
        ("sv_farmavalue", sv_farmavalue),
        ("py_biggie", py_biggie),
        ("pa_farmavalue", pa_farmavalue),
        ("hn_farmavalue", hn_farmavalue),
        ("ni_farmavalue", ni_farmavalue),
        ("cl_farmavalue", cl_farmavalue),
        ("mx_farmavalue", mx_farmavalue),
        ("tt_cva", tt_cva),
    ]

    from scrapper.repositorio_cron_log import finalizar_corrida, iniciar_corrida

    flags = _flags_scraper()
    corrida_id = iniciar_corrida(argv=flags, mensaje="Cron diario · scrapers principales")
    print(f"CORRIDA_ID={corrida_id}")
    orden = 0
    hubo_error = False
    for fuente_id, fn in pasos:
        orden += 1
        ok = _ejecutar_y_loguear(corrida_id, orden, fuente_id, fn)
        if not ok:
            hubo_error = True
            # Seguimos con el resto para dejar log completo de la madrugada.

    orden += 1
    _ejecutar_y_loguear(corrida_id, orden, "alertas_patentes", _correr_alertas_patentes)
    orden += 1
    _ejecutar_y_loguear(corrida_id, orden, "alertas_precios", _correr_alertas_precios)

    # Si viene --sin-hidalgos, la corrida queda abierta para append de Hidalgos.
    if "--sin-hidalgos" in sys.argv and "--con-hidalgos" not in sys.argv:
        finalizar_corrida(
            corrida_id,
            estado="parcial",
            mensaje="Scrapers principales listos; pendiente Hidalgos",
        )
        return 1 if hubo_error else 0

    resumen = finalizar_corrida(
        corrida_id,
        estado="error" if hubo_error else "done",
        mensaje="Cron scrapers finalizado",
    )
    print(
        "Cron log:",
        f"ok={resumen.get('total_ok')} cache={resumen.get('total_cache')} "
        f"warn={resumen.get('total_warn')} error={resumen.get('total_error')}",
    )
    return 1 if hubo_error else 0


def _meta_fuente(fuente_id: str) -> dict[str, Any]:
    try:
        from scrapper.jobs_cola import FUENTES

        return dict(FUENTES.get(fuente_id) or {})
    except Exception:
        return {}


def _clasificar_salida(exit_code: int, texto: str) -> tuple[str, str, int | None]:
    """Devuelve (estado, mensaje_corto, filas_merge)."""
    low = (texto or "").lower()
    filas = None
    m = re.search(r"MERGE\s+(\d+)\s+filas", texto or "", re.I)
    if m:
        filas = int(m.group(1))
    if exit_code:
        msg = "Falló el scraper"
        for line in reversed((texto or "").splitlines()):
            s = line.strip()
            if s:
                msg = s[:240]
                break
        return "error", msg, filas
    if any(
        x in low
        for x in (
            "sigo con caché",
            "sigo con cache",
            "caché local",
            "cache local",
            "red no disponible",
            "bloqueado http",
            "http 403",
            "akamai",
        )
    ):
        return "cache", "Usó caché / red bloqueada", filas
    if filas == 0:
        return "warn", "Corrió pero MERGE 0 filas", filas
    return "ok", "OK", filas


def _ejecutar_y_loguear(corrida_id: int, orden: int, fuente_id: str, fn: Any) -> bool:
    """Ejecuta un paso, lo persiste en cron_log y refleja en cola de jobs si aplica."""
    import contextlib
    import io
    from datetime import datetime

    from scrapper.repositorio_cron_log import registrar_paso

    meta = _meta_fuente(fuente_id)
    nombre = meta.get("nombre") or fuente_id
    script = meta.get("script")
    print("=" * 64)
    print(f" [{orden}] {nombre} ({fuente_id})")
    print("=" * 64)

    buf = io.StringIO()
    t0 = datetime.now()
    exit_code = 0
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = fn()
        if isinstance(rc, int):
            exit_code = rc
        elif rc is not None and rc is not True:
            exit_code = 1
    except Exception as exc:
        exit_code = 1
        buf.write(f"\nEXCEPCIÓN: {exc}\n")
    t1 = datetime.now()
    out = buf.getvalue()
    if out:
        # Mantener el log de archivo/cron legible en stdout real.
        sys.stdout.write(out)
        if not out.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()

    estado, mensaje, filas = _clasificar_salida(exit_code, out)
    detalle_tail = "\n".join((out or "").splitlines()[-80:])
    registrar_paso(
        corrida_id,
        orden=orden,
        fuente_id=fuente_id,
        nombre=nombre,
        script=script,
        pais=meta.get("pais"),
        farmacia=meta.get("farmacia"),
        inicio=t0,
        fin=t1,
        estado=estado,
        exit_code=exit_code,
        filas_merge=filas,
        mensaje=mensaje,
        detalle=detalle_tail,
    )
    try:
        from scrapper.jobs_cola import registrar_resultado_cron

        registrar_resultado_cron(
            fuente_id,
            ok=(estado != "error"),
            exit_code=exit_code,
            mensaje=f"[cron] {mensaje}" + (f" · MERGE {filas}" if filas is not None else ""),
            estado_extra=estado,
        )
    except Exception as exc:
        print(f"  AVISO: no se pudo reflejar job UI para {fuente_id}: {exc}")

    print(f"  → estado={estado} exit={exit_code} filas={filas} ({mensaje})")
    return estado != "error"


def _correr_alertas_patentes() -> int:
    """Detecta vencimientos FDA y refresca dias_restantes en tabla. No falla el cron."""
    print("=" * 64)
    print(" Alertas de patentes FDA (detectar + conteo diario de días)")
    print("=" * 64)
    try:
        from scrapper.alertas_patentes import detectar_todas

        r = detectar_todas()
        print(r.get("mensaje") or r)
        print(f"  dias_actualizados={r.get('dias_actualizados', 0)}")
        return 0 if r.get("ok") else 1
    except Exception as exc:
        print(f"  AVISO alertas patentes: {exc}")
        return 0


def _correr_alertas_precios() -> int:
    """Evalúa criterios de variación de precio. No falla el cron."""
    print("=" * 64)
    print(" Alertas de precios (criterios activos)")
    print("=" * 64)
    try:
        from scrapper.alertas_precios import detectar_todas

        r = detectar_todas()
        print(r.get("mensaje") or r)
        return 0 if r.get("ok") else 1
    except Exception as exc:
        print(f"  AVISO alertas precios: {exc}")
        return 0


def _hidalgos_playwright() -> int | None:
    """Corre Hidalgos en el proceso actual si hay Playwright. None = no disponible."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return None
    from scrapper.rd_hidalgos import main as hidalgos

    print("=" * 64)
    print(" Los Hidalgos (Playwright, al final)")
    print("=" * 64)
    return hidalgos()


def _hidalgos_via_docker(flags: list[str]) -> int:
    env_file = ROOT / ".env"
    cmd = [
        "docker",
        "run",
        "--rm",
        "--memory=3g",
        "-v",
        f"{ROOT}:/tmp/mac",
        "-w",
        "/tmp/mac",
        "-e",
        "PYTHONPATH=/tmp/mac",
    ]
    if env_file.is_file():
        cmd.extend(["--env-file", str(env_file)])
    cmd.extend([IMG_HIDALGOS, "python", "scrapper/rd_hidalgos.py", *flags])
    print("=" * 64)
    print(f" Los Hidalgos vía Docker ({IMG_HIDALGOS})")
    print("=" * 64)
    print(" ", " ".join(cmd))
    return subprocess.call(cmd)


def _correr_hidalgos(flags: list[str], *, obligatorio: bool) -> int:
    from datetime import datetime

    from scrapper.repositorio_cron_log import (
        finalizar_corrida,
        listar_corridas,
        listar_pasos,
        registrar_paso,
    )

    corrida_id = None
    for c in listar_corridas(limite=5):
        if str(c.get("estado") or "") in ("parcial", "running"):
            corrida_id = int(c["id"])
            break

    t0 = datetime.now()
    rc = _hidalgos_playwright()
    if rc is None:
        if shutil.which("docker"):
            rc = _hidalgos_via_docker(flags)
        else:
            msg = (
                "Hidalgos omitido: no hay Playwright en este entorno ni cliente docker. "
                "Usa: bash scrapper/run_cron_diario.sh --fresh"
            )
            if obligatorio:
                print(msg, file=sys.stderr)
                if corrida_id:
                    registrar_paso(
                        corrida_id,
                        orden=(len(listar_pasos(corrida_id)) + 1),
                        fuente_id="hidalgos",
                        nombre="Los Hidalgos",
                        script="scrapper/rd_hidalgos.py",
                        pais="República Dominicana",
                        farmacia="Los Hidalgos",
                        inicio=t0,
                        fin=datetime.now(),
                        estado="skip",
                        exit_code=None,
                        mensaje=msg,
                    )
                    finalizar_corrida(corrida_id, estado="done_parcial", mensaje=msg)
                return 1
            print(msg)
            if corrida_id:
                registrar_paso(
                    corrida_id,
                    orden=(len(listar_pasos(corrida_id)) + 1),
                    fuente_id="hidalgos",
                    nombre="Los Hidalgos",
                    script="scrapper/rd_hidalgos.py",
                    pais="República Dominicana",
                    farmacia="Los Hidalgos",
                    inicio=t0,
                    fin=datetime.now(),
                    estado="skip",
                    mensaje=msg,
                )
                finalizar_corrida(corrida_id, estado="done_parcial", mensaje="Sin Hidalgos")
            return 0

    t1 = datetime.now()
    estado = "ok" if not rc else "error"
    mensaje = "OK" if not rc else f"Hidalgos exit={rc}"
    if corrida_id:
        registrar_paso(
            corrida_id,
            orden=(len(listar_pasos(corrida_id)) + 1),
            fuente_id="hidalgos",
            nombre="Los Hidalgos",
            script="scrapper/rd_hidalgos.py",
            pais="República Dominicana",
            farmacia="Los Hidalgos",
            inicio=t0,
            fin=t1,
            estado=estado,
            exit_code=int(rc or 0),
            mensaje=mensaje,
        )
        finalizar_corrida(
            corrida_id,
            estado="error" if rc else "done",
            mensaje="Cron diario completo (con Hidalgos)",
        )
    try:
        from scrapper.jobs_cola import registrar_resultado_cron

        registrar_resultado_cron(
            "hidalgos",
            ok=not rc,
            exit_code=int(rc or 0),
            mensaje=f"[cron] {mensaje}",
        )
    except Exception:
        pass
    return int(rc or 0)


def _orquestar_desde_host(flags: list[str]) -> int:
    """En el host: primero contenedor principal, luego imagen Playwright."""
    cmd_main = [
        "docker",
        "exec",
        "-w",
        "/app",
        IMG_MAIN,
        "python",
        "scrapper/cron_diario.py",
        "--sin-hidalgos",
        *flags,
    ]
    print("=" * 64)
    print(f" [1/2] Scrapers principales ({IMG_MAIN})")
    print("=" * 64)
    print(" ", " ".join(cmd_main))
    rc_main = subprocess.call(cmd_main)
    # Hidalgos siempre se intenta; el log queda atado a la corrida parcial.
    rc_h = _hidalgos_via_docker(flags)
    # Registrar hidalgos en la corrida abierta dentro del contenedor principal (tiene DB).
    subprocess.call(
        [
            "docker",
            "exec",
            "-w",
            "/app",
            IMG_MAIN,
            "python",
            "scrapper/cron_diario.py",
            "--registrar-hidalgos",
            str(int(rc_h or 0)),
        ]
    )
    return rc_main or rc_h


def _registrar_hidalgos_exit(exit_code: int) -> int:
    """Cierra la corrida parcial del día con el resultado de Hidalgos (post docker run)."""
    from datetime import datetime

    from scrapper.repositorio_cron_log import finalizar_corrida, listar_corridas, listar_pasos, registrar_paso

    corrida_id = None
    for c in listar_corridas(limite=5):
        if str(c.get("estado") or "") in ("parcial", "running"):
            corrida_id = int(c["id"])
            break
    if not corrida_id:
        print("AVISO: no hay corrida parcial abierta para registrar Hidalgos")
        return int(exit_code or 0)

    ahora = datetime.now()
    estado = "ok" if not exit_code else "error"
    mensaje = "OK" if not exit_code else f"Hidalgos exit={exit_code}"
    registrar_paso(
        corrida_id,
        orden=(len(listar_pasos(corrida_id)) + 1),
        fuente_id="hidalgos",
        nombre="Los Hidalgos",
        script="scrapper/rd_hidalgos.py",
        pais="República Dominicana",
        farmacia="Los Hidalgos",
        inicio=ahora,
        fin=ahora,
        estado=estado,
        exit_code=int(exit_code or 0),
        mensaje=mensaje,
    )
    finalizar_corrida(
        corrida_id,
        estado="error" if exit_code else "done",
        mensaje="Cron diario completo (con Hidalgos)",
    )
    try:
        from scrapper.jobs_cola import registrar_resultado_cron

        registrar_resultado_cron(
            "hidalgos",
            ok=not exit_code,
            exit_code=int(exit_code or 0),
            mensaje=f"[cron] {mensaje}",
        )
    except Exception:
        pass
    print(f"Hidalgos registrado en corrida {corrida_id}: {estado}")
    return int(exit_code or 0)


def main() -> int:
    flags = _flags_scraper()
    sin_hidalgos = "--sin-hidalgos" in sys.argv
    con_hidalgos = "--con-hidalgos" in sys.argv

    if "--registrar-hidalgos" in sys.argv:
        # Uso: python scrapper/cron_diario.py --registrar-hidalgos <exit_code>
        try:
            idx = sys.argv.index("--registrar-hidalgos")
            code = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 1
        except Exception:
            code = 1
        return _registrar_hidalgos_exit(code)

    # Desde el host con docker: orquesta ambos contenedores en secuencia.
    if not _en_contenedor() and shutil.which("docker") and not sin_hidalgos:
        return _orquestar_desde_host(flags)

    rc = _correr_scrapers()
    if sin_hidalgos and not con_hidalgos:
        return rc

    # Al final, siempre que no se haya pedido omitir.
    return _correr_hidalgos(flags, obligatorio=con_hidalgos)


if __name__ == "__main__":
    raise SystemExit(main())
