"""Exporta el Excel a plataforma/data.js para la web."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from lista import MEDICAMENTOS

CARPETA = Path(__file__).resolve().parent
DESTINO = CARPETA / "plataforma" / "data.js"

PAIS_META = {
    "República Dominicana": ("do", "RD"),
    "Argentina": ("ar", "AR"),
    "Brasil": ("br", "BR"),
    "Colombia": ("co", "CO"),
    "Perú": ("pe", "PE"),
    "Chile": ("cl", "CL"),
    "México": ("mx", "MX"),
    "Costa Rica": ("cr", "CR"),
    "Panamá": ("pa", "PA"),
    "Uruguay": ("uy", "UY"),
    "El Salvador": ("sv", "SV"),
    "Ecuador": ("ec", "EC"),
    "Honduras": ("hn", "HN"),
    "Guatemala": ("gt", "GT"),
    "Nicaragua": ("ni", "NI"),
    "Paraguay": ("py", "PY"),
    "Venezuela": ("ve", "VE"),
    "Guyana": ("gy", "GY"),
    "Trinidad y Tobago": ("tt", "TT"),
    "Bolivia": ("bo", "BO"),
    "Estados Unidos": ("us", "US"),
    "Canadá": ("ca", "CA"),
    "Canada": ("ca", "CA"),
}
CAMPOS = ["hits", "min_usd", "med_usd", "min_dop", "ejemplo", "tipo", "fuente", "fecha"]


def limpio(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, str):
        s = v.strip()
        return s or None
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            pass
    return v


def xlsx_mas_reciente() -> Path:
    archivos = sorted(
        (CARPETA / "salida").glob("comparativo_alto_costo_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not archivos:
        raise SystemExit("No hay Excel en salida/. Corre primero generar_comparativo.py")
    return archivos[0]


def paises_desde_comparativo(comp) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    vistos: set[str] = set()
    for col in comp.columns:
        if " — " not in str(col):
            continue
        nombre = str(col).split(" — ", 1)[0].strip()
        if nombre in vistos:
            continue
        meta = PAIS_META.get(nombre)
        if not meta:
            continue
        vistos.add(nombre)
        out.append((meta[0], nombre, meta[1]))
    return out


def main() -> None:
    xlsx = xlsx_mas_reciente()
    print(f"Leyendo {xlsx.name}")

    comp = pd.read_excel(xlsx, sheet_name="Comparativo")
    det = pd.read_excel(xlsx, sheet_name="Detalle coincidencias")
    fuentes_df = pd.read_excel(xlsx, sheet_name="Fuentes")
    tasas_df = pd.read_excel(xlsx, sheet_name="Tasas FX")
    notas_df = pd.read_excel(xlsx, sheet_name="Notas y limites")
    paises = paises_desde_comparativo(comp)

    meta_cols = ["n_lista", "medicamento", "programa", "presentacion_comparada"]
    tail_cols = ["paises_con_dato", "min_global_USD", "min_global_DOP_BCRD"]
    rest = [c for c in comp.columns if c not in meta_cols + tail_cols]

    comparativo = []
    for _, row in comp.iterrows():
        item = {
            "n": int(row["n_lista"]),
            "medicamento": str(row["medicamento"]),
            "programa": str(row["programa"]),
            "presentacion_comparada": limpio(row.get("presentacion_comparada")),
            "paises_con_dato": int(row["paises_con_dato"] or 0),
            "min_usd": limpio(row["min_global_USD"]),
            "min_dop": limpio(row["min_global_DOP_BCRD"]),
            "paises": {},
        }
        for i, (pid, nombre, _) in enumerate(paises):
            chunk = rest[i * 8 : (i + 1) * 8]
            vals = {CAMPOS[j]: limpio(row[chunk[j]]) for j in range(8)}
            vals["hits"] = int(vals["hits"] or 0)
            vals["nombre"] = nombre
            item["paises"][pid] = vals
        comparativo.append(item)

    detalle = []
    for _, row in det.iterrows():
        detalle.append(
            {
                "n": int(row["n"]),
                "medicamento": str(row["medicamento"]),
                "programa": str(row["programa"]),
                "pais": str(row["pais"]),
                "producto": limpio(row["producto"]),
                "presentacion": limpio(row["presentacion"]),
                "dosis": limpio(row["dosis"]) if "dosis" in row else None,
                "pack": limpio(row["pack"]) if "pack" in row else None,
                "cantidad_concentracion": limpio(row.get("cantidad_concentracion")),
                "unidad_concentracion": limpio(row.get("unidad_concentracion")),
                "tipo_presentacion": limpio(row.get("tipo_presentacion")),
                "cantidad_presentacion": limpio(row.get("cantidad_presentacion")),
                "alcance_presentacion": limpio(row.get("alcance_presentacion")),
                "tipo_precio": limpio(row["tipo_precio"]),
                "farmacia": limpio(row.get("farmacia") or row["tipo_precio"]),
                "precio_local": limpio(row["precio_local"]),
                "moneda": limpio(row["moneda"]),
                "precio_usd": limpio(row["precio_usd"]),
                "precio_dop": limpio(row["precio_dop_bcrd"]),
                "fuente": limpio(row["fuente"]),
                "fecha_dato": limpio(row["fecha_dato"]) if "fecha_dato" in row else None,
            }
        )

    def records(df):
        out = []
        for _, row in df.iterrows():
            out.append({str(c): limpio(row[c]) for c in df.columns})
        return out

    payload = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "paises": [{"id": a, "nombre": b, "corto": c} for a, b, c in paises],
        "medicamentos": [
            {
                "n": int(m["n"]),
                "nombre": str(m["nombre"]),
                "programa": str(m["programa"]),
                "aliases": [str(a) for a in (m.get("aliases") or [])],
            }
            for m in MEDICAMENTOS
        ],
        "comparativo": comparativo,
        "detalle": detalle,
        "fuentes": records(fuentes_df),
        "tasas": records(tasas_df),
        "notas": [limpio(x) for x in notas_df.iloc[:, 0].tolist() if limpio(x)],
    }

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    js = "window.ALTO_COSTO = " + json.dumps(payload, ensure_ascii=False) + ";\n"
    DESTINO.write_text(js, encoding="utf-8")
    print(f"Escrito {DESTINO} ({DESTINO.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
