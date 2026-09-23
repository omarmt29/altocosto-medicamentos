"""
Scraper RD · Farmacias Los Hidalgos → P_aguila.medicamentos_altos_costos_america

Busca cada ítem DAMAC/FOMAC en la tienda (WooCommerce + Cloudflare).
Cada búsqueda va en un contexto nuevo para pasar el challenge.

Uso:
    python scrapper/rd_hidalgos.py
    python scrapper/rd_hidalgos.py --fresh

Requiere Playwright (está en el contenedor extraccion-medicamentos).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.matching import clasificar, medicamentos_que_pegan  # noqa: E402
from scrapper.ficha import parse_ficha  # noqa: E402
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos  # noqa: E402

CACHE = ROOT / "cache"
HITS_CACHE = CACHE / "hidalgos_hits.json"
BASE = "https://farmaciasloshidalgos.com.do"
PAIS = "República Dominicana"
FARMACIA = "Los Hidalgos"
MONEDA = "DOP"


def query_med(med: dict[str, Any]) -> str:
    aliases = [str(a).strip() for a in med["aliases"] if str(a).strip()]
    marcas = [a for a in aliases if " " not in a and len(a) >= 5]
    if marcas:
        return marcas[0]
    return aliases[0] if aliases else str(med["nombre"])


def parse_precio(textos: list[str] | None) -> float | None:
    nums: list[float] = []
    for t in textos or []:
        s = str(t).upper().replace("RD$", "").replace("$", "").replace(" ", "")
        s = s.replace(",", "")
        m = re.search(r"(\d+(?:\.\d+)?)", s)
        if not m:
            continue
        try:
            n = float(m.group(1))
        except ValueError:
            continue
        if n > 0:
            nums.append(n)
    return nums[-1] if nums else None


def slug_id(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1] if path else url


def extraer_listado(page) -> list[dict[str, Any]]:
    return page.evaluate(
        """() => [...document.querySelectorAll('li.product')].map(el => {
          const a = el.querySelector('a[href*="/producto/"]');
          const nameEl = el.querySelector('.woocommerce-loop-product__title, h2, h3');
          const name = (nameEl && nameEl.innerText.trim())
            || (a && a.getAttribute('aria-label'))
            || '';
          const prices = (el.innerText.match(/RD\\$[\\d.,]+/g) || []);
          const pid = (el.className.match(/post-(\\d+)/) || [])[1] || '';
          const stock = /outofstock/i.test(el.className) ? 'Agotado' : 'Disponible';
          return {nombre: name, href: a && a.href, prices, pid, stock, clases: el.className};
        })"""
    )


def esperar_cf(page, timeout_ms: int = 25000) -> str:
    t0 = time.time()
    while (time.time() - t0) * 1000 < timeout_ms:
        title = page.title()
        if title not in ("Just a moment...", "Un momento…", ""):
            return title
        page.wait_for_timeout(700)
    return page.title()


def _cargar_cache() -> list[dict[str, Any]]:
    if HITS_CACHE.exists() and HITS_CACHE.stat().st_size > 10:
        return json.loads(HITS_CACHE.read_text(encoding="utf-8"))
    return []


def _guardar_cache(hits: list[dict[str, Any]]) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    HITS_CACHE.write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")


def buscar_vivo(queries: list[str], hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    vistos_url = {h.get("url") for h in hits if h.get("url")}
    hechas = {str(h.get("query") or "").lower() for h in hits}
    pendientes = [q for q in queries if q.lower() not in hechas]
    limite = int(os.getenv("HIDALGOS_LIMIT") or "0")
    if limite > 0:
        pendientes = pendientes[:limite]
    print(f"Búsquedas Hidalgos: {len(pendientes)} pendientes / {len(queries)} total")
    if not pendientes:
        return hits

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Los Hidalgos necesita Playwright (Cloudflare). "
            "Ejecutar en el contenedor extraccion-medicamentos."
        ) from exc

    with sync_playwright() as p:
        for i, q in enumerate(pendientes, start=1):
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                ),
                locale="es-DO",
                viewport={"width": 1200, "height": 800},
            )
            page = ctx.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            url = f"{BASE}/?s={quote(q)}&post_type=product&type_aws=true"
            n_ok = 0
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                esperar_cf(page)
                items = extraer_listado(page)
            except Exception as exc:
                print(f"  [{i}/{len(pendientes)}] {q}: error {exc}")
                browser.close()
                continue
            for it in items:
                href = (it.get("href") or "").split("?")[0]
                if not href or href in vistos_url:
                    continue
                nombre = (it.get("nombre") or "").strip() or slug_id(href).replace("-", " ")
                vistos_url.add(href)
                hits.append(
                    {
                        "nombre": nombre,
                        "url": href,
                        "precio": parse_precio(it.get("prices") or []),
                        "precios_raw": it.get("prices") or [],
                        "id_producto": str(it.get("pid") or slug_id(href)),
                        "disponibilidad": it.get("stock") or "Disponible",
                        "query": q,
                    }
                )
                n_ok += 1
            if n_ok == 0:
                hits.append({"query": q, "url": None, "nombre": "", "precio": None})
            print(f"  [{i}/{len(pendientes)}] {q}: {n_ok} producto(s)")
            browser.close()
            _guardar_cache(hits)
            time.sleep(0.2)
    return hits


def filas_para_db(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fecha_dato = datetime.now().date().isoformat()
    out: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    for h in hits:
        nombre = h.get("nombre") or ""
        url = h.get("url") or ""
        if not url:
            continue
        texto = f"{nombre} {url}"
        hits_med = medicamentos_que_pegan(texto)
        if not hits_med:
            continue
        fake = {
            "nombre": nombre,
            "principios_activos": [],
            "principios_activos_con_dosaje": [],
            "tipo_presentacion": nombre,
            "palabras_clave": url,
        }
        for med0 in hits_med:
            med, calidad, obs = clasificar(med0, fake)
            n_lista = int(med["n"])
            pid = str(h.get("id_producto") or slug_id(url))
            clave = (pid, n_lista)
            if clave in vistos:
                continue
            vistos.add(clave)
            extra = obs
            detalle = bool(re.search(r"det\b|\*\*\*det", nombre, re.I) or url.rstrip("/").endswith("det"))
            if detalle:
                nota = "Precio al detalle (unidad), no caja"
                extra = f"{obs} · {nota}" if obs else nota
            ficha = parse_ficha(nombre, med, detalle=detalle)
            nota_ficha = ficha.get("observacion_ficha")
            if nota_ficha:
                extra = f"{extra} · {nota_ficha}" if extra else nota_ficha
            out.append(
                {
                    "pais": PAIS,
                    "farmacia": FARMACIA,
                    "fuente_url": url[:500],
                    "id_producto_farmacia": pid[:80],
                    "sku": pid[:80],
                    "n_lista": n_lista,
                    "medicamento_lista": str(med["nombre"]),
                    "programa": str(med["programa"]),
                    "nombre_comercial": nombre[:500],
                    "principio_activo": ficha["principio_activo"],
                    "concentracion": ficha["concentracion"],
                    "presentacion": ficha["presentacion"],
                    "laboratorio": ficha["laboratorio"],
                    "precio": h.get("precio"),
                    "moneda": MONEDA,
                    "disponibilidad": h.get("disponibilidad") or "Disponible",
                    "calidad": calidad,
                    "observacion": extra,
                    "fecha_publicacion": None,
                    "fecha_dato": fecha_dato,
                }
            )
    return out


def main() -> int:
    forzar = "--fresh" in sys.argv
    print("=" * 64)
    print(" RD Los Hidalgos → medicamentos_altos_costos_america")
    print("=" * 64)
    CACHE.mkdir(parents=True, exist_ok=True)
    solo_fomac = "--fomac" in sys.argv
    queries: list[str] = []
    vistos_q: set[str] = set()
    trabajo = MEDICAMENTOS
    if solo_fomac:
        trabajo = [m for m in MEDICAMENTOS if "FOMAC" in str(m["programa"])]
        print(f"Solo FOMAC: {len(trabajo)} moléculas")
    for med in trabajo:
        for raw in ([query_med(med)] if not solo_fomac else list(med["aliases"])):
            q = str(raw).strip().lower()
            if len(q) < 4 or q in vistos_q:
                continue
            vistos_q.add(q)
            queries.append(q)
    extras = [
        "lectrum", "zoladex", "forteo", "myfortic", "esbriet", "gamunex", "privigen", "flebogamma",
        "humira", "amgevita", "enbrel", "simponi", "remicade", "ibrance", "keytruda",
        "sandostatin", "blincyto", "evrysdi", "oncaspar", "neulasta", "aloxi", "onicit",
        "remsima", "hyrimoz", "brenzys",
        "neoral", "sandimmun", "avastin", "valcyte", "revlimid", "sutent", "faslodex",
        "perjeta", "phesgo", "simulect", "erbitux", "exjade", "jadenu", "advate",
        "benefix", "xyntha", "lynparza", "stivarga", "tecentriq", "vidaza", "darzalex",
        "epclusa", "harvoni", "zytiga", "glamatir", "govolyx", "eligard", "yuflyma",
        "vegzelma", "zarzio", "octagam", "truxima", "rixathon", "herzuma", "trazimera",
        "selarsdi", "seveclo", "nepexto", "octanate", "nuwiq", "ixifi", "pirfone",
        "hafyera", "zactidyn", "canabosen", "capcitox", "gilenya", "mavenclad",
        "pulmozyme", "hemlibra", "naglazyme", "tremfya", "cerezyme", "rebif", "avonex",
        "betaferon", "ocrevus", "aubagio", "xeljanz", "fabrazyme", "adempas", "tasigna",
        "imbruvica", "glivec", "cellcept", "kisqali", "tagrisso", "xtandi", "revolade",
        "afinitor", "certican", "genotropin", "norditropin", "saizen", "actemra",
        "stelara", "herceptin", "mabthera", "xolair", "invega", "femara", "casodex",
        "velcade", "tykerb", "gazyva",
    ]
    if not solo_fomac:
        for q in extras:
            if q not in vistos_q:
                vistos_q.add(q)
                queries.append(q)

    hits = [] if forzar else _cargar_cache()
    if forzar:
        hits = []
        if HITS_CACHE.exists():
            HITS_CACHE.unlink()
    if hits:
        print(f"Reanudando caché Hidalgos: {len(hits)} productos")
    hits = buscar_vivo(queries, hits)
    _guardar_cache(hits)
    print(f"Productos Hidalgos únicos: {len(hits)}")
    filas = filas_para_db(hits)
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    print(f"Coincidencias lista: {len(filas)}  (ok={ok}, revisar={len(filas) - ok})")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    if solo_fomac:
        borrados = 0
    else:
        borrados = purgar_obsoletos(
            PAIS,
            FARMACIA,
            [(f["id_producto_farmacia"], f["n_lista"]) for f in filas],
        )
    print(
        f"MERGE {res['upserts']} filas · obsoletos: {borrados} · "
        f"RD Hidalgos: {contar(PAIS, FARMACIA)} · total tabla: {contar()}"
    )
    by_med: dict[str, int] = {}
    for f in filas:
        by_med[f["medicamento_lista"]] = by_med.get(f["medicamento_lista"], 0) + 1
    for nombre, n in sorted(by_med.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {n:2d}  {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
