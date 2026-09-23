"""Detecta alertas de patentes FDA comparando snapshots (y horizonte de vencimiento).

Tipos:
  - paso_a_expirada: en el snapshot anterior estaba vigente y ahora expirada
  - vence_hoy: expiration_date = hoy y vigente/vence_hoy
  - vence_en_30d / vence_en_60d / vence_en_90d: sigue vigente y vence dentro de N días

EMA: placeholder (sin fuente de patentes aún).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from db import engine, resumen_config
from scrapper.fda_patentes import (
    _estado_fecha,
    url_google_patente,
    url_orange_patent_info,
    url_orange_patente,
    url_purple_patent_list_patente,
)
from scrapper.repositorio_alertas_patentes import (
    actualizar_dias_restantes,
    asegurar_tabla,
    existe_alerta,
    existe_alerta_patente,
    registrar_alerta,
)
from scrapper.repositorio_fda_info import TABLA as TABLA_FDA


def _q(tabla: str) -> tuple[str, str]:
    schema = resumen_config()["schema"]
    return f"[{schema}]", f"[{tabla}]"


def _parse_fd(v: Any) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()[:10]
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _parse_patentes(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [p for p in raw if isinstance(p, dict)]
    if isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if isinstance(data, list):
            return [p for p in data if isinstance(p, dict)]
    return []


def _clave_patente(p: dict[str, Any]) -> str:
    pn = str(p.get("patent_no") or "").replace(",", "").strip().upper()
    prod = str(
        p.get("appl_no")
        or p.get("bla_number")
        or p.get("product_no")
        or ""
    ).strip()
    fuente = str(p.get("fuente") or "").strip().lower()
    return f"{fuente}|{pn}|{prod}"


def _clave_producto(p: dict[str, Any]) -> str:
    return str(p.get("appl_no") or p.get("bla_number") or p.get("product_no") or "").strip()


def periodos_fda() -> list[date]:
    qschema, qtabla = _q(TABLA_FDA)
    sql = f"SELECT DISTINCT fecha_dato FROM {qschema}.{qtabla} ORDER BY fecha_dato DESC"
    with engine().connect() as conn:
        rows = conn.execute(text(sql)).fetchall()
    out = []
    for r in rows:
        fd = _parse_fd(r[0])
        if fd:
            out.append(fd)
    return out


def _cargar_snapshot_fda(fecha_dato: date) -> list[dict[str, Any]]:
    qschema, qtabla = _q(TABLA_FDA)
    sql = (
        f"SELECT n_lista, medicamento_lista, patentes_json, fecha_dato "
        f"FROM {qschema}.{qtabla} WHERE fecha_dato = :fd"
    )
    with engine().connect() as conn:
        rows = conn.execute(text(sql), {"fd": fecha_dato}).mappings().all()
    out = []
    for row in rows:
        out.append(
            {
                "n_lista": int(row["n_lista"]),
                "medicamento_lista": row.get("medicamento_lista"),
                "patentes": _parse_patentes(row.get("patentes_json")),
                "fecha_dato": _parse_fd(row.get("fecha_dato")),
            }
        )
    return out


def _mapa_patentes(snapshot: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapa: dict[str, dict[str, Any]] = {}
    for fila in snapshot:
        for p in fila.get("patentes") or []:
            pn = str(p.get("patent_no") or "").replace(",", "").strip()
            if not pn:
                continue
            key = f"{fila['n_lista']}|{_clave_patente(p)}"
            mapa[key] = {
                "n_lista": fila["n_lista"],
                "medicamento_lista": fila.get("medicamento_lista"),
                "patente": p,
            }
    return mapa


def detectar_fda(
    *,
    fecha_actual: date | None = None,
    fecha_anterior: date | None = None,
    horizonte_dias: tuple[int, ...] = (30, 60, 90, 180, 365),
    hoy: date | None = None,
) -> dict[str, Any]:
    """Compara dos snapshots FDA y registra alertas nuevas.

    Horizonte por defecto: 30, 60, 90, 180 y 365 días.
    """
    asegurar_tabla()
    hoy = hoy or date.today()
    periodos = periodos_fda()
    if not periodos:
        conteo = actualizar_dias_restantes(hoy=hoy)
        return {
            "ok": True,
            "fuente": "fda",
            "mensaje": (
                "No hay snapshots FDA de patentes. "
                f"{conteo.get('mensaje')}"
            ),
            "insertadas": 0,
            "revisadas": 0,
            "dias_actualizados": conteo.get("actualizadas", 0),
        }

    actual = fecha_actual or periodos[0]
    if fecha_anterior:
        anterior = fecha_anterior
    else:
        anteriores = [d for d in periodos if d < actual]
        anterior = anteriores[0] if anteriores else None

    snap_act = _cargar_snapshot_fda(actual)
    mapa_act = _mapa_patentes(snap_act)
    mapa_ant = _mapa_patentes(_cargar_snapshot_fda(anterior)) if anterior else {}

    insertadas = 0
    detalle_tipos: dict[str, int] = {}

    def _reg(
        tipo: str,
        item: dict[str, Any],
        estado_ant: str | None,
        estado_nuevo: str,
        *,
        una_vez: bool = False,
    ) -> None:
        nonlocal insertadas
        p = item["patente"]
        pn = str(p.get("patent_no") or "").replace(",", "").strip()
        clave = _clave_producto(p)
        if una_vez and existe_alerta(
            fuente="fda",
            tipo_alerta=tipo,
            n_lista=item["n_lista"],
            patent_no=pn,
            clave_producto=clave,
        ):
            return
        ok = registrar_alerta(
            {
                "fecha_alerta": hoy,
                "fuente": "fda",
                "tipo_alerta": tipo,
                "n_lista": item["n_lista"],
                "medicamento_lista": item.get("medicamento_lista"),
                "patent_no": pn,
                "clave_producto": clave,
                "estado_anterior": estado_ant,
                "estado_nuevo": estado_nuevo,
                "expiration_date": p.get("expiration_date"),
                "detalle_json": {
                    "fuente_patente": p.get("fuente"),
                    "expiration_text": p.get("expiration_text"),
                    "appl_no": p.get("appl_no"),
                    "appl_type": p.get("appl_type"),
                    "bla_number": p.get("bla_number"),
                    "product_no": p.get("product_no"),
                    "patent_info_url": p.get("patent_info_url") or p.get("fuente_url"),
                    "fuente_url": p.get("fuente_url") or p.get("patent_info_url"),
                    "url": (
                        p.get("patent_info_url")
                        or p.get("fuente_url")
                        or p.get("url_orange")
                        or p.get("url_purple")
                        or p.get("url")
                        or url_orange_patent_info(
                            p.get("appl_type"),
                            p.get("appl_no"),
                            p.get("product_no"),
                        )
                        or url_orange_patente(pn)
                        or url_purple_patent_list_patente(pn)
                    ),
                    "google_patent_url": p.get("google_patent_url") or url_google_patente(pn),
                    "snapshot_actual": actual.isoformat(),
                    "snapshot_anterior": anterior.isoformat() if anterior else None,
                },
            }
        )
        if ok:
            insertadas += 1
            detalle_tipos[tipo] = detalle_tipos.get(tipo, 0) + 1

    # Transiciones vs snapshot anterior
    if anterior:
        for key, item in mapa_act.items():
            p = item["patente"]
            estado_nuevo = str(p.get("estado") or "")
            # Recalcular con hoy por si el scrape es mensual
            exp = _parse_fd(p.get("expiration_date"))
            if exp is not None:
                estado_nuevo = _estado_fecha(exp, hoy)

            prev = mapa_ant.get(key)
            if not prev:
                continue
            estado_ant = str(prev["patente"].get("estado") or "")
            exp_ant = _parse_fd(prev["patente"].get("expiration_date"))
            if exp_ant is not None:
                # Estado que tenía "en el día anterior al actual" usando la fecha del snapshot anterior
                estado_ant = _estado_fecha(exp_ant, anterior)

            if estado_ant == "vigente" and estado_nuevo == "expirada":
                _reg("paso_a_expirada", item, estado_ant, estado_nuevo)

    # Horizonte sobre snapshot actual
    for item in mapa_act.values():
        p = item["patente"]
        exp = _parse_fd(p.get("expiration_date"))
        if exp is None:
            continue
        estado = _estado_fecha(exp, hoy)
        if estado == "vence_hoy":
            _reg("vence_hoy", item, None, estado, una_vez=True)
            continue
        if estado != "vigente":
            continue
        dias = (exp - hoy).days
        for h in sorted(horizonte_dias):
            if 0 < dias <= h:
                _reg(f"vence_en_{h}d", item, None, estado, una_vez=True)
                break  # solo el horizonte más cercano

    # Archivar en historial: si ya se alertó y hoy está expirada, registrar paso_a_expirada.
    # Así la de «vence en 1 día» queda guardada abajo cuando pasa la fecha.
    for item in mapa_act.values():
        p = item["patente"]
        exp = _parse_fd(p.get("expiration_date"))
        if exp is None or exp >= hoy:
            continue
        pn = str(p.get("patent_no") or "").replace(",", "").strip()
        clave = _clave_producto(p)
        if not pn:
            continue
        if not existe_alerta_patente(
            fuente="fda",
            n_lista=item["n_lista"],
            patent_no=pn,
            clave_producto=clave,
        ):
            continue
        _reg("paso_a_expirada", item, "vigente", "expirada", una_vez=True)

    conteo = actualizar_dias_restantes(hoy=hoy)

    return {
        "ok": True,
        "fuente": "fda",
        "fecha_alerta": hoy.isoformat(),
        "snapshot_actual": actual.isoformat(),
        "snapshot_anterior": anterior.isoformat() if anterior else None,
        "revisadas": len(mapa_act),
        "insertadas": insertadas,
        "por_tipo": detalle_tipos,
        "dias_actualizados": conteo.get("actualizadas", 0),
        "mensaje": (
            f"FDA: {insertadas} alerta(s) nueva(s) "
            f"(snapshot {actual.isoformat()}"
            + (f" vs {anterior.isoformat()}" if anterior else " sin anterior")
            + f"); conteo de días: {conteo.get('actualizadas', 0)} fila(s)."
        ),
    }


def detectar_ema() -> dict[str, Any]:
    return {
        "ok": True,
        "fuente": "ema",
        "insertadas": 0,
        "revisadas": 0,
        "mensaje": "EMA: aún no hay fuente de patentes/SPC en el sistema.",
    }


def detectar_todas(**kwargs: Any) -> dict[str, Any]:
    fda = detectar_fda(**kwargs)
    ema = detectar_ema()
    # Si FDA no corrió el conteo (p.ej. sin snapshots), igual refrescar filas existentes.
    conteo = fda.get("dias_actualizados")
    if conteo is None:
        hoy = kwargs.get("hoy") if isinstance(kwargs.get("hoy"), date) else date.today()
        conteo_r = actualizar_dias_restantes(hoy=hoy)
        conteo = conteo_r.get("actualizadas", 0)
        fda["dias_actualizados"] = conteo
    crit = evaluar_criterios_config(hoy=kwargs.get("hoy") if isinstance(kwargs.get("hoy"), date) else date.today())
    return {
        "ok": True,
        "insertadas": int(fda.get("insertadas") or 0)
        + int(ema.get("insertadas") or 0)
        + int(crit.get("insertadas") or 0),
        "dias_actualizados": int(conteo or 0),
        "fda": fda,
        "ema": ema,
        "criterios": crit,
        "mensaje": f"{fda.get('mensaje')} {ema.get('mensaje')} {crit.get('mensaje')}",
    }


def _fuente_patente_match(p: dict[str, Any], filtro: str | None) -> bool:
    f = (filtro or "fda").strip().lower()
    if f not in ("fda", "ema"):
        f = "fda"
    if f == "fda":
        # El snapshot de criterios FDA solo contiene patentes FDA.
        return True
    blob = " ".join(
        str(p.get(k) or "")
        for k in ("fuente", "fuente_patente", "book", "origen")
    ).lower()
    det = p.get("detalle_json") if isinstance(p.get("detalle_json"), dict) else {}
    blob += " " + " ".join(str(det.get(k) or "") for k in ("fuente_patente", "fuente", "url"))
    return "ema" in blob


def evaluar_criterios_config(*, hoy: date | None = None) -> dict[str, Any]:
    """Evalúa criterios del modal y genera notificaciones para el header.

    - Ventana dias_min..dias_max → recordatorio (diario o una vez).
    - Vence hoy / pasó a expirada según flags del criterio.
    """
    from scrapper.repositorio_alertas_patentes import (
        listar_configs,
        registrar_alerta,
        existe_alerta,
    )

    hoy = hoy or date.today()
    configs = listar_configs(solo_activas=True)
    if not configs:
        return {
            "ok": True,
            "insertadas": 0,
            "configs": 0,
            "mensaje": "Sin criterios activos de patentes.",
        }

    periodos = periodos_fda()
    if not periodos:
        return {
            "ok": True,
            "insertadas": 0,
            "configs": len(configs),
            "mensaje": "Criterios activos, pero no hay snapshot FDA para evaluar.",
        }

    snap = _cargar_snapshot_fda(periodos[0])
    mapa = _mapa_patentes(snap)
    insertadas = 0
    por_cfg: dict[str, int] = {}

    for cfg in configs:
        cid = int(cfg["id"])
        dias_min = int(cfg.get("dias_min") if cfg.get("dias_min") is not None else 0)
        dias_max = int(cfg.get("dias_max") or 0)
        if dias_max < 1:
            continue
        avisar_hoy = bool(cfg.get("avisar_vence_hoy", True))
        avisar_paso = bool(cfg.get("avisar_paso_expirada", True))
        diario = bool(cfg.get("avisar_diario", True))
        fuente_f = (str(cfg.get("fuente") or "").strip().lower() or None)
        n_filtro = cfg.get("n_lista")
        tipo = f"criterio_{cid}"

        for item in mapa.values():
            if n_filtro is not None and int(item["n_lista"]) != int(n_filtro):
                continue
            p = item["patente"]
            if not _fuente_patente_match(p, fuente_f):
                continue
            exp = _parse_fd(p.get("expiration_date"))
            if exp is None:
                continue
            estado = _estado_fecha(exp, hoy)
            dias = (exp - hoy).days
            pn = str(p.get("patent_no") or "").replace(",", "").strip()
            if not pn:
                continue
            clave = _clave_producto(p)

            match = False
            estado_nuevo = estado
            if estado == "vence_hoy" and avisar_hoy:
                match = True
            elif estado == "vigente" and dias_min <= dias <= dias_max:
                match = True
            elif estado == "expirada" and avisar_paso and dias >= -1:
                # Solo el día que acaba de vencer (o aún marcada hoy)
                if dias == -1 or (dias < 0 and diario and dias >= -dias_max):
                    match = True
                    estado_nuevo = "expirada"

            if not match:
                continue

            if not diario and existe_alerta(
                fuente="fda",
                tipo_alerta=tipo,
                n_lista=item["n_lista"],
                patent_no=pn,
                clave_producto=clave,
            ):
                continue

            ok = registrar_alerta(
                {
                    "fecha_alerta": hoy,
                    "fuente": "fda",
                    "tipo_alerta": tipo,
                    "n_lista": item["n_lista"],
                    "medicamento_lista": item.get("medicamento_lista"),
                    "patent_no": pn,
                    "clave_producto": clave,
                    "estado_anterior": None,
                    "estado_nuevo": estado_nuevo,
                    "expiration_date": p.get("expiration_date"),
                    "detalle_json": {
                        "config_id": cid,
                        "config_nombre": cfg.get("nombre"),
                        "dias_min": dias_min,
                        "dias_max": dias_max,
                        "dias_restantes_eval": dias,
                        "avisar_diario": diario,
                        "fuente_filtro": fuente_f,
                        "fuente_patente": p.get("fuente"),
                        "patent_info_url": p.get("patent_info_url") or p.get("fuente_url"),
                        "url": p.get("patent_info_url") or p.get("fuente_url") or p.get("url"),
                    },
                }
            )
            if ok:
                insertadas += 1
                por_cfg[str(cid)] = por_cfg.get(str(cid), 0) + 1

    actualizar_dias_restantes(hoy=hoy)
    return {
        "ok": True,
        "insertadas": insertadas,
        "configs": len(configs),
        "por_config": por_cfg,
        "mensaje": (
            f"Criterios: {insertadas} notificación(es) nueva(s) "
            f"desde {len(configs)} criterio(s) activo(s)."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Detectar alertas de patentes FDA/EMA")
    p.add_argument("--fuente", choices=["fda", "ema", "todas"], default="todas")
    args = p.parse_args(argv)
    if args.fuente == "fda":
        r = detectar_fda()
    elif args.fuente == "ema":
        r = detectar_ema()
    else:
        r = detectar_todas()
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
