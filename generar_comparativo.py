"""
PVP de farmacias de America (6 paises) para DAMAC/FOMAC.

Cada pais usa la busqueda publica de UNA farmacia, el mismo JSON/HTML
que muestra su tienda online:

  1. Republica Dominicana  - Farmacia 3C (catalogo local / API producto)
  2. Argentina             - Farmacity (VTEX)
  3. Brasil                - Pague Menos, Drogasil, Droga Raia, Panvel (VTEX)
  4. Colombia              - Locatel (VTEX)
  5. Peru                  - Inkafarma (Algolia de su buscador web)
  6. Chile                 - Farmacias Ahumada (busqueda Demandware)

Uso:
    cd medicamentos_alto_costo
    python generar_comparativo.py
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from datetime import datetime
from html import unescape
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd
import requests
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows

from lista import MEDICAMENTOS, prioridad
from scrapper.estructura_producto import parse_concentracion, parse_presentacion
from scrapper.equivalencia import clave_medicina_fila, clave_presentacion_fila, precio_por_unidad_usd
from scrapper.repositorio import listar_filas

CARPETA = Path(__file__).resolve().parent
CACHE = CARPETA / "cache"
SALIDA = CARPETA / "salida"
CATALOGO_RD = CARPETA.parent / "catalogo" / "productos.json"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
TIMEOUT = 25
PAUSA = 0.25

RD_API = "https://fd-app.3c.group/api/v1/producto"
FARMACITY = "https://www.farmacity.com"
PAGUE_MENOS = "https://www.paguemenos.com.br"
DROGASIL = "https://www.drogasil.com.br"
DROGARAIA = "https://www.drogaraia.com.br"
PANVEL = "https://www.panvel.com"
LOCATEL = "https://www.locatelcolombia.com"
INKAFARMA = "https://inkafarma.pe"
AHUMADA = "https://www.farmaciasahumada.cl"
INKAFARMA_ALGOLIA_APP = "15W622LAQ4"
INKAFARMA_ALGOLIA_KEY = "eb3261874e9b933efab019b04acff834"
INKAFARMA_ALGOLIA_INDEX = "products"
FX_URL = "https://open.er-api.com/v6/latest/USD"
BCRD_PORTAL = "https://www.bancentral.gov.do/"
AR_DOLAR = "https://dolarapi.com/v1/dolares/oficial"
AR_BCRA = "https://www.bcra.gob.ar/"
BR_PTAX = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
)
BR_BCB = "https://www.bcb.gov.br/"
CO_TRM = "https://www.datos.gov.co/resource/32sa-8pi3.json"
CO_BANREP = "https://www.banrep.gov.co/es/estadisticas/trm"
PE_BCRP = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04646PD/json"
PE_BCRP_PORTAL = "https://www.bcrp.gob.pe/"
CL_DOLAR = "https://mindicador.cl/api/dolar"
CL_BCCH = "https://www.bcentral.cl/"

PAISES = [
    "República Dominicana",
    "Argentina",
    "Brasil",
    "Colombia",
    "Perú",
    "Chile",
    "México",
    "Panamá",
    "Uruguay",
    "El Salvador",
    "Ecuador",
    "Honduras",
    "Guatemala",
    "Nicaragua",
    "Costa Rica",
]

EXCLUDES: dict[str, list[str]] = {
    "Filgrastim": ["pegfilgrastim"],
    "Trastuzumab": ["pertuzumab", "phesgo"],
    "Pertuzumab": ["phesgo", "trastuzumab"],
    "Interferón beta 1A": ["beta-1b", "beta 1b", "beta 1-b", "1b"],
    "Interferón beta 1B": ["beta-1a", "beta 1a", "beta 1-a"],
    "Micofenolato mofetilo": ["sodium", "sodico", "myfortic"],
    "Micofenolato sódico": ["mofetil", "mofetilo", "cellcept"],
    "Factor IX": ["factor viii", "factor 8", "octocog"],
    "Factor de coagulación VIII": ["factor ix", "factor 9", "nonacog"],
    "Pegfilgrastim": [],
}

REQUIERE: dict[str, list[str]] = {
    "Pertuzumab/Trastuzumab": ["phesgo"],
    "Sofosbuvir/Velpatasvir": ["epclusa"],
}

ENCABEZADO = PatternFill("solid", fgColor="0A2540")
FOMAC_FILL = PatternFill("solid", fgColor="D6E4F5")
FOMAC_MIX = PatternFill("solid", fgColor="EAF1F8")
FUENTE = Font(name="Calibri", size=10)
FUENTE_H = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
BORDE = Border(
    left=Side(style="thin", color="D0D7DE"),
    right=Side(style="thin", color="D0D7DE"),
    top=Side(style="thin", color="D0D7DE"),
    bottom=Side(style="thin", color="D0D7DE"),
)


def norm(texto: Any) -> str:
    s = "" if texto is None else str(texto)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def fmt_num(n: float) -> str:
    if abs(n - round(n)) < 1e-9:
        return str(int(round(n)))
    return f"{n:.4f}".rstrip("0").rstrip(".")


def parsear_dosis(*textos: Any) -> dict[str, Any]:
    """Lee mg, ml y unidades del envase desde el nombre comercial."""
    t = " ".join(str(x or "") for x in textos)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    t = t.lower().replace(",", ".")
    mg = ml = mcg = ui = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*mg\s*/\s*(\d+(?:\.\d+)?)\s*ml", t)
    if m:
        mg, ml = float(m.group(1)), float(m.group(2))
    else:
        m = re.search(r"(\d+(?:\.\d+)?)\s*mcg\b", t)
        if m:
            mcg = float(m.group(1))
        m = re.search(r"(\d+(?:\.\d+)?)\s*mg\b", t)
        if m:
            mg = float(m.group(1))
        m = re.search(r"(\d+(?:\.\d+)?)\s*ml\b", t)
        if m:
            ml = float(m.group(1))
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:ui|iu)\b", t)
        if m:
            ui = float(m.group(1))
    pres = parse_presentacion(" ".join(str(x or "") for x in textos))
    pack = None
    if pres.get("cantidad_presentacion"):
        try:
            pack = int(float(str(pres["cantidad_presentacion"])))
        except (TypeError, ValueError):
            pack = None
    partes: list[str] = []
    if mg is not None:
        partes.append(f"{fmt_num(mg)} mg")
    elif mcg is not None:
        partes.append(f"{fmt_num(mcg)} mcg")
    elif ui is not None:
        partes.append(f"{fmt_num(ui)} UI")
    if ml is not None:
        partes.append(f"{fmt_num(ml)} ml")
    conc = parse_concentracion(" ".join(str(x or "") for x in textos))
    return {
        "mg": mg,
        "ml": ml,
        "pack": pack,
        "clave": " / ".join(partes),
        "cantidad_concentracion": conc.get("cantidad_concentracion"),
        "unidad_concentracion": conc.get("unidad_concentracion"),
        "tipo_presentacion": pres.get("tipo_presentacion"),
        "cantidad_presentacion": pres.get("cantidad_presentacion"),
        "alcance_presentacion": pres.get("alcance_presentacion"),
    }


def coincide(haystack: str, med: dict[str, Any]) -> bool:
    h = norm(haystack)
    if not h:
        return False
    nombre = str(med["nombre"])
    for excl in EXCLUDES.get(nombre, []):
        if norm(excl) and norm(excl) in h:
            if nombre == "Interferón beta 1A" and "1b" in excl:
                if re.search(r"beta[\s-]*1[\s-]*b\b", h):
                    return False
                continue
            if nombre == "Interferón beta 1B" and "1a" in excl:
                if re.search(r"beta[\s-]*1[\s-]*a\b", h):
                    return False
                continue
            return False
    reqs = REQUIERE.get(nombre, [])
    if nombre == "Pertuzumab/Trastuzumab":
        return "phesgo" in h or ("pertuzumab" in h and "trastuzumab" in h)
    if nombre == "Sofosbuvir/Velpatasvir":
        return "epclusa" in h or ("sofosbuvir" in h and "velpatasvir" in h)
    if reqs:
        return any(norm(r) in h for r in reqs)
    for alias in med["aliases"]:
        a = norm(alias)
        if len(a) < 4:
            continue
        if re.search(rf"(^| ){re.escape(a)}( |$)", h):
            if nombre == "Filgrastim" and "pegfilgrastim" in h:
                continue
            return True
        if a.endswith("mab") or a.endswith("nib") or a.endswith("mib"):
            if re.search(rf"(^| ){re.escape(a)}e( |$)", h):
                return True
    return False


def a_float(valor: Any) -> float | None:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    if isinstance(valor, (int, float)):
        return float(valor) if float(valor) > 0 else None
    s = str(valor).strip()
    if not s or s in {".", "-", "NA", "N/A"}:
        return None
    s = s.replace("\xa0", "").replace(" ", "")
    if s.count(",") == 1 and s.count(".") >= 1:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(",") == 1 and s.count(".") == 0:
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")
    s = re.sub(r"[^0-9.\-]", "", s)
    try:
        n = float(s)
    except ValueError:
        return None
    return n if n > 0 else None


def clp(texto: str) -> float | None:
    s = re.sub(r"[^\d]", "", str(texto))
    if not s:
        return None
    n = float(s)
    return n if n > 0 else None


def aliases_busqueda(med: dict[str, Any]) -> list[str]:
    out = []
    for a in med["aliases"]:
        a = str(a).strip()
        if len(a) >= 5 and a.lower() not in {x.lower() for x in out}:
            out.append(a)
    return out[:3]


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "application/json, text/html;q=0.8",
        "Accept-Language": "es-419,es;q=0.9,pt-BR;q=0.8,en;q=0.7",
    })
    return s


def fecha_iso(path: Path) -> str:
    if path.exists():
        return datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
    return datetime.now().date().isoformat()


def fecha_catalogo_rd() -> str:
    meta = CARPETA.parent / "catalogo" / "ultima_actualizacion.json"
    if meta.exists():
        try:
            d = json.loads(meta.read_text(encoding="utf-8"))
            return str(d.get("fecha") or "")[:10] or fecha_iso(CATALOGO_RD)
        except (OSError, json.JSONDecodeError):
            pass
    return fecha_iso(CATALOGO_RD)


def cache_json(nombre: str, key: str, loader) -> tuple[Any, str]:
    carpeta = CACHE / "farmacias" / nombre
    carpeta.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-z0-9]+", "_", key.lower())[:80] or "q"
    path = carpeta / f"{safe}.json"
    if path.exists() and path.stat().st_size >= 2:
        return json.loads(path.read_text(encoding="utf-8")), fecha_iso(path)
    data = loader()
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data, datetime.now().date().isoformat()


def _er_api(s: requests.Session) -> dict[str, float]:
    r = s.get(FX_URL, timeout=60)
    r.raise_for_status()
    return {str(k).upper(): float(v) for k, v in r.json().get("rates", {}).items()}


def _tasa(valor: float, nombre: str, fecha: str, fuente: str, link: str) -> dict[str, Any]:
    return {
        "valor": float(valor),
        "nombre": nombre,
        "fecha": fecha,
        "fuente": fuente,
        "link": link,
    }


def tasas(s: requests.Session) -> dict[str, Any]:
    """Unidades de moneda local por 1 USD, según la cotización de cada país."""
    mercado: dict[str, float] = {}
    try:
        mercado = _er_api(s)
    except Exception:
        pass

    bcrd_compra = 58.4020
    bcrd_venta = 58.7482
    bcrd_fecha = "2026-08-12"
    try:
        home = s.get(BCRD_PORTAL, timeout=40)
        txt = home.text.replace(",", "")
        nums = re.findall(r"58\.\d{3,4}", txt)
        if len(nums) >= 2:
            bcrd_compra = float(nums[0])
            bcrd_venta = float(nums[1])
            bcrd_fecha = datetime.now().date().isoformat()
    except Exception:
        pass

    por_usd: dict[str, dict[str, Any]] = {
        "DOP": _tasa(bcrd_venta, "BCRD venta", bcrd_fecha, "Banco Central de la República Dominicana", BCRD_PORTAL),
    }

    try:
        r = s.get(AR_DOLAR, timeout=25)
        r.raise_for_status()
        d = r.json()
        por_usd["ARS"] = _tasa(
            float(d["venta"]),
            "BCRA / dólar oficial venta",
            str(d.get("fechaActualizacion") or "")[:10],
            "Banco Central de la República Argentina (oficial)",
            AR_BCRA,
        )
    except Exception:
        if mercado.get("ARS"):
            por_usd["ARS"] = _tasa(mercado["ARS"], "Reserva (mercado)", "", "open.er-api.com", FX_URL)

    try:
        d1 = datetime.now().date().replace(day=1).strftime("%m-%d-%Y")
        d2 = datetime.now().date().strftime("%m-%d-%Y")
        url = (
            f"{BR_PTAX}?@dataInicial='{d1}'&@dataFinalCotacao='{d2}'"
            "&$top=1&$orderby=dataHoraCotacao desc&$format=json"
        )
        r = s.get(url, timeout=30)
        r.raise_for_status()
        fila = (r.json().get("value") or [None])[0]
        if not fila:
            raise ValueError("PTAX vacío")
        por_usd["BRL"] = _tasa(
            float(fila["cotacaoVenda"]),
            "BCB PTAX venta",
            str(fila.get("dataHoraCotacao") or "")[:10],
            "Banco Central do Brasil — PTAX",
            BR_BCB,
        )
    except Exception:
        if mercado.get("BRL"):
            por_usd["BRL"] = _tasa(mercado["BRL"], "Reserva (mercado)", "", "open.er-api.com", FX_URL)

    try:
        r = s.get(f"{CO_TRM}?$limit=1&$order=vigenciadesde DESC", timeout=30)
        r.raise_for_status()
        fila = (r.json() or [None])[0]
        if not fila:
            raise ValueError("TRM vacío")
        por_usd["COP"] = _tasa(
            float(fila["valor"]),
            "TRM (peso por dólar)",
            str(fila.get("vigenciadesde") or "")[:10],
            "Banco de la República / Superintendencia Financiera — TRM",
            CO_BANREP,
        )
    except Exception:
        if mercado.get("COP"):
            por_usd["COP"] = _tasa(mercado["COP"], "Reserva (mercado)", "", "open.er-api.com", FX_URL)

    try:
        r = s.get(PE_BCRP, timeout=40)
        r.raise_for_status()
        elegido = None
        for periodo in reversed(r.json().get("periods") or []):
            raw = (periodo.get("values") or [None])[0]
            if raw in (None, "", "n.d.", "n.d"):
                continue
            elegido = (float(str(raw).replace(",", ".")), str(periodo.get("name") or ""))
            break
        if not elegido:
            raise ValueError("BCRP sin dato")
        por_usd["PEN"] = _tasa(
            elegido[0],
            "BCRP tipo de cambio venta",
            elegido[1],
            "Banco Central de Reserva del Perú — TC cierre venta",
            PE_BCRP_PORTAL,
        )
    except Exception:
        if mercado.get("PEN"):
            por_usd["PEN"] = _tasa(mercado["PEN"], "Reserva (mercado)", "", "open.er-api.com", FX_URL)

    try:
        r = s.get(CL_DOLAR, timeout=25)
        r.raise_for_status()
        serie = r.json().get("serie") or []
        if not serie:
            raise ValueError("mindicador vacío")
        por_usd["CLP"] = _tasa(
            float(serie[0]["valor"]),
            "Dólar observado BCCh",
            str(serie[0].get("fecha") or "")[:10],
            "Banco Central de Chile — dólar observado (mindicador.cl)",
            CL_BCCH,
        )
    except Exception:
        if mercado.get("CLP"):
            por_usd["CLP"] = _tasa(mercado["CLP"], "Reserva (mercado)", "", "open.er-api.com", FX_URL)

    try:
        from scrapper.fx import tasa_mxn

        mx = tasa_mxn(s)
        por_usd["MXN"] = _tasa(mx["valor"], mx["nombre"], mx["fecha"], mx["fuente"], mx["link"])
    except Exception:
        if mercado.get("MXN"):
            por_usd["MXN"] = _tasa(mercado["MXN"], "Reserva (mercado)", "", "open.er-api.com", FX_URL)

    for code in ("CRC", "HNL", "GTQ", "NIO", "UYU", "PAB", "PYG", "GYD", "TTD", "BOB", "VES", "CAD"):
        if code not in por_usd and mercado.get(code):
            por_usd[code] = _tasa(mercado[code], "Reserva (mercado)", "", "open.er-api.com", FX_URL)

    return {
        "por_usd": por_usd,
        "bcrd_compra": bcrd_compra,
        "bcrd_venta": bcrd_venta,
        "bcrd_fecha": bcrd_fecha,
        "bcrd_fuente": BCRD_PORTAL,
        "fx_fuente": FX_URL,
    }


def a_usd(monto: float, moneda: str, fx: dict[str, Any]) -> float | None:
    moneda = moneda.upper()
    if moneda == "USD":
        return monto
    info = (fx.get("por_usd") or {}).get(moneda)
    if not info or not info.get("valor"):
        return None
    return monto / float(info["valor"])


def a_dop(usd: float | None, fx: dict[str, Any]) -> float | None:
    if usd is None:
        return None
    return usd * fx["bcrd_venta"]


def hit(
    med: dict[str, Any],
    pais: str,
    moneda: str,
    precio: float,
    presentacion: str,
    producto: str,
    fuente: str,
    tipo_precio: str,
    fx: dict[str, Any],
    fecha_dato: str | None = None,
    estructura: dict[str, Any] | None = None,
    farmacia: str | None = None,
) -> dict[str, Any]:
    usd = a_usd(precio, moneda, fx)
    dosis = parsear_dosis(producto, presentacion)
    if estructura:
        for k in (
            "cantidad_concentracion",
            "unidad_concentracion",
            "tipo_presentacion",
            "cantidad_presentacion",
            "alcance_presentacion",
        ):
            if estructura.get(k) not in (None, ""):
                dosis[k] = estructura[k]
        if estructura.get("cantidad_presentacion") not in (None, ""):
            try:
                dosis["pack"] = int(float(str(estructura["cantidad_presentacion"])))
            except (TypeError, ValueError):
                pass
        # Preferir dosis etiquetada desde concentración estructurada.
        if estructura.get("cantidad_concentracion") and estructura.get("unidad_concentracion"):
            dosis["clave"] = f"{estructura['cantidad_concentracion']} {estructura['unidad_concentracion']}"
    pack = dosis["pack"]
    usd_unidad = None
    fila_eq = {
        "n_lista": med["n"],
        "medicamento_lista": med["nombre"],
        "nombre_comercial": producto,
        "presentacion": presentacion,
        "concentracion": dosis.get("clave"),
        "cantidad_concentracion": dosis.get("cantidad_concentracion"),
        "unidad_concentracion": dosis.get("unidad_concentracion"),
        "tipo_presentacion": dosis.get("tipo_presentacion"),
        "cantidad_presentacion": dosis.get("cantidad_presentacion"),
        "alcance_presentacion": dosis.get("alcance_presentacion"),
    }
    clave_med = clave_medicina_fila(fila_eq)
    clave_pres = clave_presentacion_fila(fila_eq)
    if usd is not None:
        pu = precio_por_unidad_usd(fila_eq, usd)
        usd_unidad = round(pu, 4) if pu is not None else (round(usd / pack, 4) if pack else round(usd, 4))
    return {
        "n": med["n"],
        "medicamento": med["nombre"],
        "programa": med["programa"],
        "pais": pais,
        "producto": str(producto)[:180],
        "presentacion": str(presentacion)[:120],
        "dosis": dosis["clave"],
        "pack": pack,
        "cantidad_concentracion": dosis.get("cantidad_concentracion"),
        "unidad_concentracion": dosis.get("unidad_concentracion"),
        "tipo_presentacion": dosis.get("tipo_presentacion"),
        "cantidad_presentacion": dosis.get("cantidad_presentacion"),
        "alcance_presentacion": dosis.get("alcance_presentacion"),
        "tipo_precio": tipo_precio,
        "farmacia": farmacia or tipo_precio,
        "precio_local": round(precio, 4),
        "moneda": moneda,
        "precio_usd": round(usd, 4) if usd is not None else None,
        "precio_usd_unidad": usd_unidad,
        "precio_dop_bcrd": round(a_dop(usd, fx), 2) if usd is not None else None,
        "clave_medicina": clave_med,
        "clave_presentacion": clave_pres,
        "fuente": fuente,
        "fecha_dato": fecha_dato or datetime.now().date().isoformat(),
    }


def precio_vtex(prod: dict[str, Any]) -> tuple[float | None, str]:
    """PVP de lista (ListPrice); no usar Price con descuento."""
    mejor = None
    pres = ""
    for item in prod.get("items") or []:
        if not pres:
            pres = str(item.get("nameComplete") or item.get("name") or "")
        for seller in item.get("sellers") or []:
            offer = seller.get("commertialOffer") or {}
            p = a_float(offer.get("ListPrice")) or a_float(offer.get("Price"))
            if p is None:
                continue
            if mejor is None or p < mejor:
                mejor = p
    return mejor, pres


def url_vtex_dato(base: str, prod: dict[str, Any]) -> str:
    from scrapper.vtex_urls import pdp_publica, url_pdp

    pdp = url_pdp(base, prod)
    if pdp:
        return pdp
    pid = prod.get("productId")
    if pid:
        resolved = pdp_publica(
            f"{base.rstrip('/')}/api/catalog_system/pub/products/search?fq=productId:{pid}",
            id_producto=str(pid),
        )
        if resolved:
            return resolved
    link = prod.get("linkText")
    if link:
        return f"{base.rstrip('/')}/{link}/p"
    return base


def url_algolia_dato(object_id: str) -> str:
    return (
        f"https://{INKAFARMA_ALGOLIA_APP}-dsn.algolia.net/1/indexes/"
        f"{INKAFARMA_ALGOLIA_INDEX}/{quote(str(object_id))}"
        f"?x-algolia-application-id={INKAFARMA_ALGOLIA_APP}"
        f"&x-algolia-api-key={INKAFARMA_ALGOLIA_KEY}"
    )


def buscar_vtex(
    s: requests.Session,
    fx: dict[str, Any],
    *,
    pais: str,
    moneda: str,
    base: str,
    etiqueta: str,
    portal: str,
) -> list[dict[str, Any]]:
    print(f"{pais}: {etiqueta} (VTEX)")
    out: list[dict[str, Any]] = []
    for med in MEDICAMENTOS:
        n_ok = 0
        vistos: set[str] = set()
        for alias in aliases_busqueda(med):
            if n_ok >= 15:
                break

            def cargar(a=alias, b=base):
                time.sleep(PAUSA)
                url = f"{b}/api/catalog_system/pub/products/search?ft={quote(a)}&_from=0&_to=19"
                r = s.get(url, timeout=TIMEOUT, headers={"Referer": b + "/", "Accept": "application/json"})
                r.raise_for_status()
                data = r.json()
                return data if isinstance(data, list) else []

            try:
                prods, fecha = cache_json(etiqueta, alias, cargar)
            except Exception as exc:
                print(f"  error {alias}: {exc}")
                continue
            for prod in prods:
                nombre = str(prod.get("productName") or "")
                blob = " ".join(
                    [
                        nombre,
                        str(prod.get("brand") or ""),
                        str(prod.get("description") or "")[:200],
                        " ".join(str(x) for x in (prod.get("allSpecifications") or [])[:8]),
                    ]
                )
                if not coincide(blob, med):
                    continue
                precio, pres = precio_vtex(prod)
                if precio is None:
                    continue
                pid = str(prod.get("productId") or nombre)
                if pid in vistos:
                    continue
                vistos.add(pid)
                out.append(
                    hit(
                        med,
                        pais,
                        moneda,
                        precio,
                        pres,
                        nombre,
                        url_vtex_dato(base, prod),
                        f"PVP {etiqueta} (tienda online)",
                        fx,
                        fecha_dato=fecha,
                    )
                )
                n_ok += 1
                if n_ok >= 15:
                    break
            if n_ok:
                break
    print(f"  {len(out)} coincidencias")
    return out


def buscar_desde_tabla(
    fx: dict[str, Any],
    *,
    pais: str | None = None,
    paises: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Coincidencias desde medicamentos_altos_costos_america (scrapers)."""
    if pais:
        titulo = f"{pais}: tabla consolidada"
        filtro = {pais}
    elif paises:
        titulo = "Tabla consolidada: " + ", ".join(paises)
        filtro = set(paises)
    else:
        titulo = "Tabla consolidada (todos los países con scraper)"
        filtro = None
    print(titulo)
    evid = CARPETA / "plataforma" / "datos" / "tabla"
    evid.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, Any]] = []
    meds_por_n = {int(m["n"]): m for m in MEDICAMENTOS}
    try:
        filas_db = [
            r for r in listar_filas()
            if a_float(r.get("precio")) is not None
            and (filtro is None or r.get("pais") in filtro)
        ]
    except Exception as exc:
        print(f"  error leyendo tabla consolidada: {exc}")
        filas_db = []

    for row in filas_db:
        try:
            n_lista = int(row.get("n_lista"))
        except Exception:
            continue
        med = meds_por_n.get(n_lista)
        if not med:
            continue
        precio = a_float(row.get("precio"))
        if precio is None:
            continue
        pais_row = str(row.get("pais") or "")
        nombre = str(row.get("nombre_comercial") or row.get("medicamento_lista") or "")
        pres = " ".join(
            str(x) for x in (row.get("presentacion"), row.get("concentracion")) if x
        )
        farmacia = str(row.get("farmacia") or pais_row or "farmacia")
        pid = str(row.get("id_producto_farmacia") or row.get("id") or "").strip()
        slug_far = re.sub(r"[^a-z0-9]+", "_", norm(farmacia)).strip("_") or "far"
        slug_pais = re.sub(r"[^a-z0-9]+", "_", norm(pais_row)).strip("_") or "pais"
        fuente_url = str(row.get("fuente_url") or "").strip()
        if pid:
            recorte = {
                "origen": f"tabla consolidada · {pais_row} · {farmacia}",
                "fecha": row.get("fecha_dato"),
                "fila": row,
            }
            archivo = f"{slug_pais}_{slug_far}_{pid}.json"
            (evid / archivo).write_text(
                json.dumps(recorte, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            # Enlace público: URL de la farmacia; el JSON en datos/tabla/ queda como evidencia.
            fuente = fuente_url or ""
        else:
            fuente = fuente_url
        if not fuente and fuente_url:
            fuente = fuente_url
        try:
            from scrapper.vtex_urls import pdp_publica

            pdp = pdp_publica(
                fuente or fuente_url,
                farmacia=farmacia,
                pais=pais_row,
                id_producto=pid,
                nombre_comercial=nombre,
            )
            if pdp:
                fuente = pdp
        except Exception:
            pass
        out.append(
            hit(
                med,
                pais_row,
                str(row.get("moneda") or "USD").upper(),
                precio,
                pres,
                nombre,
                fuente,
                f"PVP {farmacia} (tabla consolidada)",
                fx,
                fecha_dato=str(row.get("fecha_dato") or ""),
                estructura={
                    "cantidad_concentracion": row.get("cantidad_concentracion"),
                    "unidad_concentracion": row.get("unidad_concentracion"),
                    "tipo_presentacion": row.get("tipo_presentacion"),
                    "cantidad_presentacion": row.get("cantidad_presentacion"),
                    "alcance_presentacion": row.get("alcance_presentacion"),
                },
                farmacia=farmacia,
            )
        )
    print(f"  {len(out)} coincidencias")
    return out


def buscar_rd(fx: dict[str, Any]) -> list[dict[str, Any]]:
    """República Dominicana desde tabla; respaldo catálogo 3C si vacío."""
    out = buscar_desde_tabla(fx, pais="República Dominicana")
    if out:
        return out

    if not CATALOGO_RD.exists():
        print("  no hay filas RD en tabla ni catalogo/productos.json")
        return []
    print("  sin filas RD consolidadas; usando catalogo 3C de respaldo")
    evid = CARPETA / "plataforma" / "datos" / "rd"
    evid.mkdir(parents=True, exist_ok=True)
    productos = json.loads(CATALOGO_RD.read_text(encoding="utf-8"))
    fecha = fecha_catalogo_rd()
    for med in MEDICAMENTOS:
        for p in productos:
            nombre = p.get("nombre") or ""
            pa = p.get("principios_activos") or []
            pa_txt = " ".join(str(x) for x in pa) if isinstance(pa, list) else str(pa)
            blob = f"{nombre} {pa_txt}"
            if not coincide(blob, med):
                continue
            precio = a_float(p.get("precio") or p.get("precio_marcado"))
            if precio is None:
                continue
            dosajes = p.get("principios_activos_con_dosaje") or []
            dosaje_txt = " ".join(
                str(d.get("dosaje") or "") for d in dosajes if isinstance(d, dict)
            )
            pres = " ".join(
                str(x) for x in (p.get("tipo_presentacion"), dosaje_txt)
                if x
            )
            pid = p.get("id")
            if pid is not None:
                recorte = {
                    "origen": "catalogo/productos.json · Farmacia 3C",
                    "fecha": fecha,
                    "id": pid,
                    "nombre": nombre,
                    "precio": p.get("precio"),
                    "precio_marcado": p.get("precio_marcado"),
                    "tipo_presentacion": p.get("tipo_presentacion"),
                    "laboratorio": p.get("laboratorio"),
                    "principios_activos": p.get("principios_activos"),
                    "principios_activos_con_dosaje": dosajes,
                }
                (evid / f"{pid}.json").write_text(
                    json.dumps(recorte, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                fuente = f"datos/rd/{pid}.json"
            else:
                fuente = ""
            out.append(
                hit(
                    med,
                    "República Dominicana",
                    "DOP",
                    precio,
                    pres,
                    nombre,
                    fuente,
                    "PVP Farmacia 3C (catalogo retail)",
                    fx,
                    fecha_dato=fecha,
                )
            )
    print(f"  {len(out)} coincidencias")
    return out


def buscar_inkafarma(s: requests.Session, fx: dict[str, Any]) -> list[dict[str, Any]]:
    print("Peru: Inkafarma (buscador Algolia)")
    out: list[dict[str, Any]] = []
    url = f"https://{INKAFARMA_ALGOLIA_APP}-dsn.algolia.net/1/indexes/{INKAFARMA_ALGOLIA_INDEX}/query"
    headers = {
        "X-Algolia-Application-Id": INKAFARMA_ALGOLIA_APP,
        "X-Algolia-API-Key": INKAFARMA_ALGOLIA_KEY,
        "Content-Type": "application/json",
        "Referer": INKAFARMA + "/",
    }
    for med in MEDICAMENTOS:
        n_ok = 0
        vistos: set[str] = set()
        for alias in aliases_busqueda(med):
            if n_ok >= 15:
                break

            def cargar(a=alias):
                time.sleep(PAUSA)
                r = s.post(url, headers=headers, json={"query": a, "hitsPerPage": 20}, timeout=TIMEOUT)
                r.raise_for_status()
                return r.json().get("hits") or []

            try:
                hits, fecha = cache_json("inkafarma", alias, cargar)
            except Exception as exc:
                print(f"  error {alias}: {exc}")
                continue
            for row in hits:
                blob = " ".join(
                    str(row.get(k) or "")
                    for k in ("name", "composition", "keyword", "brand", "laboratory", "activePrinciples")
                )
                if not coincide(blob, med):
                    continue
                precio = a_float(row.get("pricePromo")) if row.get("withPromotion") else None
                if not precio:
                    precio = a_float(row.get("priceList") or row.get("validPrice") or row.get("priceWithCard"))
                if precio is None:
                    continue
                oid = str(row.get("objectID") or row.get("skuSap") or row.get("name"))
                if oid in vistos:
                    continue
                vistos.add(oid)
                fuente = (
                    f"{INKAFARMA}/producto/{row.get('uri')}/{row.get('objectID')}"
                    if row.get("uri") and row.get("objectID")
                    else f"{INKAFARMA}/producto/{row.get('uri')}"
                    if row.get("uri")
                    else url_algolia_dato(oid)
                    if row.get("objectID")
                    else INKAFARMA
                )
                out.append(
                    hit(
                        med,
                        "Perú",
                        "PEN",
                        precio,
                        " ".join(
                            str(x)
                            for x in (row.get("presentation"), row.get("composition"))
                            if x
                        ),
                        str(row.get("name") or ""),
                        fuente,
                        "PVP Inkafarma (tienda online)",
                        fx,
                        fecha_dato=fecha,
                    )
                )
                n_ok += 1
                if n_ok >= 15:
                    break
            if n_ok:
                break
    print(f"  {len(out)} coincidencias")
    return out


def buscar_ahumada(s: requests.Session, fx: dict[str, Any]) -> list[dict[str, Any]]:
    print("Chile: Farmacias Ahumada (busqueda web)")
    out: list[dict[str, Any]] = []
    for med in MEDICAMENTOS:
        n_ok = 0
        vistos: set[str] = set()
        for alias in aliases_busqueda(med):
            if n_ok >= 15:
                break

            def cargar(a=alias):
                time.sleep(PAUSA)
                url = (
                    f"{AHUMADA}/on/demandware.store/Sites-ahumada-cl-Site/default/"
                    f"Search-UpdateGrid?q={quote(a)}"
                )
                r = s.get(
                    url,
                    timeout=TIMEOUT,
                    headers={"Referer": f"{AHUMADA}/search?q={quote(a)}", "Accept": "text/html"},
                )
                r.raise_for_status()
                return {"html": r.text}

            try:
                packed, fecha = cache_json("ahumada", alias, cargar)
            except Exception as exc:
                print(f"  error {alias}: {exc}")
                continue
            html = packed.get("html") or ""
            for m in re.finditer(
                r'<div class="pdp-link">\s*<a class="link" href="(?P<href>[^"]+)">(?P<name>[^<]+)</a>',
                html,
                flags=re.I,
            ):
                nombre = unescape(m.group("name")).strip()
                if not coincide(nombre, med):
                    continue
                after = html[m.end() : m.end() + 2500]
                precio = None
                mprice = re.search(r'class="sales".{0,500}?\$\s*([\d.]+)', after, flags=re.S | re.I)
                if mprice:
                    precio = clp(mprice.group(1))
                if precio is None:
                    mval = re.search(r'class="value" content="(\d+)"', after)
                    if mval:
                        precio = a_float(mval.group(1))
                if precio is None:
                    continue
                href = m.group("href")
                if href in vistos:
                    continue
                vistos.add(href)
                fuente = href if href.startswith("http") else AHUMADA + href
                out.append(
                    hit(
                        med,
                        "Chile",
                        "CLP",
                        precio,
                        "",
                        nombre,
                        fuente,
                        "PVP Farmacias Ahumada (tienda online)",
                        fx,
                        fecha_dato=fecha,
                    )
                )
                n_ok += 1
                if n_ok >= 15:
                    break
            if n_ok:
                break
    print(f"  {len(out)} coincidencias")
    return out


def resumir(detalle: list[dict[str, Any]], fx: dict[str, Any]) -> pd.DataFrame:
    """Compara misma dosis + mismo alcance (unidad/lote/caja/kit). No mezcla unidad con paquete."""
    filas = []
    for med in sorted(MEDICAMENTOS, key=lambda m: (prioridad(str(m["programa"])), int(m["n"]))):
        fila: dict[str, Any] = {
            "prioridad": prioridad(str(med["programa"])),
            "n_lista": med["n"],
            "medicamento": med["nombre"],
            "programa": med["programa"],
            "presentacion_comparada": "",
        }
        por_pais: dict[str, list] = defaultdict(list)
        for h in detalle:
            if h["n"] == med["n"] and h.get("precio_usd") is not None:
                por_pais[h["pais"]].append(h)

        votos: dict[str, set[str]] = defaultdict(set)
        for pais, hs in por_pais.items():
            for h in hs:
                clave_v = h.get("clave_presentacion") or h.get("dosis")
                if clave_v:
                    votos[str(clave_v)].add(pais)
        clave = max(votos, key=lambda k: (len(votos[k]), k)) if votos else ""

        hits_clave: dict[str, list] = {}
        for pais, hs in por_pais.items():
            filtrados = [
                h
                for h in hs
                if (not clave or str(h.get("clave_presentacion") or h.get("dosis") or "") == clave)
            ]
            if filtrados:
                hits_clave[pais] = filtrados

        # Preferir alcances conocidos; nunca mezclar unidad con lote/caja/kit.
        scope_paises: dict[str, set[str]] = defaultdict(set)
        for pais, hs in hits_clave.items():
            for h in hs:
                scope = str(h.get("alcance_presentacion") or "").strip().lower()
                if scope and scope != "desconocido":
                    scope_paises[scope].add(pais)
        # Prioridad: el alcance con más países; empate → unidad > lote > caja > kit.
        pri_scope = {"unidad": 4, "lote": 3, "caja": 2, "kit": 1}
        scope_ref = (
            max(scope_paises, key=lambda k: (len(scope_paises[k]), pri_scope.get(k, 0), k))
            if scope_paises
            else ""
        )
        if scope_ref:
            for pais, hs in list(hits_clave.items()):
                scoped = [
                    h
                    for h in hs
                    if str(h.get("alcance_presentacion") or "").strip().lower() == scope_ref
                ]
                # Si el país no tiene ese alcance, queda fuera (no rellenar con otro empaque).
                if scoped:
                    hits_clave[pais] = scoped
                else:
                    hits_clave.pop(pais, None)
        else:
            # Sin alcance conocido no hay comparación fiable entre países.
            hits_clave = {}

        pack_paises: dict[int, set[str]] = defaultdict(set)
        for pais, hs in hits_clave.items():
            for h in hs:
                if h.get("pack"):
                    pack_paises[h["pack"]].add(pais)
        pack_ref = max(pack_paises, key=lambda k: (len(pack_paises[k]), -k)) if pack_paises else None

        # Dentro del mismo alcance, alinear al pack más común solo si ambos tienen conteo.
        if pack_ref and scope_ref in {"lote", "caja", "kit"}:
            for pais, hs in list(hits_clave.items()):
                same_pack = [h for h in hs if h.get("pack") == pack_ref]
                if same_pack:
                    hits_clave[pais] = same_pack

        etiq = clave
        if clave and pack_ref:
            etiq = f"{clave} × {pack_ref} un."
        elif pack_ref:
            etiq = f"{pack_ref} unidades"
        if scope_ref:
            etiq = f"{etiq} · {scope_ref}" if etiq else scope_ref
        fila["presentacion_comparada"] = etiq

        usds = []
        for pais in PAISES:
            hs = hits_clave.get(pais, [])
            if not hs:
                fila[f"{pais} — n hits"] = 0
                fila[f"{pais} — min USD"] = None
                fila[f"{pais} — mediana USD"] = None
                fila[f"{pais} — min DOP (BCRD)"] = None
                fila[f"{pais} — ejemplo"] = ""
                fila[f"{pais} — tipo precio"] = ""
                fila[f"{pais} — fuente"] = ""
                fila[f"{pais} — fecha"] = ""
                continue

            # Solo comparar precio tal cual dentro del mismo alcance/pack; sin inventar
            # equivalencias unidad↔lote.
            precios_eq = [h["precio_usd"] for h in hs]
            serie = pd.Series(precios_eq)
            mini = float(serie.min())
            medn = float(serie.median())
            best = hs[int(serie.idxmin())]
            pack_txt = f" x{best['pack']}" if best.get("pack") else ""
            alcance_txt = f" · {best.get('alcance_presentacion')}" if best.get("alcance_presentacion") else ""
            fila[f"{pais} — n hits"] = len(hs)
            fila[f"{pais} — min USD"] = round(mini, 4)
            fila[f"{pais} — mediana USD"] = round(medn, 4)
            fila[f"{pais} — min DOP (BCRD)"] = round(mini * fx["bcrd_venta"], 2)
            fila[f"{pais} — ejemplo"] = f"{best['producto']}{pack_txt}{alcance_txt}"
            fila[f"{pais} — tipo precio"] = best["tipo_precio"]
            fila[f"{pais} — fuente"] = best["fuente"]
            fila[f"{pais} — fecha"] = best.get("fecha_dato") or ""
            usds.append(mini)
        fila["paises_con_dato"] = sum(1 for p in PAISES if fila.get(f"{p} — n hits", 0))
        fila["min_global_USD"] = round(min(usds), 4) if usds else None
        fila["min_global_DOP_BCRD"] = round(min(usds) * fx["bcrd_venta"], 2) if usds else None
        filas.append(fila)
    return pd.DataFrame(filas)


def pintar_hoja(ws, freeze="B2") -> None:
    ws.freeze_panes = freeze
    ws.auto_filter.ref = ws.dimensions
    for col in range(1, ws.max_column + 1):
        celda = ws.cell(1, col)
        celda.fill = ENCABEZADO
        celda.font = FUENTE_H
        celda.alignment = Alignment(vertical="center", wrap_text=True)
        letra = get_column_letter(col)
        ws.column_dimensions[letra].width = min(36, max(12, len(str(celda.value or "")) + 4))
    ws.row_dimensions[1].height = 28
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=ws.max_column):
        prog = ""
        for c in row:
            if c.column == 3:
                prog = str(c.value or "")
        fill = None
        if prog == "FOMAC":
            fill = FOMAC_FILL
        elif "FOMAC" in prog:
            fill = FOMAC_MIX
        for c in row:
            c.font = FUENTE
            c.border = BORDE
            c.alignment = Alignment(vertical="center", wrap_text=True)
            if fill:
                c.fill = fill


def escribir_excel(
    resumen: pd.DataFrame,
    detalle: pd.DataFrame,
    fx: dict[str, Any],
    errores: list[str],
) -> Path:
    SALIDA.mkdir(parents=True, exist_ok=True)
    destino = SALIDA / f"comparativo_alto_costo_{datetime.now().strftime('%Y%m%d')}.xlsx"
    wb = Workbook()

    ws = wb.active
    ws.title = "Comparativo"
    for r in dataframe_to_rows(resumen.drop(columns=["prioridad"], errors="ignore"), index=False, header=True):
        ws.append(r)
    pintar_hoja(ws)

    ws2 = wb.create_sheet("Detalle coincidencias")
    det = detalle.copy()
    det["_p"] = det["programa"].map(prioridad)
    det = det.sort_values(["_p", "n", "pais", "precio_usd"]).drop(columns="_p")
    for r in dataframe_to_rows(det, index=False, header=True):
        ws2.append(r)
    pintar_hoja(ws2)

    ws3 = wb.create_sheet("Fuentes")
    fuentes = [
        ["País", "Farmacia", "Qué representa el precio", "Link", "Cómo se obtiene"],
        [
            "República Dominicana",
            "Fuentes RD consolidadas",
            "PVP retail consolidado en DOP desde FarmaValue, Carol, Qualipharma, farmacias.do y otras fuentes RD integradas",
            RD_API,
            "Tabla consolidada del proyecto + evidencias JSON por producto",
        ],
        [
            "Argentina",
            "Farmacity",
            "Precio de venta al público en la tienda online (ARS)",
            FARMACITY,
            "API pública VTEX /api/catalog_system/pub/products/search",
        ],
        [
            "Brasil",
            "Pague Menos",
            "Precio de venta al público en la tienda online (BRL)",
            PAGUE_MENOS,
            "API pública VTEX /api/catalog_system/pub/products/search",
        ],
        [
            "Brasil",
            "Drogasil",
            "Precio de venta al público en la tienda online (BRL)",
            DROGASIL,
            "API pública VTEX (Akamai puede bloquear el datacenter)",
        ],
        [
            "Brasil",
            "Droga Raia",
            "Precio de venta al público en la tienda online (BRL)",
            DROGARAIA,
            "API pública VTEX (Akamai puede bloquear el datacenter)",
        ],
        [
            "Brasil",
            "Panvel",
            "Precio de venta al público en la tienda online (BRL)",
            PANVEL,
            "API pública VTEX (proxy puede bloquear Online Shopping)",
        ],
        [
            "Colombia",
            "Locatel",
            "Precio de venta al público en la tienda online (COP)",
            LOCATEL,
            "API pública VTEX /api/catalog_system/pub/products/search",
        ],
        [
            "Colombia",
            "Farmatodo",
            "Precio de venta al público en la tienda online (COP)",
            "https://www.farmatodo.com.co",
            "Búsqueda Algolia pública de productos",
        ],
        [
            "Colombia",
            "Cruz Verde",
            "Precio de venta al público en la tienda online (COP)",
            "https://www.cruzverde.com.co",
            "API pública VTEX (proxy puede bloquear)",
        ],
        [
            "Colombia",
            "La Rebaja",
            "Precio de venta al público en la tienda online (COP)",
            "https://www.larebajavirtual.com",
            "API pública VTEX (proxy puede bloquear)",
        ],
        [
            "Colombia",
            "Droguerías Cafam",
            "Precio de venta al público en la tienda online (COP)",
            "https://www.drogueriascafam.com.co",
            "API pública VTEX (proxy puede bloquear)",
        ],
        [
            "Perú",
            "Inkafarma",
            "PVP del buscador de la tienda (PEN). priceList / precio promo",
            INKAFARMA,
            "Mismo Algolia que usa inkafarma.pe/buscador",
        ],
        [
            "Chile",
            "Farmacias Ahumada",
            "PVP publicado en la ficha de búsqueda de la tienda (CLP)",
            AHUMADA,
            "HTML público Search-UpdateGrid de Demandware",
        ],
        [
            "México",
            "Macrofarmacias",
            "PVP referencial de especialidad en la tienda (MXN)",
            "https://macrofarmacias.com/",
            "Catálogo público catalogo.php (HTML)",
        ],
        [
            "México",
            "Farmacias Similares",
            "PVP de góndola en la tienda online (MXN)",
            "https://www.farmaciasdesimilares.com/",
            "API pública VTEX de búsqueda de productos",
        ],
        [
            "México",
            "Farmacias del Ahorro",
            "PVP publicado en la tienda online (MXN)",
            "https://www.fahorro.com/",
            "GraphQL Magento de búsqueda de productos",
        ],
        [
            "México",
            "Farmacias San Pablo",
            "PVP publicado en la tienda online (MXN)",
            "https://www.farmaciasanpablo.com.mx/",
            "Búsqueda pública (Akamai suele bloquear este servidor)",
        ],
        [
            "República Dominicana (FX)",
            "Banco Central — mercado cambiario",
            "Cuánto vale 1 USD en DOP (venta BCRD). Se usa para DOP→USD y para mostrar equivalentes en pesos dominicanos",
            BCRD_PORTAL,
            "Portada BCRD",
        ],
        [
            "Argentina (FX)",
            "BCRA — dólar oficial venta",
            "Cuánto vale 1 USD en ARS. El PVP de Farmacity se divide por esta tasa",
            AR_BCRA,
            "dolarapi.com/v1/dolares/oficial (BCRA)",
        ],
        [
            "Brasil (FX)",
            "Banco Central do Brasil — PTAX venta",
            "Cuánto vale 1 USD en BRL. El PVP de Pague Menos se divide por esta tasa",
            BR_BCB,
            "API Olinda PTAX",
        ],
        [
            "Colombia (FX)",
            "Banco de la República — TRM",
            "Cuánto vale 1 USD en COP (Tasa Representativa del Mercado). El PVP de Locatel se divide por esta tasa",
            CO_BANREP,
            "datos.gov.co 32sa-8pi3",
        ],
        [
            "Perú (FX)",
            "BCRP — tipo de cambio venta",
            "Cuánto vale 1 USD en PEN. El PVP de Inkafarma se divide por esta tasa",
            PE_BCRP_PORTAL,
            "Serie PD04646PD (cierre venta)",
        ],
        [
            "Chile (FX)",
            "Banco Central de Chile — dólar observado",
            "Cuánto vale 1 USD en CLP. El PVP de Ahumada se divide por esta tasa",
            CL_BCCH,
            "mindicador.cl/api/dolar",
        ],
    ]
    for r in fuentes:
        ws3.append(r)
    pintar_hoja(ws3, freeze="A2")
    ws3.column_dimensions["B"].width = 40
    ws3.column_dimensions["C"].width = 70
    ws3.column_dimensions["D"].width = 55

    ws4 = wb.create_sheet("Tasas FX")
    ws4.append(["País / moneda", "USD en moneda local", "Qué tasa es", "Fecha", "Fuente", "Link"])
    etiquetas = {
        "DOP": "República Dominicana (DOP)",
        "ARS": "Argentina (ARS)",
        "BRL": "Brasil (BRL)",
        "COP": "Colombia (COP)",
        "PEN": "Perú (PEN)",
        "CLP": "Chile (CLP)",
        "MXN": "México (MXN)",
        "CRC": "Costa Rica (CRC)",
        "HNL": "Honduras (HNL)",
        "GTQ": "Guatemala (GTQ)",
        "NIO": "Nicaragua (NIO)",
        "UYU": "Uruguay (UYU)",
        "PAB": "Panamá (PAB)",
        "PYG": "Paraguay (PYG)",
        "GYD": "Guyana (GYD)",
        "TTD": "Trinidad y Tobago (TTD)",
        "BOB": "Bolivia (BOB)",
        "VES": "Venezuela (VES)",
        "CAD": "Canadá (CAD)",
    }
    for code, etiqueta in etiquetas.items():
        info = (fx.get("por_usd") or {}).get(code) or {}
        ws4.append(
            [
                etiqueta,
                info.get("valor"),
                info.get("nombre"),
                info.get("fecha"),
                info.get("fuente"),
                info.get("link"),
            ]
        )
    ws4.append(["RD compra BCRD (referencia)", fx["bcrd_compra"], "BCRD compra", fx["bcrd_fecha"], "Banco Central RD", fx["bcrd_fuente"]])
    ws4.append(
        [
            "Equivalente en DOP",
            fx["bcrd_venta"],
            "Tras pasar a USD, se multiplica por BCRD venta",
            fx["bcrd_fecha"],
            "Banco Central RD",
            fx["bcrd_fuente"],
        ]
    )
    pintar_hoja(ws4, freeze="A2")
    ws4.column_dimensions["A"].width = 36
    ws4.column_dimensions["C"].width = 42
    ws4.column_dimensions["E"].width = 55
    ws4.column_dimensions["F"].width = 40

    ws5 = wb.create_sheet("Notas y limites")
    notas = [
        ["Nota"],
        ["Seis países de América, una farmacia por país, precio de venta al público de su tienda online."],
        ["FOMAC, FOMAC* y DAMAC-FOMAC van primero."],
        ["Se compara la misma dosis (mg/mcg/UI/ml) y el mismo alcance de empaque (unidad, lote, caja o kit). No se mezcla precio por unidad con precio de paquete/caja."],
        ["Muchos DAMAC son hospitalarios: si la farmacia comunitaria no los vende, la celda queda vacía."],
        ["RD: catálogo 3C. AR: Farmacity. BR: Pague Menos, Drogasil, Droga Raia, Panvel. CO: Locatel, Farmatodo, Cruz Verde, La Rebaja, Cafam. PE: Inkafarma. CL: Ahumada. MX: Macrofarmacias, Similares, Ahorro, San Pablo."],
        ["Las peticiones usan la búsqueda pública de cada sitio, con pausa y caché local para no saturar."],
        ["Conversión a USD: precio local ÷ (cuánto vale 1 dólar en esa moneda, tasa oficial de cada país). DOP usa BCRD venta; ARS dólar oficial BCRA; BRL PTAX; COP TRM; PEN BCRP venta; CLP dólar observado; MXN Banxico FIX."],
        ["El equivalente en DOP se obtiene después: USD × venta BCRD. Así cada país se convierte con su propio dólar, y al final todo se puede leer también en pesos dominicanos."],
    ]
    for r in notas:
        ws5.append(r)
    for e in errores:
        ws5.append([f"Error: {e}"])
    ws5.column_dimensions["A"].width = 140
    ws5["A1"].font = FUENTE_H
    ws5["A1"].fill = ENCABEZADO

    tmp = destino.with_suffix(".xlsx.tmp")
    wb.save(tmp)
    tmp.replace(destino)
    return destino


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    SALIDA.mkdir(parents=True, exist_ok=True)
    s = session()
    errores: list[str] = []
    print("Tasas de cambio...")
    fx = tasas(s)
    print(f"  BCRD venta {fx['bcrd_venta']} DOP por 1 USD ({fx['bcrd_fecha']})")
    for code, info in (fx.get("por_usd") or {}).items():
        print(f"  {code}: 1 USD = {info['valor']} ({info['nombre']} · {info.get('fecha') or 's/f'})")

    detalle: list[dict[str, Any]] = []
    try:
        detalle.extend(buscar_rd(fx))
    except Exception as exc:
        errores.append(f"RD: {exc}")
        print(f"  ERROR RD: {exc}")

    tabla_solo = [
        "México",
        "Panamá",
        "Uruguay",
        "El Salvador",
        "Ecuador",
        "Honduras",
        "Guatemala",
        "Nicaragua",
        "Costa Rica",
    ]
    try:
        detalle.extend(buscar_desde_tabla(fx, paises=tabla_solo))
    except Exception as exc:
        errores.append(f"Tabla scrapers: {exc}")
        print(f"  ERROR tabla scrapers: {exc}")

    jobs = [
        (lambda: buscar_vtex(s, fx, pais="Argentina", moneda="ARS", base=FARMACITY, etiqueta="farmacity", portal=FARMACITY), "AR"),
        (lambda: buscar_vtex(s, fx, pais="Brasil", moneda="BRL", base=PAGUE_MENOS, etiqueta="paguemenos", portal=PAGUE_MENOS), "BR"),
        (lambda: buscar_vtex(s, fx, pais="Colombia", moneda="COP", base=LOCATEL, etiqueta="locatel", portal=LOCATEL), "CO"),
        (lambda: buscar_inkafarma(s, fx), "PE"),
        (lambda: buscar_ahumada(s, fx), "CL"),
    ]
    for fn, name in jobs:
        try:
            detalle.extend(fn())
        except Exception as exc:
            errores.append(f"{name}: {exc}")
            print(f"  ERROR {name}: {exc}")

    det_df = pd.DataFrame(detalle)
    if det_df.empty:
        det_df = pd.DataFrame(
            columns=[
                "n", "medicamento", "programa", "pais", "producto", "presentacion",
                "dosis", "pack", "tipo_precio", "precio_local", "moneda",
                "precio_usd", "precio_usd_unidad", "precio_dop_bcrd", "fuente", "fecha_dato",
            ]
        )
    resumen = resumir(detalle, fx)
    destino = escribir_excel(resumen, det_df, fx, errores)
    con_dato = int((resumen["paises_con_dato"] > 0).sum()) if not resumen.empty else 0
    print(f"Listo: {destino}")
    print(f"Medicamentos con al menos un PVP de farmacia: {con_dato}/{len(MEDICAMENTOS)}")
    if errores:
        print("Errores:", *errores, sep="\n  ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
