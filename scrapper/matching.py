"""Cruce de un producto de farmacia con la lista DAMAC/FOMAC."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from lista import MEDICAMENTOS

EXCLUDES: dict[str, list[str]] = {
    "Filgrastim": ["pegfilgrastim", "pegfilgastrim", "neulasta", "neulastim"],
    "Bevacizumab": ["tavastina"],
    "Trastuzumab": ["pertuzumab", "phesgo"],
    "Pertuzumab": ["phesgo", "trastuzumab"],
    "Interferón beta 1A": ["beta-1b", "beta 1b", "beta 1-b", "1b", "alanina", "beta alanina"],
    "Interferón beta 1B": ["beta-1a", "beta 1a", "beta 1-a", "alanina", "beta alanina"],
    "Micofenolato mofetilo": ["sodium", "sodico", "myfortic"],
    "Micofenolato sódico": ["mofetil", "mofetilo", "cellcept"],
    "Factor IX": ["factor viii", "factor 8", "octocog"],
    "Factor de coagulación VIII": ["factor ix", "factor 9", "nonacog", "feiba"],
    "Factor de crecimiento epidérmico humano recombinante": [
        "velvet", "antler", "velvesterone", "sesderma", "rejuvenesc",
    ],
    "Ciclosporina": ["restasis", "oftalm", "ocular"],
    "Valganciclovir": ["valaciclovir", "valacyclovir"],
}


def norm(texto: Any) -> str:
    s = "" if texto is None else str(texto)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def _alias_en_texto(alias: str, h: str, *, nombre: str) -> bool:
    a = norm(alias)
    if len(a) < 4:
        return False
    if re.search(rf"(^| ){re.escape(a)}( |$)", h):
        if nombre == "Filgrastim" and "pegfilgrastim" in h:
            return False
        return True
    if len(a) >= 6 and re.search(rf"(^| ){re.escape(a)}[a-z0-9]*( |$)", h):
        if nombre == "Filgrastim" and "pegfilgrastim" in h:
            return False
        return True
    if a.endswith(("mab", "nib", "mib", "lib")):
        if re.search(rf"(^| ){re.escape(a)}e( |$)", h):
            return True
    return False


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
    if nombre == "Pertuzumab/Trastuzumab":
        return "phesgo" in h or ("pertuzumab" in h and "trastuzumab" in h)
    if nombre == "Sofosbuvir/Velpatasvir":
        return "epclusa" in h or ("sofosbuvir" in h and "velpatasvir" in h)
    for alias in med["aliases"]:
        if _alias_en_texto(alias, h, nombre=nombre):
            return True
    # Marcas de la guía (fase 2): tipuric, sandimmun, etc. suelen ir solo en marcas.py
    try:
        from marcas import aliases_de_marcas

        for alias in aliases_de_marcas(int(med["n"])):
            if _alias_en_texto(alias, h, nombre=nombre):
                return True
    except Exception:
        pass
    return False


def medicamentos_que_pegan(haystack: str) -> list[dict[str, Any]]:
    return [m for m in MEDICAMENTOS if coincide(haystack, m)]


def principios_txt(p: dict[str, Any]) -> str:
    pa = p.get("principios_activos") or []
    if isinstance(pa, list):
        return ", ".join(str(x) for x in pa if x)
    return str(pa or "")


def dosaje_txt(p: dict[str, Any]) -> str:
    dosajes = p.get("principios_activos_con_dosaje") or []
    partes: list[str] = []
    if isinstance(dosajes, list):
        for d in dosajes:
            if not isinstance(d, dict):
                partes.append(str(d))
                continue
            nom = d.get("nombre") or d.get("principio_activo") or d.get("principio") or ""
            dos = d.get("dosaje") or d.get("concentracion") or d.get("dosis") or ""
            linea = " ".join(str(x) for x in (nom, dos) if x).strip()
            if linea:
                partes.append(linea)
    return "; ".join(partes)


def blob_producto(p: dict[str, Any]) -> str:
    pa = p.get("principios_activos") or []
    pa_txt = " ".join(str(x) for x in pa) if isinstance(pa, list) else str(pa)
    dosajes = p.get("principios_activos_con_dosaje") or []
    dos_txt = json.dumps(dosajes, ensure_ascii=False) if dosajes else ""
    return " ".join(
        str(x or "")
        for x in (
            p.get("nombre"),
            pa_txt,
            dos_txt,
            p.get("tipo_presentacion"),
            p.get("laboratorio"),
            p.get("palabras_clave"),
        )
    )


def _med_por_nombre(nombre: str) -> dict[str, Any] | None:
    n = norm(nombre)
    for m in MEDICAMENTOS:
        if norm(m["nombre"]) == n:
            return m
    return None


def clasificar(med: dict[str, Any], p: dict[str, Any]) -> tuple[dict[str, Any], str, str | None]:
    """Ajusta lista si hace falta y marca calidad ok/revisar."""
    blob = norm(
        " ".join(
            str(x or "")
            for x in (
                p.get("nombre"),
                principios_txt(p),
                dosaje_txt(p),
                p.get("tipo_presentacion"),
            )
        )
    )
    nombre = str(med["nombre"])

    if nombre == "Micofenolato mofetilo" and re.search(r"360\s*mg", blob):
        sodico = _med_por_nombre("Micofenolato sódico")
        if sodico:
            return sodico, "revisar", "360 mg suele ser micofenolato sódico (no mofetilo 500 mg)"

    if nombre == "Inmunoglobulina humana":
        if any(
            x in blob
            for x in (
                "anti d", "rho", "rhoclone", "rhogam", "rhophylac",
                "tetan", "antitetan", "igantet", "hyperhep", "hep b", "hepatitis",
            )
        ):
            return med, "revisar", "Inmunoglobulina hiperinmune (anti-D, tetánica o hepatitis), no IVIG"

    if nombre == "Pirfenidona" and any(x in blob for x in ("gel", "unguento", "crema", "kitos")):
        return med, "revisar", "Presentación tópica, no Esbriet oral"

    if nombre == "Palmitato de paliperidona":
        oral = any(x in blob for x in ("comprimido", "tableta", "capsula"))
        depot = any(x in blob for x in ("sustenna", "trinza", "xeplion", "inyect", "injet", "seringa", "jeringa"))
        if oral and not depot:
            return med, "revisar", "Paliperidona oral, no palmitato de depósito"

    if nombre == "Palonosetrón" and any(x in blob for x in ("akynzeo", "netupitant", "netupitanto")):
        return med, "revisar", "Combinación palonosetrón + netupitant (Akynzeo), no Aloxi solo"

    if nombre == "Tacrolimus":
        topico = any(x in blob for x in ("unguento", "ung", "crema", "tubo", "dermic", "pomada", "0 03", "0 1"))
        oral = any(x in blob for x in ("capsula", "tableta", "comprimido", "1mg", "1 mg"))
        if topico and not oral:
            return med, "revisar", "Tacrolimus tópico (ungüento), no sistémico"

    return med, "ok", None
