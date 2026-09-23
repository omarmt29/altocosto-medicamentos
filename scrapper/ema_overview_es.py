"""Extrae el Medicine Overview EPAR en español desde la ficha EMA.

En la página del medicamento, bajo «Medicine overview», hay PDFs en varios
idiomas. Preferimos el `_es.pdf` y parseamos secciones como:

- ¿Qué es X y para qué se utiliza?  → indicaciones
- ¿Cómo se usa X?
- ¿Cómo actúa X?
- beneficios / riesgos / autorización / medidas / otra información
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "cache" / "ema_overview_es"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
BASE = "https://www.ema.europa.eu"
CACHE_TTL_SEC = 60 * 60 * 24 * 30  # 30 días
TIMEOUT = 35

SECTION_ALIASES: list[tuple[str, tuple[str, ...]]] = [
    (
        "indicaciones",
        (
            "para qué se utiliza",
            "para que se utiliza",
            "qué es",
            "que es",
        ),
    ),
    (
        "como_se_usa",
        ("cómo se usa", "como se usa", "cómo se administra", "como se administra"),
    ),
    (
        "como_actua",
        ("cómo actúa", "como actúa", "como actua", "cómo actua", "cómo funciona", "como funciona"),
    ),
    (
        "beneficios",
        (
            "qué beneficios",
            "que beneficios",
            "beneficios ha demostrado",
            "qué ha demostrado",
        ),
    ),
    (
        "riesgos",
        (
            "cuál es el riesgo",
            "cual es el riesgo",
            "riesgo asociado",
            "qué riesgos",
            "que riesgos",
        ),
    ),
    (
        "autorizacion",
        (
            "por qué se ha autorizado",
            "porque se ha autorizado",
            "por qué se autorizó",
            "motivos por los que se autoriza",
        ),
    ),
    (
        "medidas",
        (
            "qué medidas se han adoptado",
            "que medidas se han adoptado",
            "garantizar un uso seguro",
            "uso seguro y eficaz",
        ),
    ),
    (
        "otra_info",
        ("otra información", "otra informacion"),
    ),
]


def _sess() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "es,en;q=0.8"})
    return s


def _key(url: str) -> str:
    return hashlib.sha1(url.strip().encode("utf-8")).hexdigest()[:24]


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def _leer_cache(key: str) -> dict[str, Any] | None:
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - float(data.get("ts") or 0) > CACHE_TTL_SEC:
            return None
        if not isinstance(data.get("payload"), dict):
            return None
        return data["payload"]
    except Exception:
        return None


def _guardar_cache(key: str, payload: dict[str, Any]) -> None:
    path = _cache_path(key)
    path.write_text(
        json.dumps({"ts": time.time(), "payload": payload}, ensure_ascii=False),
        encoding="utf-8",
    )


def _slug_desde_medicine_url(medicine_url: str) -> str | None:
    path = urlparse(medicine_url or "").path.strip("/")
    if not path:
        return None
    # .../medicines/human/EPAR/orkambi  ó  .../en/medicines/human/EPAR/orkambi
    m = re.search(r"/EPAR/([^/?#]+)", path, flags=re.I)
    if m:
        return m.group(1).strip()
    parts = [p for p in path.split("/") if p]
    return parts[-1] if parts else None


def _abs(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http"):
        return url
    return urljoin(BASE, url)


def resolver_pdf_overview_es(medicine_url: str, sess: requests.Session | None = None) -> str | None:
    """Localiza el PDF 'Medicine overview' en español en la ficha EPAR."""
    url = (medicine_url or "").strip()
    if not url:
        return None
    s = sess or _sess()

    # 1) Intento directo por convención de nombres EMA
    slug = _slug_desde_medicine_url(url)
    candidatos: list[str] = []
    if slug:
        for form in (slug, slug.lower(), slug.replace(" ", "-")):
            candidatos.append(
                f"{BASE}/es/documents/overview/{form}-epar-medicine-overview_es.pdf"
            )

    # 2) Parsear HTML de la ficha
    try:
        r = s.get(url, timeout=TIMEOUT)
        if r.status_code == 200 and r.text:
            hrefs = re.findall(
                r'href="([^"]*medicine-overview[^"]*_es\.pdf[^"]*)"',
                r.text,
                flags=re.I,
            )
            if not hrefs:
                hrefs = re.findall(
                    r'href="([^"]*overview[^"]*_es\.pdf[^"]*)"',
                    r.text,
                    flags=re.I,
                )
            for h in hrefs:
                candidatos.insert(0, _abs(h))
    except Exception:
        pass

    seen: set[str] = set()
    for cand in candidatos:
        if not cand or cand in seen:
            continue
        seen.add(cand)
        try:
            head = s.head(cand, timeout=12, allow_redirects=True)
            if head.status_code == 200 and "pdf" in (head.headers.get("Content-Type") or "").lower():
                return cand
            # Algunos CDN no responden bien a HEAD
            if head.status_code in (403, 405, 501):
                get = s.get(cand, timeout=TIMEOUT, stream=True)
                if get.status_code == 200:
                    get.close()
                    return cand
        except Exception:
            continue
    return None


def _limpiar_texto_pdf(raw: str) -> str:
    t = raw or ""
    # Cabecera institucional EMA
    t = re.sub(
        r"Official address[\s\S]{0,700}?Telephone[^\n]*\n?",
        "\n",
        t,
        flags=re.I,
    )
    t = re.sub(r"©\s*European Medicines Agency[\s\S]{0,200}?acknowledged\.\s*", "\n", t, flags=re.I)
    t = re.sub(r"An agency of the European Union\s*", "\n", t, flags=re.I)
    t = re.sub(r"Address for visits and deliveries[^\n]*\n?", "\n", t, flags=re.I)
    t = re.sub(r"Send us a question[^\n]*\n?", "\n", t, flags=re.I)
    t = re.sub(r"Refer to www\.ema\.europa\.eu[^\n]*\n?", "\n", t, flags=re.I)
    t = re.sub(r"Go to www\.ema\.europa\.eu[^\n]*\n?", "\n", t, flags=re.I)
    # Pie de página
    t = re.sub(r"[A-Za-zÁÉÍÓÚáéíóúÑñ0-9 /().,-]{0,60}EMA/\d+/\d+\s*Página\s*\d+/\d+", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


def _extraer_texto_pdf(content: bytes) -> str:
    from pypdf import PdfReader
    from io import BytesIO

    reader = PdfReader(BytesIO(content))
    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return _limpiar_texto_pdf("\n".join(parts))


def _clasificar_seccion(titulo: str) -> str | None:
    t = (titulo or "").lower()
    t = t.replace("¿", "").replace("?", "").strip()
    for key, aliases in SECTION_ALIASES:
        if any(a in t for a in aliases):
            return key
    return None


def _parsear_secciones(texto: str) -> dict[str, str]:
    """Parte el overview por preguntas ¿...? y asigna claves conocidas."""
    raw = texto or ""
    # Asegurar saltos antes de cada pregunta
    raw = re.sub(r"(?<!\n)(¿)", r"\n\1", raw)
    chunks = re.split(r"(?=¿[^?\n]{2,160}\?)", raw)
    out: dict[str, str] = {}
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk.startswith("¿"):
            continue
        m = re.match(r"(¿[^?]+\?)\s*([\s\S]*)", chunk)
        if not m:
            continue
        titulo = m.group(1).strip()
        cuerpo = re.sub(r"\s+\n", "\n", m.group(2)).strip()
        cuerpo = re.sub(r"\n{2,}", "\n\n", cuerpo)
        cuerpo = re.sub(r"[ \t]{2,}", " ", cuerpo).strip()
        if len(cuerpo) < 20:
            continue
        key = _clasificar_seccion(titulo)
        if not key:
            continue
        # Conservar la primera aparición (suele ser la más limpia)
        if key not in out:
            out[key] = cuerpo
            out[f"{key}_titulo"] = titulo
    return out


def obtener_overview_es(medicine_url: str, sess: requests.Session | None = None) -> dict[str, Any] | None:
    """Descarga y parsea el Medicine Overview ES de un medicamento EMA."""
    url = (medicine_url or "").strip()
    if not url:
        return None
    key = _key(url)
    cached = _leer_cache(key)
    if cached is not None:
        return cached

    s = sess or _sess()
    pdf_url = resolver_pdf_overview_es(url, sess=s)
    if not pdf_url:
        payload = {"ok": False, "medicine_url": url, "error": "sin_pdf_es"}
        _guardar_cache(key, payload)
        return payload

    try:
        r = s.get(pdf_url, timeout=TIMEOUT)
        r.raise_for_status()
        texto = _extraer_texto_pdf(r.content)
    except Exception as exc:
        payload = {
            "ok": False,
            "medicine_url": url,
            "pdf_url": pdf_url,
            "error": f"pdf:{exc}",
        }
        _guardar_cache(key, payload)
        return payload

    secs = _parsear_secciones(texto)
    indicaciones = (secs.get("indicaciones") or "").strip()
    payload: dict[str, Any] = {
        "ok": bool(indicaciones or secs),
        "medicine_url": url,
        "pdf_url": pdf_url,
        "indicaciones": indicaciones,
        "secciones": {
            k: v
            for k, v in secs.items()
            if not k.endswith("_titulo") and isinstance(v, str) and v.strip()
        },
        "titulos": {k[:-7]: v for k, v in secs.items() if k.endswith("_titulo")},
        "texto_len": len(texto),
    }
    _guardar_cache(key, payload)
    return payload


def enriquecer_filas_ema(
    filas: list[dict[str, Any]],
    info: dict[str, Any] | None = None,
    max_urls: int = 6,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Adjunta overview ES a filas EMA y rellena indicaciones_es oficiales."""
    if not filas:
        return info, filas

    auth = [f for f in filas if str(f.get("medicine_status") or "").lower() == "authorised"]
    base = auth or filas
    urls: list[str] = []
    seen: set[str] = set()
    for f in base:
        u = str(f.get("medicine_url") or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        urls.append(u)
        if len(urls) >= max_urls:
            break

    sess = _sess()
    by_url: dict[str, dict[str, Any]] = {}
    for u in urls:
        try:
            data = obtener_overview_es(u, sess=sess)
        except Exception:
            data = None
        if data and data.get("ok"):
            by_url[u] = data

    out_filas: list[dict[str, Any]] = []
    inds_es: list[str] = []
    seen_ind: set[str] = set()
    for f in filas:
        row = dict(f)
        u = str(row.get("medicine_url") or "").strip()
        ov = by_url.get(u)
        if ov:
            row["overview_pdf_es"] = ov.get("pdf_url") or ""
            row["overview_es"] = {
                "indicaciones": ov.get("indicaciones") or "",
                "secciones": ov.get("secciones") or {},
                "titulos": ov.get("titulos") or {},
                "pdf_url": ov.get("pdf_url") or "",
            }
            ind = str(ov.get("indicaciones") or "").strip()
            if ind:
                row["therapeutic_indication_es"] = ind
                row["therapeutic_indication_es_fuente"] = "epar_overview_es"
                if ind not in seen_ind:
                    seen_ind.add(ind)
                    inds_es.append(ind)
        out_filas.append(row)

    if info is None:
        return None, out_filas
    info2 = dict(info)
    if inds_es:
        info2["indicaciones_es"] = inds_es
        info2["indicaciones_es_fuente"] = "epar_overview_es"
    info2["overviews_es"] = len(by_url)
    return info2, out_filas


if __name__ == "__main__":
    test = "https://www.ema.europa.eu/en/medicines/human/EPAR/orkambi"
    print(json.dumps(obtener_overview_es(test), ensure_ascii=False, indent=2)[:3000])
