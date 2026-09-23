"""
Corre scrapers de países con baja cobertura + fuentes CO bloqueadas por proxy.

Uso:
    python scrapper/run_cobertura_baja.py
    python scrapper/run_cobertura_baja.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PASOS = [
    ("Colombia · Cruz Verde (bloqueada)", "scrapper.co_cruzverde", "main"),
    ("Colombia · La Rebaja (bloqueada)", "scrapper.co_larebaja", "main"),
    ("Colombia · Cafam (bloqueada)", "scrapper.co_cafam", "main"),
    ("Colombia · Locatel", "scrapper.co_locatel", "main"),
    ("Colombia · Farmatodo", "scrapper.co_farmatodo", "main"),
    ("Colombia · Carulla", "scrapper.co_carulla", "main"),
    ("Guatemala · Siman", "scrapper.gt_siman", "main"),
    ("Guatemala · Batres", "scrapper.gt_batres", "main"),
    ("Guatemala · Galeno", "scrapper.gt_galeno", "main"),
    ("Guatemala · Meykos", "scrapper.gt_meykos", "main"),
    ("Guatemala · Cruz Verde", "scrapper.gt_cruzverde", "main"),
    ("Guatemala · FarmaValue", "scrapper.gt_farmavalue", "main"),
    ("Nicaragua · Siman", "scrapper.ni_siman", "main"),
    ("Nicaragua · Kielsa", "scrapper.ni_kielsa", "main"),
    ("Nicaragua · Farmacias del Ahorro", "scrapper.ni_fahorro", "main"),
    ("Nicaragua · FarmaValue", "scrapper.ni_farmavalue", "main"),
    ("Costa Rica · Siman", "scrapper.cr_siman", "main"),
    ("Costa Rica · Kölbi", "scrapper.cr_kolbi", "main"),
    ("Costa Rica · Fischel", "scrapper.cr_fischel", "main"),
    ("Costa Rica · FarmaValue", "scrapper.cr_farmavalue", "main"),
    ("El Salvador · Siman", "scrapper.sv_siman", "main"),
    ("El Salvador · El Farmacéutico", "scrapper.sv_elfarmaceutico", "main"),
    ("El Salvador · FarmaValue", "scrapper.sv_farmavalue", "main"),
    ("Perú · Inkafarma", "scrapper.pe_inkafarma", "main"),
    ("Perú · Boticas Perú", "scrapper.pe_boticasperu", "main"),
    ("Honduras · Siman", "scrapper.hn_siman", "main"),
    ("Honduras · Kielsa", "scrapper.hn_kielsa", "main"),
    ("Honduras · Farmacias del Ahorro", "scrapper.hn_fahorro", "main"),
    ("Honduras · MiFarmacia", "scrapper.hn_mifarmacia", "main"),
    ("Honduras · FarmaValue", "scrapper.hn_farmavalue", "main"),
    ("Panamá · Pan Am Farma", "scrapper.pa_panamfarma", "main"),
    ("Panamá · Farmacias Julios", "scrapper.pa_julios", "main"),
    ("Panamá · Arrocha", "scrapper.pa_arrocha", "main"),
    ("Panamá · FarmaValue", "scrapper.pa_farmavalue", "main"),
    ("México · Farmacias Especializadas", "scrapper.mx_fesa", "main"),
    ("Argentina · AlfaBeta", "scrapper.ar_alfabeta", "main"),
    ("Uruguay · Pigalle", "scrapper.uy_pigalle", "main"),
    ("Uruguay · Farmacity UY", "scrapper.uy_farmacity", "main"),
    ("Uruguay · Farmacia Antártida", "scrapper.uy_antartida", "main"),
    ("Uruguay · Farmacia Goes", "scrapper.uy_goes", "main"),
    ("Uruguay · Farmashop", "scrapper.uy_farmashop", "main"),
    ("Bolivia · FSA", "scrapper.bo_fsa", "main"),
    ("Bolivia · Farmacorp", "scrapper.bo_farmacorp", "main"),
    ("Venezuela · SAAS", "scrapper.ve_saas", "main"),
    ("Venezuela · Locatel", "scrapper.ve_locatel", "main"),
    ("Perú · Farmacia Universal", "scrapper.pe_universal", "main"),
    ("Trinidad · TriniPharma", "scrapper.tt_trinipharma", "main"),
    ("Paraguay · Punto Farma", "scrapper.py_puntofarma", "main"),
    ("Paraguay · Prosalud", "scrapper.py_prosalud", "main"),
    ("Paraguay · Biggie", "scrapper.py_biggie", "main"),
    ("Chile · FarmaValue", "scrapper.cl_farmavalue", "main"),
    ("México · FarmaValue", "scrapper.mx_farmavalue", "main"),
    ("Trinidad · CVA Pharmacy", "scrapper.tt_cva", "main"),
]


def main() -> int:
    argv = sys.argv[1:]
    rc_final = 0
    print("=" * 72)
    print(" Cobertura baja · países CA + CO bloqueadas + Perú")
    print("=" * 72)
    for titulo, mod_name, fn_name in PASOS:
        print(f"\n>>> {titulo}")
        mod = __import__(mod_name, fromlist=[fn_name])
        fn = getattr(mod, fn_name)
        try:
            rc = int(fn() or 0)
        except Exception as exc:
            print(f"  ERROR {titulo}: {exc}")
            rc = 1
        if rc:
            rc_final = rc
    print("\n" + "=" * 72)
    print(f" Fin cobertura baja (rc={rc_final})")
    return rc_final


if __name__ == "__main__":
    raise SystemExit(main())
