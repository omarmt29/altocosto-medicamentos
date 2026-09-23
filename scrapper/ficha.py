"""Parte nombre comercial en principio activo, concentración y presentación."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

LABS = (
    "Sandoz", "Novartis", "Roche", "Abbott", "Abbvie", "AstraZeneca", "Astra Zeneca",
    "Pfizer", "Lilly", "Bayer", "Sanofi", "GSK", "MSD", "Merck", "Janssen",
    "LAM", "Varifarma", "Microsules", "Biosidus", "Roemmers", "Roemmer",
    "Alfa", "Feltrex", "Calox", "MK", "Procaps", "Pharmatech", "Asofarma",
    "Euro", "Sued", "Rowe", "Behring", "Grifols", "Kedrion", "BSV",
    "EMS", "Eurofarma", "Aché", "Ache", "Medley", "Blau", "Cristalia", "Cristália",
    "Libbs", "Zodiac", "Hypera", "Neo Quimica", "Neoquímica", "Germed",
)

FORMAS: list[tuple[str, str]] = [
    ("solucion inyectable", "Solución inyectable"),
    ("sol iny", "Solución inyectable"),
    ("jeringa prellenada", "Jeringa prellenada"),
    ("jeringa precargada", "Jeringa prellenada"),
    ("jeringa prell", "Jeringa prellenada"),
    ("jer prell", "Jeringa prellenada"),
    ("jga prelle", "Jeringa prellenada"),
    ("jga prell", "Jeringa prellenada"),
    ("pluma precargada", "Pluma"),
    ("pluma recargada", "Pluma"),
    ("pluma prec", "Pluma"),
    ("plumas", "Pluma"),
    ("pluma", "Pluma"),
    ("fco amp", "Frasco-ampolla"),
    ("frasco ampula", "Frasco-ampolla"),
    ("frasco ampolla", "Frasco-ampolla"),
    ("frasco ampola", "Frasco-ampolla"),
    ("frasco-ampola", "Frasco-ampolla"),
    ("seringa preenchida", "Jeringa prellenada"),
    ("seringa precargada", "Jeringa prellenada"),
    ("seringa", "Jeringa"),
    ("solucao injetavel", "Solución inyectable"),
    ("suspensao injetavel", "Suspensión inyectable"),
    ("ampolla", "Ampolla"),
    ("ampollas", "Ampolla"),
    ("amp", "Ampolla"),
    ("viales", "Vial"),
    ("vial", "Vial"),
    ("inyectable", "Inyectable"),
    ("caneta preenchida", "Pluma"),
    ("caneta", "Pluma"),
    ("capsulas", "Cápsulas"),
    ("comprimidos", "Comprimidos"),
    ("comprimido", "Comprimidos"),
    ("compr", "Comprimidos"),
    ("comp", "Comprimidos"),
    ("tabletas", "Tabletas"),
    ("tableta", "Tabletas"),
    ("tabs", "Tabletas"),
    ("tab", "Tabletas"),
    ("capsulas", "Cápsulas"),
    ("capsula", "Cápsulas"),
    ("caps", "Cápsulas"),
    ("cap", "Cápsulas"),
    ("capletas", "Capletas"),
    ("frasco", "Frasco"),
    ("tubo", "Tubo"),
    ("caja", "Caja"),
    ("unguento", "Ungüento"),
    ("pomada", "Ungüento"),
    ("crema", "Crema"),
    ("gel", "Gel"),
    ("polvo liofilizado", "Polvo liofilizado"),
    ("liofilizado", "Polvo liofilizado"),
    ("en polvo", "Polvo"),
    ("polvo", "Polvo"),
]


def _norm(texto: str) -> str:
    s = unicodedata.normalize("NFKD", texto or "")
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.replace(",", ".")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _fmt_num(n: str) -> str:
    n = n.replace(",", ".")
    try:
        x = float(n)
    except ValueError:
        return n
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.4f}".rstrip("0").rstrip(".")


def concentracion_de(nombre: str) -> str | None:
    t = _norm(nombre)
    patrones = [
        r"(\d+(?:\.\d+)?)\s*(mg|mcg|ug|µg|ui|iu)\s*/\s*(\d+(?:\.\d+)?)\s*(ml|mg)",
        r"(\d+(?:\.\d+)?)\s*(mg|mcg|ug|µg|ui|iu)\s*/\s*(ml)",
        r"(\d+(?:\.\d+)?)\s*%",
        r"(\d+(?:\.\d+)?)\s*(mg|mcg|ug|µg|ui|iu|mu|g|gr)\b",
    ]
    m = re.search(patrones[0], t, re.I)
    if m:
        return f"{_fmt_num(m.group(1))} {m.group(2).lower()}/{_fmt_num(m.group(3))} {m.group(4).lower()}"
    m = re.search(patrones[1], t, re.I)
    if m:
        return f"{_fmt_num(m.group(1))} {m.group(2).lower()}/ml"
    m = re.search(patrones[2], t, re.I)
    if m:
        return f"{_fmt_num(m.group(1))} %"
    m = re.search(patrones[3], t, re.I)
    if m:
        uni = m.group(2).lower().replace("ug", "mcg").replace("µg", "mcg").replace("iu", "ui").replace("gr", "g")
        return f"{_fmt_num(m.group(1))} {uni}"
    return None


def forma_de(nombre: str) -> str | None:
    t = _norm(nombre).lower()
    t = re.sub(r"[^a-z0-9./% ]+", " ", t)
    for pista, std in FORMAS:
        if re.search(rf"\b{re.escape(pista)}\b", t):
            return std
    return None


def unidades_de(nombre: str) -> tuple[int | None, str | None]:
    t = _norm(nombre)
    t = re.sub(r"\*{2,}.*$", "", t)
    # Pegados frecuentes en farmacias.do: "x 50cap", "120comp", "28tab"
    t = re.sub(
        r"(?i)(\d)\s*(cap(?:sulas?)?|comp(?:rimidos?)?|tab(?:letas?)?|tabs?|amp(?:ollas?)?|viales?|vial)\b",
        r"\1 \2",
        t,
    )
    patrones = [
        r"c/\s*(\d{1,4})\s*(fco(?:\s*amp)?|frasco[- ]ampulas?|frascos?(?:\s+amp)?|jga|jer(?:inga)?|ampollas?|amp\.?|viales?|vial|tabletas?|tabs?|tab\b|jeringas?|plumas?)\b",
        r"x\s*(\d{1,4})\s*(amp\.?\s*vial|ampollas?|amp\.?|viales?|vial|tabletas?|tabs?|comprimidos?|compr\.?|comp\.?|capsulas?|caps?|cap\b|capletas?|frascos?|unidades?|jeringas?|plumas?|ml)\b",
        r"com\s+(\d{1,4})\s*(capsulas?|comprimidos?(?:\s+revestidos?)?|cpr|cp\b|comp\b|caps?|tabletas?|tabs?|seringas?|canetas?|frasco[- ]ampolas?)\b",
        r"(\d{1,4})\s*(ampollas?|amp\.?|viales?|vial|tabletas?|tabs?|comprimidos?|compr\.?|comp\.?|capsulas?|caps?|cap\b|seringas?|canetas?|jeringas?|plumas?|frasco[- ]ampolas?)\b",
        r"caja\s*(?:de\s*)?(?:c/\s*)?(\d{1,4})\b",
        r"c/\s*(\d{1,4})\b",
        # "x 30" empaque, no la x final de "Zoladex 3.6mg".
        r"(?<![a-z])x\s*(\d{1,4})\b(?!\.\d)",
    ]
    for pat in patrones:
        m = re.search(pat, t, re.I)
        if not m:
            continue
        n = int(m.group(1))
        if not 1 <= n <= 500:
            continue
        forma = forma_de(m.group(2) if m.lastindex and m.lastindex >= 2 else t) or forma_de(t)
        return n, forma
    if re.search(r"\b(vial|viales)\b", t, re.I):
        return 1, forma_de(t) or "Vial"
    if re.search(r"\b(amp|ampolla)\b", t, re.I):
        return 1, forma_de(t) or "Ampolla"
    if re.search(r"\bpluma\b", t, re.I):
        return 1, "Pluma"
    return None, forma_de(t)


def laboratorio_de(nombre: str) -> str | None:
    t = _norm(nombre)
    for lab in LABS:
        if re.search(rf"\b{re.escape(lab)}\b", t, re.I):
            return lab
    return None


def presentacion_de(nombre: str, detalle: bool = False) -> str | None:
    n, forma = unidades_de(nombre)
    if not forma and concentracion_de(nombre) and re.search(r"/ml", concentracion_de(nombre) or "", re.I):
        forma = "Solución"
    if not forma and not n:
        return None
    if n and forma:
        base = f"{forma} x {n}"
    elif forma:
        base = forma
    else:
        base = f"x {n}"
    if detalle:
        base += " (detalle)"
    return base[:120]


def parse_ficha(nombre: str, med: dict[str, Any] | None = None, *, detalle: bool = False) -> dict[str, str | None]:
    """
    principio_activo = molécula de la lista (para filtrar igual en todos los países).
    concentracion / presentacion = lo que dice el envase de esa farmacia.
    """
    # farmacias.do a veces pega sufijos: Comprimidosac, Prellenadaac-7640…
    nombre_limpio = re.sub(r"(?i)\bac-?\d{8,}\b", " ", nombre or "")
    nombre_limpio = re.sub(
        r"(?i)\b(comprimidos?|tabletas?|capsulas?|jeringa\s+prellenada|pluma\s+recargada)ac\b",
        r"\1",
        nombre_limpio,
    )
    nombre_limpio = re.sub(r"\s+", " ", nombre_limpio).strip()

    pa = str(med["nombre"]) if med else None
    conc = concentracion_de(nombre_limpio)
    pres = presentacion_de(nombre_limpio, detalle=detalle)
    obs = None
    blob = _norm(nombre_limpio).lower()
    # Onicit inyectable sin mg en el título: envase estándar Aloxi/Onicit 0.25 mg ampolla.
    if not conc and re.search(r"\bonicit\b", blob) and re.search(r"\b(inyect|amp)", blob):
        conc = "0.25 mg"
        pres = pres or "Ampolla x 1"
        obs = "Dosis no venía en el título; Onicit inyectable ampolla es 0.25 mg"
    return {
        "principio_activo": pa[:500] if pa else None,
        "concentracion": conc,
        "presentacion": pres,
        "laboratorio": laboratorio_de(nombre_limpio),
        "observacion_ficha": obs,
    }
