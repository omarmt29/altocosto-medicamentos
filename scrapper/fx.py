"""Tasas oficiales (unidades de moneda local por 1 USD)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import requests

BANXICO_TIPOS = "https://www.banxico.org.mx/tipcamb/llenarTiposCambioAction.do?idioma=sp"
BANXICO_PORTAL = "https://www.banxico.org.mx/"
AR_DOLAR = "https://dolarapi.com/v1/dolares/oficial"
AR_BCRA = "https://www.bcra.gob.ar/"
CO_TRM = "https://www.datos.gov.co/resource/32sa-8pi3.json"
CO_BANREP = "https://www.banrep.gov.co/es/estadisticas/trm"
ER_API = "https://open.er-api.com/v6/latest/USD"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        }
    )
    return s


def tasa_mxn(s: requests.Session | None = None) -> dict[str, Any]:
    """FIX Banxico (pesos por dólar). Reserva: open.er-api.com."""
    ses = s or _session()
    try:
        r = ses.get(BANXICO_TIPOS, timeout=25)
        r.raise_for_status()
        html = r.text
        marker = 'id="tdSF43718"'
        i = html.find(marker)
        if i < 0:
            raise ValueError("sin SF43718")
        chunk = html[i : i + 250]
        import re

        m = re.search(r"(\d+\.\d{2,6})", chunk)
        if not m:
            raise ValueError("sin número FIX")
        valor = float(m.group(1))
        fecha_m = re.search(r"(\d{2}/\d{2}/\d{4})", html)
        fecha = ""
        if fecha_m:
            d, mo, y = fecha_m.group(1).split("/")
            fecha = f"{y}-{mo}-{d}"
        else:
            fecha = datetime.now().date().isoformat()
        return {
            "moneda": "MXN",
            "valor": valor,
            "nombre": "Banxico FIX (SF43718)",
            "fecha": fecha,
            "fuente": "Banco de México — tipo de cambio para solventar obligaciones",
            "link": BANXICO_PORTAL,
        }
    except Exception:
        r = ses.get(ER_API, timeout=20)
        r.raise_for_status()
        d = r.json()
        valor = float((d.get("rates") or {})["MXN"])
        return {
            "moneda": "MXN",
            "valor": valor,
            "nombre": "Reserva (mercado)",
            "fecha": str(d.get("time_last_update_utc") or "")[:16],
            "fuente": "open.er-api.com",
            "link": ER_API,
        }


def _er_api_moneda(ses: requests.Session, codigo: str) -> dict[str, Any]:
    r = ses.get(ER_API, timeout=20)
    r.raise_for_status()
    d = r.json()
    valor = float((d.get("rates") or {})[codigo])
    return {
        "moneda": codigo,
        "valor": valor,
        "nombre": "Reserva (mercado)",
        "fecha": str(d.get("time_last_update_utc") or "")[:16],
        "fuente": "open.er-api.com",
        "link": ER_API,
    }


def tasa_ars(s: requests.Session | None = None) -> dict[str, Any]:
    """Dólar oficial venta BCRA (pesos por dólar)."""
    ses = s or _session()
    try:
        r = ses.get(AR_DOLAR, timeout=25)
        r.raise_for_status()
        d = r.json()
        return {
            "moneda": "ARS",
            "valor": float(d["venta"]),
            "nombre": "BCRA / dólar oficial venta",
            "fecha": str(d.get("fechaActualizacion") or "")[:10],
            "fuente": "Banco Central de la República Argentina (oficial)",
            "link": AR_BCRA,
        }
    except Exception:
        return _er_api_moneda(ses, "ARS")


def tasa_cop(s: requests.Session | None = None) -> dict[str, Any]:
    """TRM (peso colombiano por dólar)."""
    ses = s or _session()
    try:
        r = ses.get(f"{CO_TRM}?$limit=1&$order=vigenciadesde DESC", timeout=30)
        r.raise_for_status()
        fila = (r.json() or [None])[0]
        if not fila:
            raise ValueError("TRM vacío")
        return {
            "moneda": "COP",
            "valor": float(fila["valor"]),
            "nombre": "TRM (peso por dólar)",
            "fecha": str(fila.get("vigenciadesde") or "")[:10],
            "fuente": "Banco de la República / Superintendencia Financiera — TRM",
            "link": CO_BANREP,
        }
    except Exception:
        return _er_api_moneda(ses, "COP")


def _fila_web(etiqueta: str, t: dict[str, Any]) -> dict[str, Any]:
    return {
        "País / moneda": etiqueta,
        "USD en moneda local": t["valor"],
        "Qué tasa es": t["nombre"],
        "Fecha": t["fecha"],
        "Fuente": t["fuente"],
        "Link": t["link"],
    }


CL_DOLAR = "https://mindicador.cl/api/dolar"
CL_BCCH = "https://www.bcentral.cl/"


def tasa_clp(s: requests.Session | None = None) -> dict[str, Any]:
    """Dólar observado BCCh (pesos chilenos por dólar)."""
    ses = s or _session()
    try:
        r = ses.get(CL_DOLAR, timeout=25)
        r.raise_for_status()
        serie = r.json().get("serie") or []
        if not serie:
            raise ValueError("mindicador vacío")
        return {
            "moneda": "CLP",
            "valor": float(serie[0]["valor"]),
            "nombre": "Dólar observado BCCh",
            "fecha": str(serie[0].get("fecha") or "")[:10],
            "fuente": "Banco Central de Chile — dólar observado (mindicador.cl)",
            "link": CL_BCCH,
        }
    except Exception:
        return _er_api_moneda(ses, "CLP")


def tasa_crc(s: requests.Session | None = None) -> dict[str, Any]:
    """Colón costarricense por dólar (reserva mercado)."""
    return _er_api_moneda(s or _session(), "CRC")


def tasa_pab(s: requests.Session | None = None) -> dict[str, Any]:
    """Balboa panameño: paridad 1:1 con USD."""
    _ = s
    return {
        "moneda": "PAB",
        "valor": 1.0,
        "nombre": "Paridad PAB/USD (1:1)",
        "fecha": datetime.now().date().isoformat(),
        "fuente": "Balboa panameño a la par del dólar estadounidense",
        "link": "https://www.banconal.com.pa/",
    }


def tasa_pen(s: requests.Session | None = None) -> dict[str, Any]:
    """Sol peruano por dólar (reserva mercado; BCRP en generar_comparativo)."""
    return _er_api_moneda(s or _session(), "PEN")


def tasa_uyu(s: requests.Session | None = None) -> dict[str, Any]:
    """Peso uruguayo por dólar (reserva mercado)."""
    return _er_api_moneda(s or _session(), "UYU")


def tasa_hnl(s: requests.Session | None = None) -> dict[str, Any]:
    """Lempira hondureño por dólar (reserva mercado)."""
    return _er_api_moneda(s or _session(), "HNL")


def tasa_gtq(s: requests.Session | None = None) -> dict[str, Any]:
    """Quetzal guatemalteco por dólar (reserva mercado)."""
    return _er_api_moneda(s or _session(), "GTQ")


def tasa_nio(s: requests.Session | None = None) -> dict[str, Any]:
    """Córdoba nicaragüense por dólar (reserva mercado)."""
    return _er_api_moneda(s or _session(), "NIO")


def tasa_pyg(s: requests.Session | None = None) -> dict[str, Any]:
    """Guaraní paraguayo por dólar (reserva mercado)."""
    return _er_api_moneda(s or _session(), "PYG")


def tasa_gyd(s: requests.Session | None = None) -> dict[str, Any]:
    """Dólar guyanés por dólar (reserva mercado)."""
    return _er_api_moneda(s or _session(), "GYD")


def tasa_ttd(s: requests.Session | None = None) -> dict[str, Any]:
    """Dólar de Trinidad y Tobago por dólar (reserva mercado)."""
    return _er_api_moneda(s or _session(), "TTD")


def tasa_bob(s: requests.Session | None = None) -> dict[str, Any]:
    """Boliviano por dólar (reserva mercado)."""
    return _er_api_moneda(s or _session(), "BOB")


def tasa_ves(s: requests.Session | None = None) -> dict[str, Any]:
    """Bolívar venezolano por dólar (reserva mercado)."""
    return _er_api_moneda(s or _session(), "VES")


def tasa_cad(s: requests.Session | None = None) -> dict[str, Any]:
    """Dólar canadiense por dólar (reserva mercado)."""
    return _er_api_moneda(s or _session(), "CAD")


def tasas_para_web() -> list[dict[str, Any]]:
    """Filas para /api/tasas."""
    ses = _session()
    out: list[dict[str, Any]] = []
    for etiqueta, fn in (
        ("Argentina (ARS)", tasa_ars),
        ("Colombia (COP)", tasa_cop),
        ("México (MXN)", tasa_mxn),
        ("Chile (CLP)", tasa_clp),
        ("Perú (PEN)", tasa_pen),
        ("Costa Rica (CRC)", tasa_crc),
        ("Panamá (PAB)", tasa_pab),
        ("Uruguay (UYU)", tasa_uyu),
        ("Honduras (HNL)", tasa_hnl),
        ("Guatemala (GTQ)", tasa_gtq),
        ("Nicaragua (NIO)", tasa_nio),
        ("Paraguay (PYG)", tasa_pyg),
        ("Guyana (GYD)", tasa_gyd),
        ("Trinidad y Tobago (TTD)", tasa_ttd),
        ("Bolivia (BOB)", tasa_bob),
        ("Venezuela (VES)", tasa_ves),
        ("Canadá (CAD)", tasa_cad),
    ):
        try:
            out.append(_fila_web(etiqueta, fn(ses)))
        except Exception:
            continue
    return out
