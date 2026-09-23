"""Normaliza concentración y presentación en campos estructurados."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def _norm(texto: Any) -> str:
    s = unicodedata.normalize("NFKD", str(texto or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.replace(",", ".").lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _fmt_num(txt: str) -> str:
    s = str(txt).replace(",", ".").strip()
    try:
        n = float(s)
    except ValueError:
        return s
    if abs(n - round(n)) < 1e-9:
        return str(int(round(n)))
    return f"{n:.4f}".rstrip("0").rstrip(".")


def parse_concentracion(concentracion: Any, nombre: Any = None) -> dict[str, str | None]:
    t = _norm(concentracion) or _norm(nombre)
    if not t:
        return {"cantidad_concentracion": None, "unidad_concentracion": None}

    m = re.search(r"(\d+(?:\.\d+)?)\s*(mg|mcg|ug|ui|iu|g|ml)\s*/\s*(\d+(?:\.\d+)?)\s*(ml|mg|g)", t, re.I)
    if m:
        unidad_1 = m.group(2).lower().replace("ug", "mcg").replace("iu", "ui")
        unidad_2 = m.group(4).lower()
        return {
            "cantidad_concentracion": f"{_fmt_num(m.group(1))}/{_fmt_num(m.group(3))}",
            "unidad_concentracion": f"{unidad_1}/{unidad_2}",
        }

    m = re.search(r"(\d+(?:\.\d+)?)\s*(mg|mcg|ug|ui|iu|mu|g|ml|%)\b", t, re.I)
    if m:
        unidad = m.group(2).lower().replace("ug", "mcg").replace("iu", "ui")
        return {
            "cantidad_concentracion": _fmt_num(m.group(1)),
            "unidad_concentracion": unidad,
        }

    return {"cantidad_concentracion": None, "unidad_concentracion": None}


def _tipo_presentacion(texto: str) -> str | None:
    formas = [
        ("solucion inyectable", "Solución inyectable"),
        ("jeringa prellenada", "Jeringa prellenada"),
        ("jeringa precargada", "Jeringa prellenada"),
        ("pluma", "Pluma"),
        ("frasco ampolla", "Frasco-ampolla"),
        ("frasco ampula", "Frasco-ampolla"),
        ("fco amp", "Frasco-ampolla"),
        ("vial", "Vial"),
        ("ampolla", "Ampolla"),
        ("amp", "Ampolla"),
        ("capsulas", "Cápsulas"),
        ("capsula", "Cápsulas"),
        ("caps", "Cápsulas"),
        ("comprimidos", "Comprimidos"),
        ("comprimido", "Comprimidos"),
        ("comp", "Comprimidos"),
        ("tabletas", "Tabletas"),
        ("tableta", "Tabletas"),
        ("tabs", "Tabletas"),
        ("tab", "Tabletas"),
        ("frasco", "Frasco"),
        ("caja", "Caja"),
        ("kit", "Kit"),
        ("blister", "Blister"),
        ("tubo", "Tubo"),
        ("pluma recargada", "Pluma"),
        ("polvo liofilizado", "Polvo liofilizado"),
        ("liofilizado", "Polvo liofilizado"),
        ("en polvo", "Polvo"),
        ("polvo", "Polvo"),
        ("unguento", "Ungüento"),
        ("pomada", "Ungüento"),
    ]
    for pista, std in formas:
        if re.search(rf"\b{re.escape(pista)}\b", texto):
            return std
    return None


def _es_volumen(texto: str, numero: str) -> bool:
    """Evita tomar 'x 100 ml' / 'x 5 mg' como cantidad de empaque."""
    return bool(
        re.search(
            rf"(?:^|[^\d.]){re.escape(numero)}\s*(?:ml|mg|mcg|ug|g|ui|iu)\b",
            texto,
            re.I,
        )
    )


def parse_presentacion(presentacion: Any, nombre: Any = None) -> dict[str, str | None]:
    t_pres = _norm(presentacion)
    t_nom = _norm(nombre)
    # Combinar ambos: a veces la presentación trae "x 100" y el nombre aclara "x 100 ml".
    t = " ".join(x for x in (t_pres, t_nom) if x).strip()
    if not t:
        return {
            "tipo_presentacion": None,
            "cantidad_presentacion": None,
            "alcance_presentacion": "desconocido",
        }

    tipo = _tipo_presentacion(t_pres) or _tipo_presentacion(t)
    cantidad = None
    for pat in (
        # No capturar volumen: "ampolla x 100 ml" no es lote de 100.
        # Tampoco "Zoladex 3.6mg" (x de la marca + decimal).
        r"(?<![a-z])x\s*(\d{1,4})\b(?!\.\d)\s*(?!(?:ml|mg|mcg|ug|g|ui|iu|mu)\b)",
        r"\bc/\s*(\d{1,4}(?:\.\d+)?)\s*(?!(?:ml|mg|mcg|ug|g|ui|iu|mu)\b)",
        r"\b(\d{1,4}(?:\.\d+)?)\s*(?:tabletas?|tabs?|tab|comprimidos?|comp|capsulas?|caps?|ampollas?|amp|viales?|vial|jeringas?|plumas?|frascos?|unidades?)\b",
        r"\bcaja\s*(?:de\s*)?(?:c/\s*)?(\d{1,4}(?:\.\d+)?)\b",
        # FarmaValue / títulos cortos: "Cellcept 500mg, 50" (la norma convierte ',' → '.')
        r"(?:mg|mcg|ui|iu|g)\s*[.,]\s*(\d{1,4})(?:\b|$)",
        r"[.,]\s*(\d{1,4})\s*$",
    ):
        m = re.search(pat, t, re.I)
        if not m:
            continue
        cand = _fmt_num(m.group(1))
        if _es_volumen(t, cand):
            continue
        cantidad = cand
        break

    # Formas unitarias sin conteo explícito → 1 unidad.
    if cantidad is None and tipo in {
        "Ampolla",
        "Vial",
        "Frasco-ampolla",
        "Frasco",
        "Jeringa prellenada",
        "Pluma",
        "Solución inyectable",
        "Polvo liofilizado",
        "Polvo",
    }:
        cantidad = "1"

    alcance = "desconocido"
    if re.search(r"\bkit\b", t):
        alcance = "kit"
    elif re.search(r"\bcaja\b", t):
        alcance = "caja"
    elif cantidad is not None:
        try:
            alcance = "unidad" if float(cantidad) <= 1 else "lote"
        except ValueError:
            alcance = "desconocido"
    elif tipo in {
        "Ampolla",
        "Vial",
        "Frasco-ampolla",
        "Frasco",
        "Jeringa prellenada",
        "Pluma",
        "Solución inyectable",
        "Polvo liofilizado",
        "Polvo",
        "Comprimidos",
        "Cápsulas",
        "Tabletas",
    }:
        alcance = "unidad"
        if cantidad is None and tipo in {"Comprimidos", "Cápsulas", "Tabletas"}:
            cantidad = "1"

    return {
        "tipo_presentacion": tipo,
        "cantidad_presentacion": cantidad,
        "alcance_presentacion": alcance,
    }


def es_precio_al_detalle(fila: dict[str, Any] | None = None, *textos: Any) -> bool:
    """Detecta PVP de unidad/detalle (…det, ***DET, 'detalle'), no el de la caja."""
    partes: list[str] = [str(x or "") for x in textos]
    if fila:
        for k in (
            "nombre_comercial",
            "presentacion",
            "observacion",
            "fuente_url",
            "id_producto_farmacia",
            "sku",
        ):
            partes.append(str(fila.get(k) or ""))
    blob = " ".join(partes).lower()
    if re.search(r"\b(detalle|por unidad|no caja)\b", blob):
        return True
    if "***det" in blob or re.search(r"det\b", blob):
        return True
    # Slugs típicos RD: .../xeloda-500mg-x-120compdet  o  id terminado en det
    if re.search(r"(^|[^a-z])[^/\s]*det(/|$|\s)", blob):
        return True
    return False


def enriquecer_fila_estructurada(fila: dict[str, Any]) -> dict[str, Any]:
    nombre = fila.get("nombre_comercial") or fila.get("medicamento_lista") or ""
    pres_txt = str(fila.get("presentacion") or "").strip()
    # Residuos de fichas viejas (p. ej. "x 3" por Zoladex): reparsear desde el título.
    if re.fullmatch(r"x\s*\d{1,4}", _norm(pres_txt), flags=re.I):
        pres_txt = ""
    conc = parse_concentracion(fila.get("concentracion"), nombre)
    pres = parse_presentacion(pres_txt, nombre)
    enriched = dict(fila)
    enriched.update(conc)
    enriched.update(pres)

    if es_precio_al_detalle(enriched):
        enriched["alcance_presentacion"] = "unidad"
        enriched["cantidad_presentacion"] = "1"
        pres_txt = str(enriched.get("presentacion") or "").strip()
        if pres_txt and "(detalle)" not in pres_txt.lower():
            enriched["presentacion"] = f"{pres_txt} (detalle)"[:120]
        elif not pres_txt:
            tipo = enriched.get("tipo_presentacion") or "Unidad"
            enriched["presentacion"] = f"{tipo} x 1 (detalle)"
        obs = str(enriched.get("observacion") or "").strip()
        if "detalle" not in obs.lower() and "unidad" not in obs.lower():
            enriched["observacion"] = (
                f"{obs}; Precio al detalle (unidad), no caja" if obs else "Precio al detalle (unidad), no caja"
            )
    return enriched
