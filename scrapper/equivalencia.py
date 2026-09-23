"""
Equivalencia farmacológica y de presentación entre ofertas de farmacia.

Niveles (de más estricto a más laxo):
  SAME_PRODUCT          — mismo SKU/marca/lab + dosis + presentación
  SAME_MEDICINE         — mismo principio (lista), dosis y forma equivalente (marca distinta OK)
  SAME_PRESENTATION     — además misma cantidad de unidades (comparable precio caja vs caja)
  THERAPEUTIC_EQUIVALENT — no se infiere automáticamente entre distintos n_lista
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from scrapper.estructura_producto import enriquecer_fila_estructurada, parse_concentracion

# Formas farmacológicamente equivalentes para emparejar (canónico → grupo)
_FORMA_CANON: dict[str, str] = {
    "comprimidos": "comprimido",
    "comprimido": "comprimido",
    "comp": "comprimido",
    "tabletas": "comprimido",
    "tableta": "comprimido",
    "tabs": "comprimido",
    "tab": "comprimido",
    "comprimidos revestidos": "comprimido_revestido",
    "comprimido recubierto": "comprimido_revestido",
    "comprimidos recubiertos": "comprimido_revestido",
    "tabletas recubiertas": "comprimido_revestido",
    "capsulas": "capsula",
    "capsula": "capsula",
    "caps": "capsula",
    "cap": "capsula",
    "solucion inyectable": "inyectable",
    "inyectable": "inyectable",
    "ampolla": "inyectable",
    "vial": "inyectable",
    "frasco ampolla": "inyectable",
    "frasco-ampolla": "inyectable",
    "jeringa prellenada": "inyectable",
    "jeringa": "inyectable",
    "pluma": "inyectable",
    "polvo liofilizado": "polvo_liofilizado",
    "polvo": "polvo",
    "unguento": "topico",
    "pomada": "topico",
    "crema": "topico",
    "gel": "topico",
}

_LIBERACION_RE = re.compile(
    r"\b(?:xr|sr|cr|er|mr|pr|la|lp|retard|prolongad[ao]|modified release|extended release)\b",
    re.I,
)

_VIA_ORAL = re.compile(r"\b(?:comprimid|tableta|capsula|caplet|oral|suspension oral)\b", re.I)
_VIA_INY = re.compile(r"\b(?:inyect|ampolla|vial|jeringa|pluma|solucion inyect|subcut|intraven|intramusc)\b", re.I)
_VIA_TOP = re.compile(r"\b(?:unguento|pomada|crema|gel|topico|oftalm|nasal)\b", re.I)


def _norm(texto: Any) -> str:
    s = unicodedata.normalize("NFKD", str(texto or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.replace(",", ".").lower()
    return re.sub(r"\s+", " ", s).strip()


def _fmt_num(txt: str | float | int | None) -> str | None:
    if txt is None or txt == "":
        return None
    try:
        n = float(str(txt).replace(",", "."))
    except (TypeError, ValueError):
        return str(txt).strip() or None
    if abs(n - round(n)) < 1e-9:
        return str(int(round(n)))
    return f"{n:.6f}".rstrip("0").rstrip(".")


def forma_canonica(tipo: Any, nombre: str = "") -> str | None:
    t = _norm(tipo)
    blob = f"{t} {_norm(nombre)}"
    if re.search(r"\b(revestid|recubiert)", blob):
        return "comprimido_revestido"
    if not t:
        return None
    if t in _FORMA_CANON:
        return _FORMA_CANON[t]
    for pista, canon in sorted(_FORMA_CANON.items(), key=lambda x: -len(x[0])):
        if pista in t:
            return canon
    return t or None


def formas_equivalentes(a: str | None, b: str | None) -> bool:
    ca, cb = forma_canonica(a), forma_canonica(b)
    if not ca or not cb:
        return False
    if ca == cb:
        return True
    # Comprimido simple vs revestido: NO equivalente clínicamente por defecto
    return False


def liberacion_de(*textos: Any) -> str | None:
    t = _norm(" ".join(str(x or "") for x in textos))
    if not t:
        return None
    if _LIBERACION_RE.search(t):
        return "modificada"
    return "inmediata"


def via_de(*textos: Any) -> str | None:
    t = _norm(" ".join(str(x or "") for x in textos))
    if not t:
        return None
    if _VIA_INY.search(t):
        return "parenteral"
    if _VIA_TOP.search(t):
        return "topica"
    if _VIA_ORAL.search(t):
        return "oral"
    return None


def es_combinacion(nombre_lista: str, nombre_comercial: str, principio: str | None = None) -> bool:
    blob = _norm(f"{nombre_lista} {nombre_comercial} {principio or ''}")
    if "/" in nombre_lista or "+" in nombre_lista:
        return True
    if re.search(r"\b(?:y|con|mas|\+|/)\b", blob) and re.search(
        r"\b(?:mg|mcg|ml)\b.*\b(?:mg|mcg|ml)\b", blob
    ):
        return True
    return False


def clave_concentracion(
    cantidad: Any,
    unidad: Any,
    *,
    nombre: str = "",
    concentracion_txt: str = "",
) -> str | None:
    c = _fmt_num(cantidad) if cantidad not in (None, "") else None
    u = _norm(unidad) if unidad else None
    if c and u:
        return f"{c} {u}"
    conc = parse_concentracion(concentracion_txt, nombre)
    c2 = conc.get("cantidad_concentracion")
    u2 = conc.get("unidad_concentracion")
    if c2 and u2:
        return f"{c2} {u2}"
    return None


def cantidad_unidades(fila: dict[str, Any]) -> int | None:
    raw = fila.get("cantidad_presentacion")
    if raw not in (None, ""):
        try:
            n = int(float(str(raw).replace(",", ".")))
            return n if n > 0 else None
        except (TypeError, ValueError):
            pass
    alcance = _norm(fila.get("alcance_presentacion"))
    if alcance == "unidad":
        return 1
    return None


def precio_por_unidad_usd(fila: dict[str, Any], precio_usd: float | None) -> float | None:
    if precio_usd is None or precio_usd <= 0:
        return None
    n = cantidad_unidades(fila)
    if not n:
        return None
    return round(precio_usd / n, 6)


@dataclass
class PerfilProducto:
    n_lista: int | None
    medicamento_lista: str
    nombre_comercial: str
    laboratorio: str | None
    marca: str | None
    concentracion: str | None
    forma: str | None
    cantidad: int | None
    alcance: str | None
    liberacion: str | None
    via: str | None
    es_combinacion: bool
    calidad: str | None
    incompleto: bool = False

    @property
    def clave_medicina(self) -> str | None:
        if not self.concentracion or not self.forma:
            return None
        lib = self.liberacion or "inmediata"
        via = self.via or "?"
        return f"{self.n_lista}|{self.concentracion}|{self.forma}|{lib}|{via}"

    @property
    def clave_presentacion(self) -> str | None:
        km = self.clave_medicina
        if not km or not self.cantidad:
            return None
        return f"{km}|{self.cantidad}"


@dataclass
class ResultadoEquivalencia:
    same_product: bool = False
    same_medicine: bool = False
    same_presentation: bool = False
    therapeutic_equivalent: bool = False
    match_level: str = "NO_MATCH"
    confidence: float = 0.0
    review_required: bool = False
    reasons: list[str] = field(default_factory=list)
    precio_por_unidad_a: float | None = None
    precio_por_unidad_b: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "same_product": self.same_product,
            "same_medicine": self.same_medicine,
            "same_presentation": self.same_presentation,
            "therapeutic_equivalent": self.therapeutic_equivalent,
            "match_level": self.match_level,
            "confidence": round(self.confidence, 3),
            "review_required": self.review_required,
            "reasons": self.reasons,
            "precio_por_unidad_a": self.precio_por_unidad_a,
            "precio_por_unidad_b": self.precio_por_unidad_b,
        }


def _marca_de(nombre: str) -> str | None:
    t = str(nombre or "").strip()
    if not t:
        return None
    return t.split()[0][:80]


def perfil_desde_fila(fila: dict[str, Any]) -> PerfilProducto:
    enriched = enriquecer_fila_estructurada(dict(fila))
    for k in (
        "tipo_presentacion",
        "cantidad_presentacion",
        "alcance_presentacion",
        "cantidad_concentracion",
        "unidad_concentracion",
        "concentracion",
        "laboratorio",
        "calidad",
        "n_lista",
        "medicamento_lista",
        "nombre_comercial",
        "principio_activo",
    ):
        if fila.get(k) not in (None, "") and enriched.get(k) in (None, ""):
            enriched[k] = fila[k]

    nombre = str(enriched.get("nombre_comercial") or "")
    med = str(enriched.get("medicamento_lista") or "")
    n_lista = enriched.get("n_lista")
    try:
        n_lista = int(n_lista) if n_lista is not None else None
    except (TypeError, ValueError):
        n_lista = None

    forma_raw = enriched.get("tipo_presentacion")
    forma = forma_canonica(forma_raw, nombre)
    conc = clave_concentracion(
        enriched.get("cantidad_concentracion"),
        enriched.get("unidad_concentracion"),
        nombre=nombre,
        concentracion_txt=str(enriched.get("concentracion") or ""),
    )
    cant = cantidad_unidades(enriched)
    lib = liberacion_de(nombre, enriched.get("presentacion"), forma_raw)
    via = via_de(nombre, forma_raw, enriched.get("presentacion"))
    combo = es_combinacion(med, nombre, enriched.get("principio_activo"))
    calidad = str(enriched.get("calidad") or "ok")
    incompleto = not conc or not forma or not cant

    if calidad not in (None, "", "ok"):
        incompleto = True

    return PerfilProducto(
        n_lista=n_lista,
        medicamento_lista=med,
        nombre_comercial=nombre,
        laboratorio=(str(enriched.get("laboratorio") or "").strip() or None),
        marca=_marca_de(nombre),
        concentracion=conc,
        forma=forma,
        cantidad=cant,
        alcance=str(enriched.get("alcance_presentacion") or "") or None,
        liberacion=lib,
        via=via,
        es_combinacion=combo,
        calidad=calidad,
        incompleto=incompleto,
    )


def comparar(a: dict[str, Any] | PerfilProducto, b: dict[str, Any] | PerfilProducto) -> ResultadoEquivalencia:
    pa = a if isinstance(a, PerfilProducto) else perfil_desde_fila(a)
    pb = b if isinstance(b, PerfilProducto) else perfil_desde_fila(b)
    out = ResultadoEquivalencia()

    if pa.n_lista is not None and pb.n_lista is not None and pa.n_lista != pb.n_lista:
        out.reasons.append("distinto principio de lista (n_lista)")
        out.match_level = "NO_MATCH"
        out.therapeutic_equivalent = False
        return out

    if pa.calidad not in (None, "", "ok") or pb.calidad not in (None, "", "ok"):
        out.review_required = True
        out.reasons.append("calidad marcada para revisión")

    if pa.incompleto or pb.incompleto:
        out.review_required = True
        out.reasons.append("información insuficiente de dosis o presentación")
        out.confidence = 0.25
        out.match_level = "REVIEW_REQUIRED"
        return out

    if pa.es_combinacion != pb.es_combinacion:
        out.reasons.append("uno es combinación y el otro monofármaco")
        out.match_level = "NO_MATCH"
        return out

    if pa.concentracion != pb.concentracion:
        out.reasons.append(f"dosis distinta ({pa.concentracion} vs {pb.concentracion})")
        out.match_level = "NO_MATCH"
        return out

    if not formas_equivalentes(pa.forma, pb.forma):
        out.reasons.append(f"forma distinta ({pa.forma} vs {pb.forma})")
        out.match_level = "NO_MATCH"
        return out

    if pa.liberacion != pb.liberacion:
        out.reasons.append("liberación distinta")
        out.match_level = "NO_MATCH"
        return out

    if pa.via and pb.via and pa.via != pb.via:
        out.reasons.append("vía de administración distinta")
        out.match_level = "NO_MATCH"
        return out

    out.same_medicine = True
    out.confidence = 0.85

    if pa.cantidad and pb.cantidad and pa.cantidad == pb.cantidad:
        out.same_presentation = True
        out.confidence = 0.95
    else:
        out.reasons.append(
            f"cantidad distinta ({pa.cantidad or '?'} vs {pb.cantidad or '?'}) — mismo medicamento, distinta presentación"
        )

    misma_marca = pa.marca and pb.marca and _norm(pa.marca) == _norm(pb.marca)
    mismo_lab = pa.laboratorio and pb.laboratorio and _norm(pa.laboratorio) == _norm(pb.laboratorio)
    if out.same_presentation and misma_marca and (mismo_lab or not pa.laboratorio or not pb.laboratorio):
        out.same_product = True
        out.confidence = 1.0
        out.match_level = "SAME_PRODUCT"
    elif out.same_presentation:
        out.match_level = "SAME_MEDICINE"
        out.reasons.append("marca o laboratorio distinto")
    else:
        out.match_level = "SAME_MEDICINE"

    if isinstance(a, dict) and isinstance(b, dict):
        pu_a = precio_por_unidad_usd(a, a.get("precio_usd") or a.get("precio"))
        pu_b = precio_por_unidad_usd(b, b.get("precio_usd") or b.get("precio"))
        out.precio_por_unidad_a = pu_a
        out.precio_por_unidad_b = pu_b

    return out


def clave_presentacion_fila(fila: dict[str, Any]) -> str | None:
    return perfil_desde_fila(fila).clave_presentacion


def clave_medicina_fila(fila: dict[str, Any]) -> str | None:
    return perfil_desde_fila(fila).clave_medicina
