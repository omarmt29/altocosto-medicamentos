"""Traducción EN→ES con caché en disco (para indicaciones FDA/EMA).

Usa el endpoint gratuito no oficial de Google Translate vía POST
(el GET suele devolver 429 / fallar con textos largos).
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "cache" / "traducciones"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
CACHE_VERSION = "v5"
GOOGLE_URL = "https://translate.googleapis.com/translate_a/single"


def _key(texto: str, fuente: str, destino: str) -> str:
    raw = f"{CACHE_VERSION}|{fuente}|{destino}|{texto}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def _leer_cache(key: str) -> str | None:
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        txt = data.get("texto")
        return str(txt) if txt else None
    except Exception:
        return None


def _guardar_cache(key: str, texto: str, fuente: str, destino: str) -> None:
    path = _cache_path(key)
    path.write_text(
        json.dumps(
            {
                "fuente": fuente,
                "destino": destino,
                "texto": texto,
                "ts": time.time(),
                "ver": CACHE_VERSION,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _parece_ingles(texto: str) -> bool:
    t = texto or ""
    if len(t) < 20:
        return False
    markers = [
        r"\bis indicated for\b",
        r"\bare indicated for\b",
        r"\bINDICATIONS AND USAGE\b",
        r"\bWarnings and Precautions\b",
        r"\bpatients of age and older\b",
        r"\bTreatment of\b",
        r"\bthe treatment of\b",
        r"\bReducing signs and symptoms\b",
        r"\bin combination with\b",
        r"\binadequate response\b",
        r"\bdisease-modifying\b",
        r"\bPlease refer to\b",
        r"\bmoderate to severe\b",
        r"\brheumatoid arthritis\b",
        r"\bactive polyarticular\b",
        r"\badult patients\b",
    ]
    hits = sum(1 for p in markers if re.search(p, t, re.I))
    words = re.findall(r"[A-Za-z]{3,}", t)
    if not words:
        return False
    en = sum(
        1
        for w in words
        if w.lower()
        in {
            "the",
            "and",
            "for",
            "with",
            "patients",
            "treatment",
            "indicated",
            "adult",
            "pediatric",
            "moderate",
            "severe",
            "reducing",
            "symptoms",
            "active",
            "when",
            "response",
            "including",
            "combination",
            "methotrexate",
            "please",
            "refer",
            "product",
            "information",
            "arthritis",
            "rheumatoid",
            "juvenile",
            "psoriatic",
            "ulcerative",
            "colitis",
            "crohn",
            "disease",
        }
    )
    return hits >= 1 or (en / max(len(words), 1)) > 0.05


def _fragmentos_ingles(texto: str) -> list[str]:
    """Extrae trozos que aún parecen inglés para una segunda pasada."""
    t = texto or ""
    frags: list[str] = []
    # oraciones / cláusulas
    for piece in re.split(r"(?<=[\.\n;:])\s+|\s+[•·]\s+", t):
        p = piece.strip()
        if len(p) >= 24 and _parece_ingles(p):
            frags.append(p)
    # frases típicas sueltas
    for m in re.finditer(
        r"\b(?:moderate to severe|the treatment of|in combination with|"
        r"rheumatoid arthritis|juvenile idiopathic arthritis|"
        r"psoriatic arthritis|ulcerative colitis|Crohn'?s disease|"
        r"adult patients|inadequate response)[^.\n]{0,120}",
        t,
        flags=re.I,
    ):
        frags.append(m.group(0).strip())
    # dedupe preservando orden
    seen: set[str] = set()
    out: list[str] = []
    for f in frags:
        k = f.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(f)
    return out[:24]


def _chunk(texto: str, size: int) -> list[str]:
    texto = texto.strip()
    if not texto:
        return []
    if len(texto) <= size:
        return [texto]
    parts: list[str] = []
    buf = ""
    piezas = re.split(r"(?<=[\.\n;•:])\s+", texto)
    for para in piezas:
        if not para:
            continue
        if len(buf) + len(para) + 1 <= size:
            buf = f"{buf} {para}".strip() if buf else para
            continue
        if buf:
            parts.append(buf)
            buf = ""
        while len(para) > size:
            parts.append(para[:size])
            para = para[size:]
        buf = para
    if buf:
        parts.append(buf)
    return parts


def _parse_google(data: Any) -> str | None:
    if not isinstance(data, list) or not data or not isinstance(data[0], list):
        return None
    out: list[str] = []
    for piece in data[0]:
        if isinstance(piece, list) and piece and isinstance(piece[0], str):
            out.append(piece[0])
    return "".join(out) if out else None


def _google(chunk: str, fuente: str, destino: str, sess: requests.Session) -> str | None:
    """Google Translate gratis (client=gtx) vía POST — más estable que GET."""
    payload = {
        "client": "gtx",
        "sl": fuente,
        "tl": destino,
        "dt": "t",
        "q": chunk,
    }
    headers = {
        "User-Agent": UA,
        "Accept": "application/json,text/plain,*/*",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    }
    for attempt in range(3):
        try:
            r = sess.post(
                GOOGLE_URL,
                data=payload,
                headers=headers,
                timeout=25,
                allow_redirects=False,
            )
        except requests.RequestException:
            time.sleep(0.4 * (attempt + 1))
            continue
        if r.status_code in (301, 302, 303, 307, 308, 429):
            time.sleep(0.8 * (attempt + 1))
            continue
        if r.status_code >= 400:
            return None
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "json" not in ctype and not (r.text or "").lstrip().startswith("["):
            return None
        try:
            data = r.json()
        except Exception:
            return None
        out = _parse_google(data)
        if out and out.strip():
            return out.strip()
        time.sleep(0.25 * (attempt + 1))
    return None


def _mymemory(chunk: str, fuente: str, destino: str, sess: requests.Session) -> str | None:
    from urllib.parse import quote

    url = (
        "https://api.mymemory.translated.net/get"
        f"?q={quote(chunk[:450])}&langpair={quote(fuente)}|{quote(destino)}"
    )
    try:
        r = sess.get(url, timeout=30, headers={"User-Agent": UA})
    except requests.RequestException:
        return None
    if r.status_code >= 400:
        return None
    try:
        data = r.json()
    except Exception:
        return None
    txt = ((data or {}).get("responseData") or {}).get("translatedText")
    if not txt or "MYMEMORY WARNING" in str(txt).upper():
        return None
    return str(txt).strip()


def _traducir_chunk(chunk: str, fuente: str, destino: str, sess: requests.Session) -> str:
    out = _google(chunk, fuente, destino, sess)
    if out and out.strip():
        # si Google devolvió casi lo mismo (fallo soft), reintentar una vez
        if _parece_ingles(out) and len(chunk) > 60:
            time.sleep(0.8)
            out2 = _google(chunk, fuente, destino, sess)
            if out2 and not _parece_ingles(out2):
                return out2
            # fallback troceado más fino
            fine = _chunk(chunk, 700)
            if len(fine) > 1:
                pieces = []
                for i, ch in enumerate(fine):
                    piece = _google(ch, fuente, destino, sess) or _mymemory(ch, fuente, destino, sess) or ch
                    pieces.append(piece)
                    if i < len(fine) - 1:
                        time.sleep(0.2)
                joined = " ".join(pieces).strip()
                if joined and not _parece_ingles(joined):
                    return joined
        return out

    fine = _chunk(chunk, 420)
    pieces: list[str] = []
    for i, ch in enumerate(fine):
        mm = _mymemory(ch, fuente, destino, sess)
        pieces.append(mm if mm else ch)
        if i < len(fine) - 1:
            time.sleep(0.15)
    return " ".join(pieces).strip() or chunk


def _post_limpieza(texto: str) -> str:
    t = texto or ""
    reps = [
        (r"(?i)^\s*\d*\s*INDICATIONS AND USAGE\s*", "INDICACIONES Y USO\n"),
        (r"(?i)\bINDICATIONS AND USAGE\b", "INDICACIONES Y USO"),
        (r"(?i)\bWarnings and Precautions\b", "Advertencias y precauciones"),
        (r"(?i)\bsee Warnings and Precautions\b", "ver Advertencias y precauciones"),
        (r"(?i)\bage and older\b", "años de edad y mayores"),
        (r"(?i)\bpediatric patients\b", "pacientes pediátricos"),
        (r"(?i)\badult patients\b", "pacientes adultos"),
        (r"(?i)\bis indicated for\b", "está indicado para"),
        (r"(?i)\bare indicated for\b", "están indicados para"),
        (r"(?i)\bthe treatment of\b", "el tratamiento de"),
        (r"(?i)\bin combination with\b", "en combinación con"),
        (r"(?i)\bPlease refer to the product information document\.?\b", "Consulte el documento de información del producto."),
    ]
    for pat, rep in reps:
        t = re.sub(pat, rep, t)
    t = re.sub(r"(?i)\bin pacientes\b", "en pacientes", t)
    t = re.sub(r"\bde de\b", "de", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


# MeSH / áreas terapéuticas EMA (EN → ES). Claves en minúsculas.
AREAS_MESH_ES: dict[str, str] = {
    "acromegaly": "Acromegalia",
    "amyotrophic lateral sclerosis": "Esclerosis lateral amiotrófica",
    "angiofibroma": "Angiofibroma",
    "anemia, aplastic": "Anemia aplásica",
    "arthritis": "Artritis",
    "arthritis, juvenile": "Artritis juvenil",
    "arthritis, juvenile rheumatoid": "Artritis reumatoide juvenil",
    "arthritis, psoriatic": "Artritis psoriásica",
    "arthritis, rheumatoid": "Artritis reumatoide",
    "asthma": "Asma",
    "axial spondyloarthritis": "Espondiloartritis axial",
    "beta-thalassemia": "Beta-talasemia",
    "bone marrow transplantation": "Trasplante de médula ósea",
    "bone resorption": "Resorción ósea",
    "breast neoplasms": "Neoplasias de mama",
    "cancer": "Cáncer",
    "carcinoma, bronchogenic": "Carcinoma broncogénico",
    "carcinoma, hepatocellular": "Carcinoma hepatocelular",
    "carcinoma, non-small-cell lung": "Carcinoma de pulmón no microcítico",
    "carcinoma, renal cell": "Carcinoma de células renales",
    "carcinoma, transitional cell": "Carcinoma de células de transición",
    "chemotherapy-induced febrile neutropenia": "Neutropenia febril inducida por quimioterapia",
    "colitis, ulcerative": "Colitis ulcerosa",
    "colonic neoplasms": "Neoplasias de colon",
    "colorectal neoplasms": "Neoplasias colorrectales",
    "covid-19 virus infection": "Infección por virus COVID-19",
    "crohn disease": "Enfermedad de Crohn",
    "cytokine release syndrome": "Síndrome de liberación de citocinas",
    "dermatitis, atopic": "Dermatitis atópica",
    "dermatofibrosarcoma": "Dermatofibrosarcoma",
    "dwarfism, pituitary": "Enanismo hipofisario",
    "endometrial neoplasms": "Neoplasias de endometrio",
    "fabry disease": "Enfermedad de Fabry",
    "fallopian tube neoplasms": "Neoplasias de trompa de Falopio",
    "febrile neutropenia": "Neutropenia febril",
    "fractures, bone": "Fracturas óseas",
    "gastrointestinal stromal tumors": "Tumores del estroma gastrointestinal",
    "gaucher disease": "Enfermedad de Gaucher",
    "giant cell arteritis": "Arteritis de células gigantes",
    "graft rejection": "Rechazo de injerto",
    "growth": "Crecimiento",
    "guillain-barre syndrome": "Síndrome de Guillain-Barré",
    "head and neck neoplasms": "Neoplasias de cabeza y cuello",
    "hematopoietic stem cell transplantation": "Trasplante de células madre hematopoyéticas",
    "hemophilia a": "Hemofilia A",
    "hemophilia b": "Hemofilia B",
    "hepatitis b": "Hepatitis B",
    "hepatitis c, chronic": "Hepatitis C crónica",
    "hidradenitis suppurativa": "Hidradenitis supurativa",
    "hodgkin disease": "Enfermedad de Hodgkin",
    "hypercalcemia": "Hipercalcemia",
    "hypereosinophilic syndrome": "Síndrome hipereosinofílico",
    "hypertension, pulmonary": "Hipertensión pulmonar",
    "idiopathic pulmonary fibrosis": "Fibrosis pulmonar idiopática",
    "immunization, passive": "Inmunización pasiva",
    "immunologic deficiency syndromes": "Síndromes de inmunodeficiencia",
    "iron overload": "Sobrecarga de hierro",
    "kidney transplantation": "Trasplante renal",
    "leukemia, hairy cell": "Leucemia de células peludas",
    "leukemia, lymphocytic, chronic, b-cell": "Leucemia linfocítica crónica de células B",
    "leukemia, myelogenous, chronic, bcr-abl positive": "Leucemia mieloide crónica BCR-ABL positiva",
    "leukemia, myeloid, acute": "Leucemia mieloide aguda",
    "leukemia, myelomonocytic, acute": "Leucemia mielomonocítica aguda",
    "leukemia, myelomonocytic, chronic": "Leucemia mielomonocítica crónica",
    "liver transplantation": "Trasplante hepático",
    "lung diseases": "Enfermedades pulmonares",
    "lymphoma, follicular": "Linfoma folicular",
    "lymphoma, mantle-cell": "Linfoma de células del manto",
    "lymphoma, non-hodgkin": "Linfoma no Hodgkin",
    "melanoma": "Melanoma",
    "microscopic polyangiitis": "Poliangeítis microscópica",
    "mucocutaneous lymph node syndrome": "Síndrome de ganglios linfáticos mucocutáneos",
    "mucopolysaccharidosis vi": "Mucopolisacaridosis VI",
    "multiple myeloma": "Mieloma múltiple",
    "multiple sclerosis": "Esclerosis múltiple",
    "multiple sclerosis, relapsing-remitting": "Esclerosis múltiple remitente-recurrente",
    "muscular atrophy, spinal": "Atrofia muscular espinal",
    "myelodysplastic syndromes": "Síndromes mielodisplásicos",
    "myelodysplastic-myeloproliferative diseases": "Enfermedades mielodisplásicas-mieloproliferativas",
    "nausea": "Náuseas",
    "neoplasms": "Neoplasias",
    "neuroendocrine tumors": "Tumores neuroendocrinos",
    "neutropenia": "Neutropenia",
    "non-radiographic axial spondyloarthritis": "Espondiloartritis axial no radiográfica",
    "osteitis deformans": "Osteítis deformante",
    "osteoporosis": "Osteoporosis",
    "osteoporosis, postmenopausal": "Osteoporosis posmenopáusica",
    "ovarian neoplasms": "Neoplasias de ovario",
    "pancreatic neoplasms": "Neoplasias de páncreas",
    "pemphigus": "Pénfigo",
    "peritoneal neoplasms": "Neoplasias peritoneales",
    "polyradiculoneuropathy": "Polirradiculoneuropatía",
    "polyradiculoneuropathy, chronic inflammatory demyelinating": "Polirradiculoneuropatía desmielinizante inflamatoria crónica",
    "prader-willi syndrome": "Síndrome de Prader-Willi",
    "precursor cell lymphoblastic leukemia-lymphoma": "Leucemia-linfoma linfoblástico de células precursoras",
    "prostatic neoplasms": "Neoplasias de próstata",
    "prostatic neoplasms, castration-resistant": "Neoplasias de próstata resistentes a la castración",
    "psoriasis": "Psoriasis",
    "psychotic disorders": "Trastornos psicóticos",
    "pulmonary arterial hypertension": "Hipertensión arterial pulmonar",
    "purpura, thrombocytopenic, idiopathic": "Púrpura trombocitopénica idiopática",
    "respiratory tract diseases": "Enfermedades del tracto respiratorio",
    "rhinitis": "Rinitis",
    "schizophrenia": "Esquizofrenia",
    "scleroderma, systemic": "Esclerodermia sistémica",
    "skin diseases, papulosquamous": "Enfermedades cutáneas papuloescamosas",
    "small cell lung carcinoma": "Carcinoma pulmonar de células pequeñas",
    "spondylarthropathies": "Espondiloartropatías",
    "spondylitis, ankylosing": "Espondilitis anquilosante",
    "squamous cell carcinoma of head and neck": "Carcinoma de células escamosas de cabeza y cuello",
    "stomach neoplasms": "Neoplasias de estómago",
    "telangiectasia, hereditary hemorrhagic": "Telangiectasia hemorrágica hereditaria",
    "tuberous sclerosis": "Esclerosis tuberosa",
    "turner syndrome": "Síndrome de Turner",
    "urologic neoplasms": "Neoplasias urológicas",
    "urticaria": "Urticaria",
    "uterine cervical neoplasms": "Neoplasias de cuello uterino",
    "uveitis": "Uveítis",
    "vomiting": "Vómitos",
    "von willebrand diseases": "Enfermedad de von Willebrand",
    "wegeners granulomatosis": "Granulomatosis de Wegener",
    "wegener granulomatosis": "Granulomatosis de Wegener",
    "wet macular degeneration": "Degeneración macular húmeda",
}


def _norm_area_key(s: str) -> str:
    t = re.sub(r"\s+", " ", str(s or "").strip().lower())
    t = t.replace("’", "'").replace("–", "-").replace("—", "-")
    return t


def traducir_termino_area(termino: str, usar_motor: bool = True) -> str:
    """Traduce un término MeSH / área EMA a español (glosario + motor opcional)."""
    raw = re.sub(r"\s+", " ", str(termino or "").strip())
    if not raw:
        return ""
    key = _norm_area_key(raw)
    if key in AREAS_MESH_ES:
        return AREAS_MESH_ES[key]
    # ya parece español (tildes / palabras frecuentes)
    if re.search(r"[áéíóúñüÁÉÍÓÚÑÜ]", raw) or re.search(
        r"(?i)\b(artritis|cáncer|rechazo|neoplasia|síndrome|enfermedad)\b", raw
    ):
        return raw
    if not usar_motor:
        return raw
    res = traducir(raw, fuente="en", destino="es")
    out = str((res or {}).get("texto") or raw).strip()
    # Title Case suave si Google devolvió todo minúsculas
    if out and out == out.lower() and len(out) < 80:
        out = out[:1].upper() + out[1:]
    return out or raw


def traducir_areas_terapeuticas(texto: str, usar_motor: bool = True) -> str:
    """Traduce una cadena de áreas EMA separadas por ';'."""
    raw = str(texto or "").strip()
    if not raw:
        return ""
    partes = [p.strip() for p in re.split(r"\s*;\s*", raw) if p.strip()]
    if not partes:
        return ""
    trad = [traducir_termino_area(p, usar_motor=usar_motor) for p in partes]
    # dedupe preservando orden
    out: list[str] = []
    seen: set[str] = set()
    for t in trad:
        k = t.lower()
        if not t or k in seen:
            continue
        seen.add(k)
        out.append(t)
    return "; ".join(out)


def traducir(texto: str, fuente: str = "en", destino: str = "es") -> dict[str, Any]:
    raw = (texto or "").strip()
    if not raw:
        return {"ok": True, "texto": "", "cached": False, "traducido": False}
    # textos ya en español / cortos genéricos
    if not _parece_ingles(raw) and len(raw) > 40:
        # si no parece inglés, devolver tal cual (p.ej. ya traducido)
        key_early = _key(raw, fuente, destino)
        cached_early = _leer_cache(key_early)
        if cached_early:
            return {"ok": True, "texto": cached_early, "cached": True, "traducido": True}

    key = _key(raw, fuente, destino)
    cached = _leer_cache(key)
    if cached is not None and not _parece_ingles(cached):
        return {"ok": True, "texto": cached, "cached": True, "traducido": True}

    sess = requests.Session()
    sess.verify = False
    sess.headers.update({"User-Agent": UA, "Accept": "application/json"})

    # trozos cómodos para POST (evita 429 y cortes)
    chunks = _chunk(raw, 900)
    translated: list[str] = []
    for i, ch in enumerate(chunks):
        translated.append(_traducir_chunk(ch, fuente, destino, sess))
        if i < len(chunks) - 1:
            time.sleep(0.35)

    result = _post_limpieza(" ".join(translated).strip() or raw)

    # una pasada extra sobre restos EN + glosario clínico
    leftovers = _fragmentos_ingles(result)[:8]
    leftovers.sort(key=len, reverse=True)
    for frag in leftovers:
        if not _parece_ingles(result):
            break
        fixed = _google(frag.strip(), fuente, destino, sess)
        if fixed and fixed != frag:
            result = result.replace(frag, fixed, 1)
            time.sleep(0.1)
    result = _post_limpieza(result)

    # glosario final de términos clínicos frecuentes que suelen quedar
    glossary = [
        (r"(?i)\bpolyarticular juvenile idiopathic arthritis\b", "artritis idiopática juvenil poliarticular"),
        (r"(?i)\bjuvenile idiopathic arthritis\b", "artritis idiopática juvenil"),
        (r"(?i)\brheumatoid arthritis\b", "artritis reumatoide"),
        (r"(?i)\bpsoriatic arthritis\b", "artritis psoriásica"),
        (r"(?i)\bankylosing spondylitis\b", "espondilitis anquilosante"),
        (r"(?i)\bulcerative colitis\b", "colitis ulcerosa"),
        (r"(?i)\bCrohn'?s disease\b", "enfermedad de Crohn"),
        (r"(?i)\bplaque psoriasis\b", "psoriasis en placas"),
        (r"(?i)\bhidradenitis suppurativa\b", "hidradenitis supurativa"),
        (r"(?i)\bmoderate to severe\b", "moderada a grave"),
        (r"(?i)\badult patients\b", "pacientes adultos"),
        (r"(?i)\bpediatric patients\b", "pacientes pediátricos"),
        (r"(?i)\binadequate response\b", "respuesta inadecuada"),
        (r"(?i)\bin combination with\b", "en combinación con"),
        (r"(?i)\bthe treatment of\b", "el tratamiento de"),
        (r"(?i)\bis indicated for\b", "está indicado para"),
        (r"(?i)\bare indicated for\b", "están indicados para"),
        (r"(?i)\bin pacientes\b", "en pacientes"),
        (r"(?i)\bde de\b", "de"),
    ]
    for pat, rep in glossary:
        result = re.sub(pat, rep, result)
    result = _post_limpieza(result)

    # guardar aunque queden restos mínimos; si sigue muy EN, no cachear para reintentar luego
    if result and not _parece_ingles(result):
        _guardar_cache(key, result, fuente, destino)
    elif result and result != raw:
        # parcial: cachear con clave distinta? mejor no — forzar reintento futuro
        pass

    return {
        "ok": True,
        "texto": result,
        "cached": False,
        "traducido": result != raw,
        "motor": "google-gtx-post",
    }


def traducir_lista(textos: list[str], fuente: str = "en", destino: str = "es") -> list[str]:
    out: list[str] = []
    for t in textos:
        out.append(traducir(t, fuente=fuente, destino=destino).get("texto") or t)
        time.sleep(0.15)
    return out
