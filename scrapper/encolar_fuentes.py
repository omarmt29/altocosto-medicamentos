"""Encola todos los scrapers salvo farmacias.do."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scrapper.jobs_cola import FUENTES, encolar  # noqa: E402

EXCLUIDAS = {"farmacias_do"}


def main() -> int:
    n = 0
    for fid, meta in FUENTES.items():
        if fid in EXCLUIDAS:
            print(f"skip {fid}")
            continue
        if meta.get("requiere_playwright"):
            print(f"skip {fid} (playwright)")
            continue
        job = encolar(fid, solicitado_por="arranque", force=False)
        print(f"encolado {fid} job={job.get('id')} reutilizado={job.get('reutilizado')}")
        n += 1
    print(f"fuentes encoladas: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
