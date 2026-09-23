#!/usr/bin/env python3
"""
Scrape local de farmacias bloqueadas en el datacenter → export JSON + Excel.

Correr en tu PC (sin proxy corporativo), dentro del repo:

    cd medicamentos_alto_costo
    python -m venv .venv && source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
    pip install -r requirements.txt
    python scrapper/run_local_bloqueadas.py --fresh

Salida por defecto: ./export_local/corrida_YYYYMMDD-HHMM/

Opciones:
    --out DIR          Carpeta destino (default export_local/corrida_…)
    --fresh            Ignora caché y vuelve a la red
    --fomac            Solo moléculas FOMAC
    --solo SLUGS       Ej: --solo farmacity,cruzverde,inkafarma
    --lista            Muestra slugs disponibles y sale

Luego sube la carpeta o el Excel consolidado al servidor e importa con:
    python scrapper/importar_local.py export_local/corrida_…

Cruz Verde: si la API pide sesión, exporta antes en tu navegador:
    export CRUZVERDE_COOKIE='connect.sid=...'
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.export_local import escribir_corrida, escribir_excel, normalizar_filas  # noqa: E402
from scrapper.vtex_tienda import recolectar as recolectar_vtex  # noqa: E402


def _meds(argv_flags: list[str]) -> list[dict[str, Any]]:
    if "--fomac" in argv_flags:
        return [m for m in MEDICAMENTOS if "FOMAC" in str(m["programa"])]
    return MEDICAMENTOS


def _fuente_vtex(
    slug: str,
    pais: str,
    farmacia: str,
    moneda: str,
    base: str,
    cache_name: str,
    *,
    verify: bool = False,
) -> Callable[[list[str]], list[dict[str, Any]]]:
    cache = ROOT / "cache" / "farmacias" / cache_name

    def run(argv_flags: list[str]) -> list[dict[str, Any]]:
        forzar = "--fresh" in argv_flags
        solo_cache = "--cache" in argv_flags
        return recolectar_vtex(
            pais=pais,
            farmacia=farmacia,
            moneda=moneda,
            base=base,
            cache=cache,
            forzar=forzar,
            meds=_meds(argv_flags),
            verify=verify,
            solo_cache=solo_cache,
        )

    return run


def _fuente_cruzverde(argv_flags: list[str]) -> list[dict[str, Any]]:
    from scrapper.co_cruzverde import recolectar

    return recolectar(forzar="--fresh" in argv_flags, meds=_meds(argv_flags))


def _fuente_inkafarma(argv_flags: list[str]) -> list[dict[str, Any]]:
    from scrapper.pe_inkafarma import recolectar

    return recolectar(forzar="--fresh" in argv_flags, meds=_meds(argv_flags))


def _fuente_sanpablo(argv_flags: list[str]) -> list[dict[str, Any]]:
    import requests
    from scrapper.magento_tienda import recolectar as recolectar_magento

    base = "https://www.farmaciasanpablo.com.mx"
    cache = ROOT / "cache" / "farmacias" / "sanpablo"
    kwargs = dict(
        pais="México",
        farmacia="Farmacias San Pablo",
        moneda="MXN",
        base=base,
        cache=cache,
        forzar="--fresh" in argv_flags,
        meds=_meds(argv_flags),
        solo_cache="--cache" in argv_flags,
    )
    try:
        r = requests.get(
            f"{base}/api/catalog_system/pub/products/search",
            params={"ft": "metformina", "_from": 0, "_to": 1},
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=20,
        )
        if r.status_code in (200, 206) and isinstance(r.json(), list):
            return recolectar_vtex(**kwargs, verify=True)
    except Exception:
        pass
    return recolectar_magento(**kwargs)


FUENTES: dict[str, dict[str, Any]] = {
    "farmacity": {
        "pais": "Argentina",
        "farmacia": "Farmacity",
        "run": _fuente_vtex("farmacity", "Argentina", "Farmacity", "ARS", "https://www.farmacity.com", "farmacity"),
    },
    "drogasil": {
        "pais": "Brasil",
        "farmacia": "Drogasil",
        "run": _fuente_vtex("drogasil", "Brasil", "Drogasil", "BRL", "https://www.drogasil.com.br", "drogasil"),
    },
    "drogaraia": {
        "pais": "Brasil",
        "farmacia": "Droga Raia",
        "run": _fuente_vtex("drogaraia", "Brasil", "Droga Raia", "BRL", "https://www.drogaraia.com.br", "drogaraia"),
    },
    "panvel": {
        "pais": "Brasil",
        "farmacia": "Panvel",
        "run": _fuente_vtex("panvel", "Brasil", "Panvel", "BRL", "https://www.panvel.com", "panvel"),
    },
    "sanpablo": {
        "pais": "México",
        "farmacia": "Farmacias San Pablo",
        "run": _fuente_sanpablo,
    },
    "cruzverde": {
        "pais": "Colombia",
        "farmacia": "Cruz Verde",
        "run": _fuente_cruzverde,
    },
    "larebaja": {
        "pais": "Colombia",
        "farmacia": "La Rebaja",
        "run": _fuente_vtex("larebaja", "Colombia", "La Rebaja", "COP", "https://www.larebajavirtual.com", "larebaja"),
    },
    "cafam": {
        "pais": "Colombia",
        "farmacia": "Droguerías Cafam",
        "run": _fuente_vtex("cafam", "Colombia", "Droguerías Cafam", "COP", "https://www.drogueriascafam.com.co", "cafam"),
    },
    "inkafarma": {
        "pais": "Perú",
        "farmacia": "Inkafarma",
        "run": _fuente_inkafarma,
    },
    "farmashop": {
        "pais": "Uruguay",
        "farmacia": "Farmashop",
        "run": _fuente_vtex(
            "farmashop",
            "Uruguay",
            "Farmashop",
            "UYU",
            "https://tienda.farmashop.com.uy",
            "farmashop",
        ),
    },
    "pigalle": {
        "pais": "Uruguay",
        "farmacia": "Pigalle",
        "run": lambda argv: __import__("scrapper.uy_pigalle", fromlist=["main"]).main(),
    },
    "farmacity_uy": {
        "pais": "Uruguay",
        "farmacia": "Farmacity UY",
        "run": _fuente_vtex(
            "farmacity_uy",
            "Uruguay",
            "Farmacity UY",
            "UYU",
            "https://www.farmacity.com.uy",
            "farmacity_uy",
        ),
    },
    "antartida": {
        "pais": "Uruguay",
        "farmacia": "Farmacia Antártida",
        "run": lambda argv: __import__("scrapper.uy_antartida", fromlist=["main"]).main(),
    },
    "goes": {
        "pais": "Uruguay",
        "farmacia": "Farmacia Goes",
        "run": lambda argv: __import__("scrapper.uy_goes", fromlist=["main"]).main(),
    },
    "fybeca": {
        "pais": "Ecuador",
        "farmacia": "Fybeca",
        "run": _fuente_vtex("fybeca", "Ecuador", "Fybeca", "USD", "https://www.fybeca.com", "fybeca"),
    },
    "batres": {
        "pais": "Guatemala",
        "farmacia": "Farmacias Batres",
        "run": _fuente_vtex("batres", "Guatemala", "Farmacias Batres", "GTQ", "https://www.farmaciasbatres.com.gt", "batres_gt"),
    },
    "kolbi": {
        "pais": "Costa Rica",
        "farmacia": "Kölbi",
        "run": _fuente_vtex("kolbi", "Costa Rica", "Kölbi", "CRC", "https://www.kolbi.cr", "kolbi"),
    },
    "sannicolas": {
        "pais": "El Salvador",
        "farmacia": "Farmacias San Nicolás",
        "run": _fuente_vtex(
            "sannicolas",
            "El Salvador",
            "Farmacias San Nicolás",
            "USD",
            "https://www.farmaciasannicolas.com",
            "sannicolas_sv",
        ),
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape local → export_local (sin BD)")
    parser.add_argument("--out", type=Path, help="Carpeta de salida")
    parser.add_argument("--fresh", action="store_true", help="Ignorar caché local")
    parser.add_argument("--fomac", action="store_true", help="Solo FOMAC")
    parser.add_argument("--cache", action="store_true", help="Solo caché (sin red)")
    parser.add_argument("--solo", type=str, help="Slugs separados por coma")
    parser.add_argument("--lista", action="store_true", help="Listar slugs")
    args, _rest = parser.parse_known_args()

    if args.lista:
        for slug, meta in FUENTES.items():
            print(f"{slug:12}  {meta['pais']} · {meta['farmacia']}")
        return 0

    argv_flags: list[str] = []
    if args.fresh:
        argv_flags.append("--fresh")
    if args.fomac:
        argv_flags.append("--fomac")
    if args.cache:
        argv_flags.append("--cache")

    ts = datetime.now().strftime("%Y%m%d-%H%M")
    out_dir = args.out or (ROOT / "export_local" / f"corrida_{ts}")
    out_dir.mkdir(parents=True, exist_ok=True)

    slugs = [s.strip() for s in (args.solo or "").split(",") if s.strip()]
    if not slugs:
        slugs = list(FUENTES.keys())

    desconocidos = [s for s in slugs if s not in FUENTES]
    if desconocidos:
        print("Slugs desconocidos:", ", ".join(desconocidos))
        print("Usa --lista para ver opciones.")
        return 1

    manifest: dict[str, Any] = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "modo": "local_sin_bd",
        "flags": argv_flags,
        "out_dir": str(out_dir.resolve()),
        "fuentes": [],
    }
    todas: list[dict[str, Any]] = []

    print(f"Exportando en {out_dir.resolve()}")
    print(f"Fuentes: {', '.join(slugs)}\n")

    for slug in slugs:
        meta = FUENTES[slug]
        print("=" * 64)
        print(f" {meta['pais']} · {meta['farmacia']} ({slug})")
        print("=" * 64)
        try:
            filas = meta["run"](argv_flags)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            filas = []
            res = escribir_corrida(
                out_dir=out_dir,
                slug=slug,
                pais=meta["pais"],
                farmacia=meta["farmacia"],
                filas=[],
                notas=f"error: {exc}",
            )
            manifest["fuentes"].append(res)
            continue

        nota = "scrape local sin BD"
        for f in filas:
            obs = str(f.get("observacion") or "").strip()
            extra = "Importado desde scrape local"
            if extra not in obs:
                f["observacion"] = f"{obs} | {extra}" if obs else extra

        res = escribir_corrida(
            out_dir=out_dir,
            slug=slug,
            pais=meta["pais"],
            farmacia=meta["farmacia"],
            filas=filas,
            notas=nota,
        )
        manifest["fuentes"].append(res)
        todas.extend(filas)
        print(
            f"  → {res['filas']} filas (ok={res['ok']}, con precio={res['con_precio']}) "
            f"→ {res['json']}, {res['xlsx']}\n"
        )

    if todas:
        escribir_excel(todas, out_dir / "TODAS_las_fuentes.xlsx")
        escribir_json_consolidado = out_dir / "TODAS_las_fuentes.json"
        escribir_json_consolidado.write_text(
            json.dumps(normalizar_filas(todas), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        manifest["consolidado"] = {
            "filas": len(todas),
            "json": "TODAS_las_fuentes.json",
            "xlsx": "TODAS_las_fuentes.xlsx",
        }

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 64)
    print(f"Listo. Carpeta: {out_dir.resolve()}")
    print(f"Manifest: {manifest_path.name}")
    if todas:
        print("Consolidado: TODAS_las_fuentes.xlsx")
    print("\nPara incorporar en el servidor:")
    print(f"  python scrapper/importar_local.py {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
