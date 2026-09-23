"""Indicadores interactivos de Tendencias (figuras Plotly en JSON)."""

from __future__ import annotations

from collections import defaultdict
import re
from typing import Any

from sqlalchemy import text

from scrapper import repositorio_historial as hist
from scrapper.repositorio_historial import _ids, _jsonable, engine

# ISO-3 para choropleth de Plotly
ISO_PAIS: dict[str, str] = {
    "República Dominicana": "DOM",
    "Argentina": "ARG",
    "Brasil": "BRA",
    "Colombia": "COL",
    "Perú": "PER",
    "Chile": "CHL",
    "México": "MEX",
    "Panamá": "PAN",
    "Uruguay": "URY",
    "El Salvador": "SLV",
    "Ecuador": "ECU",
    "Honduras": "HND",
    "Guatemala": "GTM",
    "Nicaragua": "NIC",
    "Costa Rica": "CRI",
}

# IDs numéricos ISO-3166-1 (topojson world-atlas)
ISO_NUM: dict[str, str] = {
    "República Dominicana": "214",
    "Argentina": "032",
    "Brasil": "076",
    "Colombia": "170",
    "Perú": "604",
    "Chile": "152",
    "México": "484",
    "Panamá": "591",
    "Uruguay": "858",
    "El Salvador": "222",
    "Ecuador": "218",
    "Honduras": "340",
    "Guatemala": "320",
    "Nicaragua": "558",
    "Costa Rica": "188",
}

LAYOUT_BASE: dict[str, Any] = {
    "font": {"family": "IBM Plex Sans, system-ui, sans-serif", "size": 13, "color": "#1a2b3c"},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "#f8fafc",
    "margin": {"l": 48, "r": 24, "t": 56, "b": 48},
    "hoverlabel": {"bgcolor": "#fff", "font": {"size": 13}},
}


def _layout(**extra: Any) -> dict[str, Any]:
    base = dict(LAYOUT_BASE)
    base.update(extra)
    return base


def _fecha_ref(fecha: str | None = None) -> str | None:
    fd = str(fecha or "").strip()[:10]
    if fd:
        return fd
    fechas = hist.fechas_disponibles()
    return fechas[-1] if fechas else None


def _filas_vigentes(fecha: str) -> list[dict[str, Any]]:
    """Un registro por (n_lista, producto_key, pais, farmacia) con el precio USD mínimo vigente."""
    asegurar = hist.asegurar_tabla
    asegurar()
    qschema, qtabla, _full, _df = _ids()
    sql = (
        f"SELECT n_lista, "
        f"MAX(medicamento_lista) AS medicamento_lista, "
        f"MAX(nombre_comercial) AS nombre_comercial, "
        f"MAX(concentracion) AS concentracion, "
        f"MAX(presentacion) AS presentacion, "
        f"producto_key, pais, farmacia, "
        f"MIN(precio_usd) AS precio_usd, MIN(precio) AS precio, MAX(moneda) AS moneda "
        f"FROM {qschema}.{qtabla} "
        f"WHERE fecha_dato <= :fd AND fecha_vista >= :fd "
        f"AND precio_usd IS NOT NULL AND precio_usd > 0 "
        f"GROUP BY n_lista, producto_key, pais, farmacia"
    )
    with engine().connect() as conn:
        rows = conn.execute(text(sql), {"fd": fecha}).mappings().all()
    return [{k: _jsonable(v) for k, v in dict(r).items()} for r in rows]


def _etiqueta_perfil(perfil) -> str:
    if not perfil or not perfil.concentracion:
        return ""
    bits = [perfil.concentracion]
    if perfil.forma:
        bits.append(str(perfil.forma).replace("_", " "))
    if perfil.cantidad:
        bits.append(f"x {perfil.cantidad}")
    if perfil.liberacion == "modificada":
        bits.append("liberación modificada")
    return " · ".join(bits)


def _clave_comparable(fila: dict[str, Any]) -> tuple[str | None, Any, str]:
    """Clave de comparación: misma dosis + forma + cantidad (como el comparativo).

    Returns (clave, perfil, etiqueta). Sin clave → no entra al match estricto.
    """
    try:
        from scrapper.equivalencia import perfil_desde_fila
    except Exception:
        return None, None, ""
    try:
        perfil = perfil_desde_fila(fila)
    except Exception:
        return None, None, ""
    clave = perfil.clave_presentacion or perfil.clave_medicina
    if not clave:
        return None, perfil, ""
    return clave, perfil, _etiqueta_perfil(perfil)


def _min_por_pais_principio(filas: list[dict[str, Any]]) -> dict[int, dict[str, float]]:
    """Compat: n_lista → {pais: min_usd} solo sobre filas con presentación comparable.

    Preferimos el mínimo dentro de la presentación con más países (elegirClave).
    """
    grupos = _grupos_comparables(filas)
    out: dict[int, dict[str, float]] = {}
    for n, mapa in _elegir_por_principio(grupos).items():
        out[n] = {p: v["precio_usd"] for p, v in mapa.items()}
    return out


def _grupos_comparables(filas: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    """clave_presentacion → {pais: mejor fila}."""
    try:
        from scrapper.exclusiones_comparables import (
            clave_excluida,
            fila_excluida_de_comparacion,
            recargar,
        )

        recargar()
    except Exception:
        clave_excluida = lambda _c: False  # noqa: E731
        fila_excluida_de_comparacion = lambda _f, clave=None: False  # noqa: E731

    grupos: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for f in filas:
        clave, perfil, etiqueta = _clave_comparable(f)
        if not clave:
            continue
        if clave_excluida(clave):
            continue
        if fila_excluida_de_comparacion(f, clave=clave):
            continue
        try:
            usd = float(f["precio_usd"])
            pais = str(f["pais"])
        except (TypeError, ValueError, KeyError):
            continue
        if usd <= 0 or not pais:
            continue
        cur = grupos[clave].get(pais)
        if cur is None or usd < float(cur["precio_usd"]):
            row = dict(f)
            row["_clave"] = clave
            row["_perfil"] = perfil
            row["_etiqueta"] = etiqueta
            row["precio_usd"] = usd
            grupos[clave][pais] = row
    return grupos


def _elegir_por_principio(
    grupos: dict[str, dict[str, dict[str, Any]]],
) -> dict[int, dict[str, dict[str, Any]]]:
    """Por n_lista elige la clave con más países (y más filas)."""
    por_n: dict[int, list[tuple[str, dict[str, dict[str, Any]]]]] = defaultdict(list)
    for clave, mapa in grupos.items():
        try:
            n = int(str(clave).split("|", 1)[0])
        except (TypeError, ValueError):
            continue
        por_n[n].append((clave, mapa))

    elegidos: dict[int, dict[str, dict[str, Any]]] = {}
    for n, cands in por_n.items():
        cands.sort(key=lambda x: (-len(x[1]), -sum(1 for _ in x[1]), x[0]))
        elegidos[n] = cands[0][1]
    return elegidos


def _mejor_fila_pais(
    filas: list[dict[str, Any]],
) -> dict[tuple[int, str], dict[str, Any]]:
    """(n_lista, pais) → fila de la presentación elegida con menor precio_usd."""
    grupos = _grupos_comparables(filas)
    elegidos = _elegir_por_principio(grupos)
    best: dict[tuple[int, str], dict[str, Any]] = {}
    for n, mapa in elegidos.items():
        for pais, fila in mapa.items():
            best[(n, pais)] = fila
    return best


def _detalle_wins_pais(
    filas: list[dict[str, Any]],
    nombres: dict[int, str],
    fuentes: dict[tuple[Any, str, str], str],
) -> dict[str, list[dict[str, Any]]]:
    """Por país: presentaciones comparables donde ese país es el más barato."""
    grupos = _grupos_comparables(filas)
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for clave, mapa in grupos.items():
        if len(mapa) < 2:
            continue
        precios = {p: float(f["precio_usd"]) for p, f in mapa.items()}
        barato = min(precios.values())
        if barato <= 0:
            continue
        ganadores = [p for p, v in precios.items() if abs(v - barato) < 1e-9]
        for p in ganadores:
            fila = mapa[p]
            try:
                n = int(fila["n_lista"])
            except (TypeError, ValueError, KeyError):
                continue
            farm = str(fila.get("farmacia") or "")
            out[p].append(
                {
                    "n_lista": n,
                    "principio": nombres.get(n) or str(fila.get("medicamento_lista") or f"N{n}"),
                    "presentacion": fila.get("_etiqueta") or fila.get("presentacion") or fila.get("concentracion"),
                    "nombre_comercial": fila.get("nombre_comercial"),
                    "farmacia": farm or None,
                    "precio": fila.get("precio"),
                    "moneda": fila.get("moneda"),
                    "precio_usd": round(float(fila["precio_usd"]), 4),
                    "fuente_url": fuentes.get((n, p, farm)) if farm else None,
                    "paises_en_juego": len(mapa),
                    "clave": clave,
                    "precios_otros": {
                        op: round(float(ov), 4)
                        for op, ov in sorted(precios.items(), key=lambda x: x[1])
                        if op != p
                    },
                }
            )
    for p in out:
        out[p].sort(key=lambda r: r["precio_usd"] or 0)
    return dict(out)


def _agregar_paises(filas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Wins por país contando solo presentaciones con ≥2 países (misma clave)."""
    grupos = _grupos_comparables(filas)
    wins: dict[str, int] = defaultdict(int)
    suma_rel: dict[str, float] = defaultdict(float)
    cuenta: dict[str, int] = defaultdict(int)
    suma_usd: dict[str, float] = defaultdict(float)

    for _clave, mapa in grupos.items():
        if len(mapa) < 2:
            continue
        precios = {p: float(f["precio_usd"]) for p, f in mapa.items()}
        barato = min(precios.values())
        if barato <= 0:
            continue
        ganadores = [p for p, v in precios.items() if abs(v - barato) < 1e-9]
        for p in ganadores:
            wins[p] += 1
        for p, v in precios.items():
            suma_rel[p] += v / barato
            suma_usd[p] += v
            cuenta[p] += 1

    rows = []
    for pais, n in sorted(cuenta.items(), key=lambda x: (-wins[x[0]], x[1])):
        rows.append(
            {
                "pais": pais,
                "iso": ISO_PAIS.get(pais, ""),
                "iso_num": ISO_NUM.get(pais, ""),
                "veces_mas_barato": int(wins[pais]),
                "principios_con_dato": int(n),
                "pct_mas_barato": round(100.0 * wins[pais] / n, 1) if n else 0.0,
                "indice_vs_minimo": round(suma_rel[pais] / n, 3) if n else None,
                "precio_promedio_usd": round(suma_usd[pais] / n, 2) if n else None,
            }
        )
    rows.sort(key=lambda r: (-r["veces_mas_barato"], r["indice_vs_minimo"] or 99))
    return rows


def _comparar_paises(
    filas: list[dict[str, Any]],
    nombres: dict[int, str],
    seleccion: list[str],
    *,
    require_all: bool = True,
) -> dict[str, Any]:
    """Compara países con misma presentación (dosis+forma+cantidad).

    require_all=True: el par solo cuenta si TODOS los seleccionados tienen la presentación
    (precios compartidos N-way).
    require_all=False: cuenta cada presentación con ≥2 seleccionados presentes
    (conveniencia por tema con badges on/off).
    """
    paises = [str(p).strip() for p in (seleccion or []) if str(p).strip()]
    seen: set[str] = set()
    uniq: list[str] = []
    for p in paises:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    paises = uniq
    vacio = {
        "paises": paises,
        "pais_a": paises[0] if paises else None,
        "pais_b": paises[1] if len(paises) > 1 else None,
        "compartidos": 0,
        "victorias": {p: 0 for p in paises},
        "empates": 0,
        "conveniente": None,
        "ahorro_medio_pct": 0,
        "pares": [],
        "criterio": "misma_presentacion" if require_all else "misma_presentacion_subconjunto",
    }
    if len(paises) < 2:
        return vacio

    grupos = _grupos_comparables(filas)
    pares = []
    wins: dict[str, int] = {p: 0 for p in paises}
    empates = 0
    ahorros: list[float] = []

    for clave, mapa in grupos.items():
        if require_all:
            if any(p not in mapa for p in paises):
                continue
            presentes = list(paises)
        else:
            presentes = [p for p in paises if p in mapa]
            if len(presentes) < 2:
                continue
        precios = {p: float(mapa[p]["precio_usd"]) for p in presentes}
        if any(v <= 0 for v in precios.values()):
            continue
        minimo = min(precios.values())
        maximo = max(precios.values())
        ganadores = [p for p, v in precios.items() if abs(v - minimo) < 1e-9]
        if len(ganadores) == 1:
            wins[ganadores[0]] += 1
            mas_barato = ganadores[0]
        else:
            empates += 1
            mas_barato = "empate"
        ahorro_pct = round(100.0 * (maximo - minimo) / maximo, 1) if maximo > 0 else 0.0
        ahorros.append(ahorro_pct)
        muestra = mapa[presentes[0]]
        try:
            n = int(muestra["n_lista"])
        except (TypeError, ValueError, KeyError):
            continue
        etiqueta = muestra.get("_etiqueta") or ""
        principio = nombres.get(n) or str(muestra.get("medicamento_lista") or f"N{n}")
        pares.append(
            {
                "n_lista": n,
                "clave": clave,
                "principio": principio,
                "presentacion": etiqueta,
                "label": f"{principio} · {etiqueta}" if etiqueta else principio,
                "precios": {p: round(precios[p], 2) for p in presentes},
                "precio_a": round(precios[paises[0]], 2) if paises[0] in precios else None,
                "precio_b": (
                    round(precios[paises[1]], 2)
                    if len(paises) > 1 and paises[1] in precios
                    else None
                ),
                "mas_barato": mas_barato,
                "ahorro_usd": round(maximo - minimo, 2),
                "ahorro_pct": ahorro_pct,
                "paises_en_par": presentes,
                "evidencia": {
                    p: {
                        "nombre_comercial": mapa[p].get("nombre_comercial"),
                        "farmacia": mapa[p].get("farmacia"),
                        "precio": mapa[p].get("precio"),
                        "moneda": mapa[p].get("moneda"),
                        "precio_usd": round(precios[p], 2),
                        "concentracion": mapa[p].get("concentracion"),
                        "presentacion": mapa[p].get("presentacion") or etiqueta,
                        "producto_key": mapa[p].get("producto_key"),
                    }
                    for p in presentes
                },
            }
        )

    pares.sort(key=lambda p: -p["ahorro_pct"])
    top = max(wins.values()) if wins else 0
    lideres = [p for p, v in wins.items() if v == top and top > 0]
    conveniente = lideres[0] if len(lideres) == 1 else ("Empate" if lideres else None)

    return {
        "paises": paises,
        "pais_a": paises[0],
        "pais_b": paises[1] if len(paises) > 1 else None,
        "compartidos": len(pares),
        "victorias": wins,
        "gana_a": wins.get(paises[0], 0),
        "gana_b": wins.get(paises[1], 0) if len(paises) > 1 else 0,
        "empates": empates,
        "conveniente": conveniente,
        "ahorro_medio_pct": round(sum(ahorros) / len(ahorros), 1) if ahorros else 0,
        "pares": pares[:80],
        "criterio": "misma_presentacion" if require_all else "misma_presentacion_subconjunto",
    }


def _detalle_wins_lab(
    filas: list[dict[str, Any]],
    labs: dict[tuple[Any, str, str], str],
    nombres: dict[int, str],
    fuentes: dict[tuple[Any, str, str], str],
) -> dict[str, list[dict[str, Any]]]:
    """Por laboratorio: principios donde ese lab tiene el precio mínimo."""
    # (n, lab) → best fila
    best: dict[tuple[int, str], dict[str, Any]] = {}
    por_prin_lab: dict[int, dict[str, float]] = defaultdict(dict)
    for f in filas:
        try:
            n = int(f["n_lista"])
            usd = float(f["precio_usd"])
            pais = str(f["pais"])
            farm = str(f.get("farmacia") or "")
        except (TypeError, ValueError, KeyError):
            continue
        lab = labs.get((n, pais, farm))
        if not lab:
            continue
        cur = por_prin_lab[n].get(lab)
        if cur is None or usd < cur:
            por_prin_lab[n][lab] = usd
            best[(n, lab)] = f

    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for n, por_lab in por_prin_lab.items():
        if not por_lab:
            continue
        barato = min(por_lab.values())
        for lab, v in por_lab.items():
            if abs(v - barato) >= 1e-9:
                continue
            fila = best.get((n, lab)) or {}
            pais = str(fila.get("pais") or "")
            farm = str(fila.get("farmacia") or "")
            out[lab].append(
                {
                    "n_lista": n,
                    "principio": nombres.get(n) or str(fila.get("medicamento_lista") or f"N{n}"),
                    "nombre_comercial": fila.get("nombre_comercial"),
                    "pais": pais or None,
                    "farmacia": farm or None,
                    "precio": fila.get("precio"),
                    "moneda": fila.get("moneda"),
                    "precio_usd": round(float(v), 4),
                    "fuente_url": fuentes.get((n, pais, farm)) if farm else None,
                    "labs_en_juego": len(por_lab),
                }
            )
    for lab in out:
        out[lab].sort(key=lambda r: r["precio_usd"] or 0)
    return dict(out)


def _labs_por_clave() -> dict[tuple[Any, str, str], str]:
    """(n_lista, pais, farmacia) → laboratorio desde precios actuales."""
    try:
        from scrapper import repositorio as repo

        filas = repo.listar_filas()
    except Exception:
        return {}
    out: dict[tuple[Any, str, str], str] = {}
    for f in filas:
        lab = str(f.get("laboratorio") or "").strip()
        if not lab or lab.lower() in ("nan", "none", "-", "n/a"):
            continue
        # Filtrar códigos internos (ANDA/NDA, SKU) y etiquetas de servicio
        if re.match(r"^\d{4}[A-Z]?-?\d+", lab, re.I) or re.match(r"^(ANDA|NDA|BLA)\b", lab, re.I):
            continue
        if len(lab) < 3 or lab.isdigit():
            continue
        if re.search(r"\b(pick\s*up|delivery|envio|envío|retiro)\b", lab, re.I):
            continue
        n = f.get("n_lista")
        pais = str(f.get("pais") or "").strip()
        farm = str(f.get("farmacia") or "").strip()
        if n is None or not pais or not farm:
            continue
        key = (int(n), pais, farm)
        # Preferir el primer laboratorio no vacío
        out.setdefault(key, lab[:120])
    return out


def _fuentes_vivas() -> dict[tuple[Any, str, str], str]:
    """(n_lista, pais, farmacia) → fuente_url."""
    try:
        from scrapper import repositorio as repo

        filas = repo.listar_filas()
    except Exception:
        return {}
    out: dict[tuple[Any, str, str], str] = {}
    for f in filas:
        url = str(f.get("fuente_url") or "").strip()
        if not url:
            continue
        n = f.get("n_lista")
        pais = str(f.get("pais") or "").strip()
        farm = str(f.get("farmacia") or "").strip()
        if n is None or not pais or not farm:
            continue
        out.setdefault((int(n), pais, farm), url)
    return out


def _agregar_labs(filas: list[dict[str, Any]], labs: dict[tuple[Any, str, str], str]) -> list[dict[str, Any]]:
    # Por presentación comparable: min USD por laboratorio
    grupos = _grupos_comparables(filas)
    por_clave_lab: dict[str, dict[str, float]] = defaultdict(dict)
    for clave, mapa in grupos.items():
        for pais, f in mapa.items():
            try:
                n = int(f["n_lista"])
                usd = float(f["precio_usd"])
                farm = str(f.get("farmacia") or "")
            except (TypeError, ValueError, KeyError):
                continue
            lab = labs.get((n, pais, farm))
            if not lab:
                continue
            cur = por_clave_lab[clave].get(lab)
            if cur is None or usd < cur:
                por_clave_lab[clave][lab] = usd

    wins: dict[str, int] = defaultdict(int)
    suma: dict[str, float] = defaultdict(float)
    cuenta: dict[str, int] = defaultdict(int)

    for _clave, por_lab in por_clave_lab.items():
        if len(por_lab) < 2:
            continue
        barato = min(por_lab.values())
        for lab, v in por_lab.items():
            if abs(v - barato) < 1e-9:
                wins[lab] += 1
            suma[lab] += v
            cuenta[lab] += 1

    rows = []
    for lab, n in cuenta.items():
        if n < 2:
            continue
        rows.append(
            {
                "laboratorio": lab,
                "veces_mas_barato": int(wins[lab]),
                "principios_con_dato": int(n),
                "pct_mas_barato": round(100.0 * wins[lab] / n, 1) if n else 0.0,
                "precio_promedio_usd": round(suma[lab] / n, 2) if n else None,
            }
        )
    rows.sort(key=lambda r: (-r["veces_mas_barato"], r["precio_promedio_usd"] or 1e9))
    return rows[:25]


def _fig_paises(rows: list[dict[str, Any]]):
    import plotly.graph_objects as go

    top = list(reversed(rows[:15]))
    fig = go.Figure(
        go.Bar(
            x=[r["veces_mas_barato"] for r in top],
            y=[r["pais"] for r in top],
            orientation="h",
            marker_color="#003eab",
            text=[f"{r['pct_mas_barato']}%" for r in top],
            textposition="outside",
            hovertemplate=(
                "<b>%{y}</b><br>Veces más barato: %{x}"
                "<br>% del catálogo: %{text}"
                "<br>Índice vs mínimo: %{customdata[0]}"
                "<br>Precio prom. USD: %{customdata[1]}"
                "<extra></extra>"
            ),
            customdata=[[r["indice_vs_minimo"], r["precio_promedio_usd"]] for r in top],
        )
    )
    fig.update_layout(
        **_layout(
            title="Países con precios más baratos<br><sup>Veces que el país ofrece el PVP mínimo del principio</sup>",
            xaxis_title="Veces más barato",
            yaxis_title="",
            height=max(360, 40 + 28 * len(top)),
            showlegend=False,
        )
    )
    return fig


def _fig_labs(rows: list[dict[str, Any]]):
    import plotly.graph_objects as go

    top = list(reversed(rows[:15]))
    fig = go.Figure(
        go.Bar(
            x=[r["veces_mas_barato"] for r in top],
            y=[r["laboratorio"] for r in top],
            orientation="h",
            marker_color="#0f766e",
            text=[f"{r['pct_mas_barato']}%" for r in top],
            textposition="outside",
            hovertemplate=(
                "<b>%{y}</b><br>Veces más barato: %{x}"
                "<br>% del catálogo: %{text}"
                "<br>Precio prom. USD: %{customdata[0]}"
                "<extra></extra>"
            ),
            customdata=[[r["precio_promedio_usd"]] for r in top],
        )
    )
    fig.update_layout(
        **_layout(
            title="Laboratorios con precios más baratos<br><sup>Según laboratorio declarado en la farmacia (cruce con historial USD)</sup>",
            xaxis_title="Veces más barato",
            yaxis_title="",
            height=max(360, 40 + 28 * len(top)),
            showlegend=False,
        )
    )
    return fig


def _fig_mapa(rows: list[dict[str, Any]], pais_a: str | None, pais_b: str | None):
    import plotly.graph_objects as go

    locs = [r["iso"] for r in rows if r.get("iso")]
    z = [r["pct_mas_barato"] for r in rows if r.get("iso")]
    text = [r["pais"] for r in rows if r.get("iso")]
    custom = [[r["veces_mas_barato"], r["precio_promedio_usd"]] for r in rows if r.get("iso")]

    fig = go.Figure(
        go.Choropleth(
            locations=locs,
            z=z,
            text=text,
            customdata=custom,
            colorscale=[
                [0.0, "#e8f0fb"],
                [0.5, "#5b8fd9"],
                [1.0, "#003eab"],
            ],
            colorbar_title="% más barato",
            marker_line_color="#fff",
            marker_line_width=0.6,
            hovertemplate=(
                "<b>%{text}</b><br>% veces más barato: %{z}%"
                "<br>Veces: %{customdata[0]}"
                "<br>Precio prom. USD: %{customdata[1]}"
                "<extra></extra>"
            ),
        )
    )
    # Destacar países seleccionados con scattergeo
    sel = []
    for p, color in ((pais_a, "#dc2626"), (pais_b, "#ea580c")):
        if not p:
            continue
        iso = ISO_PAIS.get(p)
        if not iso:
            continue
        sel.append(
            go.Scattergeo(
                locations=[iso],
                locationmode="ISO-3",
                mode="markers+text",
                text=[p],
                textposition="top center",
                marker={"size": 14, "color": color, "line": {"width": 2, "color": "#fff"}},
                name=p,
                hovertemplate=f"<b>{p}</b> (seleccionado)<extra></extra>",
            )
        )
    for tr in sel:
        fig.add_trace(tr)

    fig.update_layout(
        **_layout(
            title="Mapa de conveniencia por país<br><sup>Color = % de principios en los que el país es el más barato. Selecciona 2 países abajo para comparar.</sup>",
            geo={
                "showframe": False,
                "showcoastlines": True,
                "coastlinecolor": "#94a3b8",
                "projection_type": "natural earth",
                "bgcolor": "rgba(0,0,0,0)",
                "landcolor": "#f1f5f9",
                "lakecolor": "#e0f2fe",
                "scope": "world",
                "lataxis_range": [-60, 75],
                "lonaxis_range": [-120, 20],
            },
            height=480,
            margin={"l": 8, "r": 8, "t": 64, "b": 8},
        )
    )
    return fig


def _fig_comparar(cmp: dict[str, Any]):
    import plotly.graph_objects as go

    pares = list(reversed((cmp.get("pares") or [])[:20]))
    if not pares:
        fig = go.Figure()
        fig.update_layout(
            **_layout(
                title=f"Comparativo {cmp['pais_a']} vs {cmp['pais_b']}",
                annotations=[
                    {
                        "text": "No hay principios en común con precio en ambos países.",
                        "xref": "paper",
                        "yref": "paper",
                        "x": 0.5,
                        "y": 0.5,
                        "showarrow": False,
                        "font": {"size": 15, "color": "#64748b"},
                    }
                ],
                height=280,
            )
        )
        return fig

    y = [(p.get("label") or p.get("principio") or "")[:48] for p in pares]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name=cmp["pais_a"],
            y=y,
            x=[p["precio_a"] for p in pares],
            orientation="h",
            marker_color="#003eab",
            hovertemplate="<b>%{y}</b><br>" + cmp["pais_a"] + ": %{x:,.2f} USD<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name=cmp["pais_b"],
            y=y,
            x=[p["precio_b"] for p in pares],
            orientation="h",
            marker_color="#ea580c",
            hovertemplate="<b>%{y}</b><br>" + cmp["pais_b"] + ": %{x:,.2f} USD<extra></extra>",
        )
    )
    fig.update_layout(
        **_layout(
            barmode="group",
            title=(
                f"{cmp['pais_a']} vs {cmp['pais_b']}<br>"
                f"<sup>Conveniente: <b>{cmp['conveniente']}</b> · "
                f"{cmp['gana_a']}–{cmp['gana_b']} (empates {cmp['empates']}) · "
                f"{cmp['compartidos']} principios compartidos · "
                f"brecha media {cmp['ahorro_medio_pct']}%</sup>"
            ),
            xaxis_title="Precio mínimo USD",
            yaxis_title="",
            height=max(380, 48 + 26 * len(pares)),
            legend={"orientation": "h", "y": 1.02, "x": 0},
        )
    )
    return fig


def _fig_wins_pie(cmp: dict[str, Any]):
    import plotly.graph_objects as go

    labels = [cmp["pais_a"], cmp["pais_b"], "Empate"]
    values = [cmp["gana_a"], cmp["gana_b"], cmp["empates"]]
    colors = ["#003eab", "#ea580c", "#94a3b8"]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.45,
            marker_colors=colors,
            textinfo="label+percent",
            hovertemplate="%{label}: %{value} principios<extra></extra>",
        )
    )
    fig.update_layout(
        **_layout(
            title="¿Quién gana más veces?",
            height=340,
            showlegend=False,
            margin={"l": 20, "r": 20, "t": 56, "b": 20},
        )
    )
    return fig


def panel_graficos(
    *,
    fecha: str | None = None,
    pais_a: str | None = None,
    pais_b: str | None = None,
    paises_cmp: list[str] | None = None,
    incluir_figuras: bool = False,
) -> dict[str, Any]:
    """Devuelve indicadores tabulares (+ figuras Plotly opcionales)."""
    fd = _fecha_ref(fecha)
    if not fd:
        return {"ok": False, "error": "Sin fechas en el historial.", "figuras": {}}

    filas = _filas_vigentes(fd)
    if not filas:
        return {"ok": False, "error": f"Sin precios vigentes en {fd}.", "figuras": {}, "fecha": fd}

    rows_paises = _agregar_paises(filas)
    labs_map = _labs_por_clave()
    rows_labs = _agregar_labs(filas, labs_map)

    nombres: dict[int, str] = {}
    for f in filas:
        try:
            n = int(f["n_lista"])
        except (TypeError, ValueError):
            continue
        nombres.setdefault(n, str(f.get("medicamento_lista") or f"N{n}"))

    por_prin = _min_por_pais_principio(filas)
    paises_lista = sorted({r["pais"] for r in rows_paises})

    seleccion: list[str] = []
    for p in list(paises_cmp or []) + [pais_a or "", pais_b or ""]:
        p = str(p or "").strip()
        if p and p in paises_lista and p not in seleccion:
            seleccion.append(p)
    if len(seleccion) < 2:
        prefer = "República Dominicana"
        if prefer in paises_lista and prefer not in seleccion:
            seleccion.insert(0, prefer)
        for r in rows_paises:
            if r["pais"] not in seleccion:
                seleccion.append(r["pais"])
            if len(seleccion) >= 2:
                break

    pa = seleccion[0] if seleccion else None
    pb = seleccion[1] if len(seleccion) > 1 else None
    comparar = _comparar_paises(filas, nombres, seleccion) if len(seleccion) >= 2 else None

    fuentes = _fuentes_vivas()
    if comparar and comparar.get("pares"):
        for par in comparar["pares"]:
            evid = par.get("evidencia") or {}
            for p, ev in evid.items():
                farm = str(ev.get("farmacia") or "")
                n = par.get("n_lista")
                if farm and n is not None and not ev.get("fuente_url"):
                    ev["fuente_url"] = fuentes.get((int(n), p, farm))

    detalle = {
        "por_pais": _detalle_wins_pais(filas, nombres, fuentes),
        "por_lab": _detalle_wins_lab(filas, labs_map, nombres, fuentes),
        "fecha": fd,
        "nota": (
            "Solo se comparan ofertas con la misma presentación comparable "
            "(principio + dosis + forma + cantidad de unidades), igual que el comparativo. "
            "El enlace abre la fuente de la farmacia cuando está disponible."
        ),
    }

    figuras: dict[str, Any] = {}
    if incluir_figuras:
        figuras = {
            "paises_baratos": _fig_paises(rows_paises).to_plotly_json(),
            "laboratorios": _fig_labs(rows_labs).to_plotly_json() if rows_labs else None,
            "mapa": _fig_mapa(rows_paises, pa, pb).to_plotly_json(),
            "comparar": _fig_comparar(comparar).to_plotly_json() if comparar else None,
            "comparar_pie": _fig_wins_pie(comparar).to_plotly_json() if comparar else None,
        }

    return {
        "ok": True,
        "fecha": fd,
        "fechas": hist.fechas_disponibles(),
        "paises": paises_lista,
        "pais_a": pa,
        "pais_b": pb,
        "paises_cmp": seleccion,
        "comparar": comparar,
        "detalle": detalle,
        "resumen": {
            "principios": len(por_prin),
            "paises": len(paises_lista),
            "top_pais": rows_paises[0]["pais"] if rows_paises else None,
            "top_lab": rows_labs[0]["laboratorio"] if rows_labs else None,
            "comparar": {
                "conveniente": comparar["conveniente"] if comparar else None,
                "compartidos": comparar["compartidos"] if comparar else 0,
                "gana_a": comparar["gana_a"] if comparar else 0,
                "gana_b": comparar["gana_b"] if comparar else 0,
                "ahorro_medio_pct": comparar["ahorro_medio_pct"] if comparar else 0,
                "victorias": comparar["victorias"] if comparar else {},
            }
            if comparar
            else None,
        },
        "tablas": {
            "paises": rows_paises,
            "laboratorios": rows_labs,
        },
        "figuras": figuras,
    }


def catalogo_temas(*, fecha: str | None = None) -> dict[str, Any]:
    """Lista de temas EMA con data comparable (≥1 presentación en ≥2 países)."""
    from scrapper import repositorio_ema as ema

    fd = _fecha_ref(fecha)
    filas = _filas_vigentes(fd) if fd else []
    por_n: dict[int, list[dict[str, Any]]] = defaultdict(list)
    con_precio: set[int] = set()
    for f in filas:
        try:
            n = int(f["n_lista"])
        except (TypeError, ValueError, KeyError):
            continue
        con_precio.add(n)
        por_n[n].append(f)

    temas = []
    omitidos_sin_par = 0
    for t in ema.matriz_temas_ema():
        nset = set(t.get("n_listas") or [])
        filas_tema: list[dict[str, Any]] = []
        for n in nset:
            filas_tema.extend(por_n.get(n) or [])
        # Misma regla que el panel: presentación comparable en ≥2 países.
        n_comparables = 0
        if len(filas_tema) >= 2:
            for mapa in _grupos_comparables(filas_tema).values():
                if len(mapa) >= 2:
                    n_comparables += 1
        if n_comparables < 1:
            omitidos_sin_par += 1
            continue
        temas.append(
            {
                **{k: v for k, v in t.items() if k != "principios"},
                "principios": t.get("principios") or [],
                "n_con_precio": len(nset & con_precio),
                "n_comparables": n_comparables,
            }
        )
    return {
        "ok": True,
        "fecha": fd,
        "temas": temas,
        "total": len(temas),
        "omitidos_sin_comparable": omitidos_sin_par,
        "nota": (
            "Temas EMA con al menos una presentación comparable "
            "(misma dosis + forma + cantidad en ≥2 países). "
            "Se omiten términos genéricos y temas sin par usable."
        ),
    }


def panel_tema(
    *,
    tema_id: str,
    fecha: str | None = None,
    pais_a: str | None = None,
    pais_b: str | None = None,
    paises_cmp: list[str] | None = None,
) -> dict[str, Any]:
    """Conveniencia por tema: matches de presentación + score de país."""
    from scrapper import repositorio_ema as ema

    tema = ema.principios_de_tema(tema_id)
    if not tema:
        return {"ok": False, "error": f"Tema no encontrado: {tema_id}"}

    fd = _fecha_ref(fecha)
    if not fd:
        return {"ok": False, "error": "Sin fechas en el historial.", "tema": tema}

    n_ok = set(int(x) for x in (tema.get("n_listas") or []))
    filas_all = _filas_vigentes(fd)
    filas = []
    for f in filas_all:
        try:
            if int(f["n_lista"]) in n_ok:
                filas.append(f)
        except (TypeError, ValueError, KeyError):
            continue

    nombres: dict[int, str] = {}
    for p in tema.get("principios") or []:
        try:
            nombres[int(p["n_lista"])] = str(p.get("medicamento") or f"N{p['n_lista']}")
        except (TypeError, ValueError, KeyError):
            continue
    for f in filas:
        try:
            n = int(f["n_lista"])
        except (TypeError, ValueError, KeyError):
            continue
        nombres.setdefault(n, str(f.get("medicamento_lista") or f"N{n}"))

    rows_paises_global = _agregar_paises(filas)
    paises_lista = sorted({r["pais"] for r in rows_paises_global}) or sorted(
        {str(f.get("pais")) for f in filas if f.get("pais")}
    )

    seleccion: list[str] = []
    for p in list(paises_cmp or []) + [pais_a or "", pais_b or ""]:
        p = str(p or "").strip()
        if p and p in paises_lista and p not in seleccion:
            seleccion.append(p)
    # Sin filtro explícito → todos los países con precio en el tema (badges).
    if not seleccion:
        prefer = "República Dominicana"
        orden = list(paises_lista)
        if prefer in orden:
            orden = [prefer] + [p for p in orden if p != prefer]
        seleccion = orden
    elif len(seleccion) < 2 and len(paises_lista) >= 2:
        for p in paises_lista:
            if p not in seleccion:
                seleccion.append(p)
            if len(seleccion) >= 2:
                break

    comparar = (
        _comparar_paises(filas, nombres, seleccion, require_all=False)
        if len(seleccion) >= 2
        else None
    )
    fuentes = _fuentes_vivas()
    if comparar and comparar.get("pares"):
        for par in comparar["pares"]:
            evid = par.get("evidencia") or {}
            for p, ev in evid.items():
                farm = str(ev.get("farmacia") or "")
                n = par.get("n_lista")
                if farm and n is not None and not ev.get("fuente_url"):
                    ev["fuente_url"] = fuentes.get((int(n), p, farm))

    # Score del panel = mismo universo que el modal: solo países seleccionados
    # y presentaciones donde TODOS los seleccionados tienen match (dosis+forma+cantidad).
    rows_paises: list[dict[str, Any]] = []
    if comparar and comparar.get("pares"):
        wins = comparar.get("victorias") or {}
        n_casos = int(comparar.get("compartidos") or 0) or 1
        suma_usd: dict[str, float] = defaultdict(float)
        cuenta: dict[str, int] = defaultdict(int)
        for par in comparar.get("pares") or []:
            for p, usd in (par.get("precios") or {}).items():
                try:
                    v = float(usd)
                except (TypeError, ValueError):
                    continue
                if v <= 0:
                    continue
                suma_usd[p] += v
                cuenta[p] += 1
        for p in seleccion:
            w = int(wins.get(p) or 0)
            n = int(cuenta.get(p) or 0)
            rows_paises.append(
                {
                    "pais": p,
                    "iso": ISO_PAIS.get(p, ""),
                    "iso_num": ISO_NUM.get(p, ""),
                    "veces_mas_barato": w,
                    "principios_con_dato": n,
                    "pct_mas_barato": round(100.0 * w / n_casos, 1) if n_casos else 0.0,
                    "precio_promedio_usd": round(suma_usd[p] / n, 2) if n else None,
                }
            )
        rows_paises.sort(key=lambda r: (-r["veces_mas_barato"], r["precio_promedio_usd"] or 1e18))

    # Tablas por principio (agrupa pares del tema)
    por_principio: dict[int, list[dict[str, Any]]] = defaultdict(list)
    if comparar:
        for par in comparar.get("pares") or []:
            try:
                n = int(par["n_lista"])
            except (TypeError, ValueError, KeyError):
                continue
            por_principio[n].append(par)

    tablas_principio = []
    for n, pares in sorted(por_principio.items(), key=lambda x: nombres.get(x[0], "").lower()):
        tablas_principio.append(
            {
                "n_lista": n,
                "principio": nombres.get(n) or f"N{n}",
                "casos": len(pares),
                "pares": pares,
            }
        )

    conveniente = None
    if comparar and comparar.get("conveniente") and comparar["conveniente"] != "Empate":
        conveniente = comparar["conveniente"]
    elif rows_paises:
        conveniente = rows_paises[0]["pais"]

    sel_txt = " · ".join(seleccion) if seleccion else "—"
    return {
        "ok": True,
        "fecha": fd,
        "fechas": hist.fechas_disponibles(),
        "tema": {
            "id": tema["id"],
            "label": tema.get("label") or tema.get("label_es") or tema.get("label_en"),
            "label_es": tema.get("label_es"),
            "label_en": tema.get("label_en"),
            "n_principios": tema.get("n_principios"),
            "principios": tema.get("principios") or [],
        },
        "paises": paises_lista,
        "paises_cmp": seleccion,
        "pais_a": seleccion[0] if seleccion else None,
        "pais_b": seleccion[1] if len(seleccion) > 1 else None,
        "comparar": comparar,
        "tablas": {
            "paises": rows_paises,
            "paises_global": rows_paises_global,
            "por_principio": tablas_principio,
        },
        "detalle": {
            "por_pais": _detalle_wins_pais(
                [f for f in filas if str(f.get("pais") or "") in set(seleccion)],
                nombres,
                fuentes,
            ) if seleccion else {},
            "fecha": fd,
            "nota": (
                f"Tema EMA «{tema.get('label') or tema.get('label_en')}». "
                f"Comparación entre {sel_txt}. "
                "Solo presentaciones con misma dosis, forma y cantidad en todos los países seleccionados."
            ),
        },
        "resumen": {
            "conveniente": conveniente,
            "principios_tema": len(n_ok),
            "principios_con_precio": len({int(f["n_lista"]) for f in filas if f.get("n_lista") is not None}),
            "casos_comparables": int((comparar or {}).get("compartidos") or 0),
            "paises": len(seleccion) if seleccion else len(paises_lista),
            "victorias": (comparar or {}).get("victorias") or {r["pais"]: r["veces_mas_barato"] for r in rows_paises},
            "ahorro_medio_pct": (comparar or {}).get("ahorro_medio_pct") or 0,
            "criterio": "misma_presentacion_entre_seleccionados",
        },
    }

