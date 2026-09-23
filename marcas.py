"""Guía de marcas comerciales DAMAC/FOMAC (lista original).

Sirve para saber qué buscar en cada farmacia al agregar un país.
Las marcas se cruzan con lista.MEDICAMENTOS al importar.
"""

from __future__ import annotations

import re
import unicodedata

# n_lista → marcas / nombres comerciales tal como vienen en la lista madre.
MARCAS: dict[int, list[str]] = {
    1: ["ZYTIGA", "ACETATO DE ABIRATERONA"],
    2: ["GLAMATIR"],
    3: ["ZOLADEX", "PROZOLADEX LA", "PROZOLADEX", "GOVOLYX"],
    4: ["LUPRON DEPOT", "ELIGARD"],
    5: ["ACLASTA", "ZOMETA", "ACIDO ZOLEDRONICO"],
    6: ["HUMIRA", "HYRIMOZ", "AMGEVITA", "IDACIO", "YUFLYMA"],
    7: ["FABRAZYME"],
    8: ["TECENTRIQ"],
    9: ["VIDAZA", "ZACTIDYN", "WINDUZA", "XITIDIN", "AZADUAL"],
    10: ["SIMULECT"],
    11: [],
    12: ["AVASTIN", "VEGZELMA"],
    13: ["CASODEX"],
    14: ["VELCADE", "BORTEZOMIB"],
    15: ["CANABOSEN"],
    16: ["CAPCITOX", "CAPETERO", "RELICITABINE", "CAPECITABINA"],
    17: ["ERBITUX"],
    18: ["SANDIMMUN NEORAL"],
    19: ["MAVENCLAD"],
    20: ["DARZALEX FASPRO", "DARZALEX"],
    21: [],
    22: ["EXJADE", "DEFERASIROX"],
    23: ["PULMOZYME"],
    24: ["REVOLADE"],
    25: ["HEMLIBRA"],
    26: ["XTANDI"],
    27: ["ENBREL", "ERELZI", "NEPEXTO"],
    28: ["AFINITOR", "NAT-EVEROLIMUS", "CERTICAN"],
    29: ["OCTANATE", "NUWIQ"],
    30: ["HEBERPROT-P"],
    31: ["BENEFIX"],
    32: ["ZARZIO"],
    33: ["GILENYA"],
    34: ["FASLODEX"],
    35: ["NAGLAZYME"],
    36: ["SIMPONI"],
    37: ["TREMFYA"],
    38: ["IMBRUVICA"],
    39: ["GLIVEC", "IMATINIB"],
    40: ["CEREZYME"],
    41: ["REMICADE", "REMSIMA", "IXIFI"],
    42: ["OCTAGAM", "PRIVIGEN"],
    43: ["REBIF", "AVONEX"],
    44: ["BETAFERON"],
    45: ["TYKERB"],
    46: ["REVLIMID", "LENALIDOMIDA"],
    47: ["FEMARA"],
    48: ["CELLCEPT", "MICOFENOLATO DE MOFETILO"],
    49: ["MYFORTIC"],
    50: ["TASIGNA", "NILOTINIB HYDROCHLORIDE"],
    51: ["GAZYVA"],
    52: ["OCREVUS", "OCREVUS ZUNOVO"],
    53: ["SANDOSTATIN", "SANDOSTATIN LAR"],
    54: ["LYNPARZA"],
    55: ["XOLAIR"],
    56: ["TAGRISSO"],
    57: ["IBRANCE"],
    58: ["INVEGA", "INVEGA HAFYERA", "INVEGA SUSTENNA", "INVEGA TRINZA", "PALIPERIDONE"],
    59: ["KEYTRUDA"],
    60: ["PERJETA"],
    61: ["PHESGO"],
    62: ["PIRFONE"],
    63: ["STIVARGA"],
    64: [],
    65: ["KISQALI"],
    66: ["RILUTEK"],
    67: ["ADEMPAS", "RIOCI"],
    68: ["MABTHERA", "TRUXIMA", "RIXATHON"],
    69: [],
    70: ["RAPAMUNE"],
    71: ["EPCLUSA"],
    72: ["GENOTROPIN", "SAIZEN", "NORDITROPIN FLEXPRO"],
    73: ["NEXAVAR"],
    74: ["SUTENT", "SUNITINIB MALATO"],
    75: ["TACROLIMUS", "PROGRAF", "TIPURIC"],
    76: ["AUBAGIO", "TERIFLUNOMIDE"],
    77: ["FORTEO"],
    78: ["TIMOGLOBULINA"],
    79: ["ACTEMRA"],
    80: ["XELJANZ XR", "XELJANZ"],
    81: ["HERCEPTIN", "HERZUMA", "TRAZIMERA"],
    82: ["STELARA", "SELARSDI"],
    83: ["VALGANCICLOVIR", "SEVECLO"],
    84: ["BLINCYTO"],
    85: ["ONCASPAR"],
    86: ["EVRYSDI"],
    87: [],
    88: [],
}


def _norm_alias(texto: str) -> str:
    s = unicodedata.normalize("NFKD", texto or "")
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.replace("®", " ").replace('"', " ")
    s = re.sub(r"[/]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def aliases_de_marcas(n: int) -> list[str]:
    """Tokens de búsqueda (≥4 chars) a partir de la guía de marcas."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in MARCAS.get(int(n), []):
        limpio = _norm_alias(raw)
        if not limpio:
            continue
        partes = [limpio]
        for trozo in re.split(r"[\s\-]+", limpio):
            if trozo and trozo not in partes:
                partes.append(trozo)
        for a in partes:
            if len(a) < 4:
                continue
            if a in {
                "acetato",
                "acido",
                "humana",
                "factor",
                "malato",
                "depot",
                "flexpro",
                "hydrochloride",
                # Sufijos compartidos de coformulaciones (no son marcas únicas)
                "faspro",
                "hycela",
                "hylecta",
                "zunovo",
                "qlex",
                "hybreza",
            }:
                continue
            if a not in seen:
                seen.add(a)
                out.append(a)
    return out
