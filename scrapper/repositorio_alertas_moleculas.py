"""Alertas de moléculas nuevas en FDA / EMA."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import text

from db import engine, resumen_config

TABLA = "medicamentos_alertas_moleculas"

DDL = """
IF NOT EXISTS (
    SELECT 1
    FROM sys.tables t
    INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE t.name = N'{tabla}' AND s.name = N'{schema}'
)
BEGIN
    CREATE TABLE {qschema}.{qtabla} (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        fecha_alerta DATE NOT NULL,
        fuente NVARCHAR(20) NOT NULL,
        tipo_alerta NVARCHAR(40) NOT NULL,
        n_lista INT NOT NULL,
        medicamento_lista NVARCHAR(300) NULL,
        clave_producto NVARCHAR(120) NOT NULL,
        estado_anterior NVARCHAR(80) NULL,
        estado_nuevo NVARCHAR(80) NULL,
        detalle_json NVARCHAR(MAX) NULL,
        leida BIT NOT NULL CONSTRAINT DF_{df}_leida DEFAULT 0,
        fecha_registro DATETIME NOT NULL CONSTRAINT DF_{df}_reg DEFAULT GETDATE(),
        CONSTRAINT UQ_{df} UNIQUE (fuente, tipo_alerta, n_lista, clave_producto)
    );
    CREATE INDEX IX_{df}_fecha ON {qschema}.{qtabla} (fecha_alerta DESC, leida);
    CREATE INDEX IX_{df}_fuente ON {qschema}.{qtabla} (fuente, tipo_alerta);
END
"""


def _ids() -> tuple[str, str, str, str]:
    schema = resumen_config()["schema"]
    return f"[{schema}]", f"[{TABLA}]", f"{schema}.{TABLA}", "mac_amol"


def asegurar_tabla() -> str:
    qschema, qtabla, full, df = _ids()
    schema = resumen_config()["schema"]
    sql = (
        DDL.replace("{qschema}", qschema)
        .replace("{qtabla}", qtabla)
        .replace("{schema}", schema)
        .replace("{tabla}", TABLA)
        .replace("{df}", df)
    )
    with engine().begin() as conn:
        conn.execute(text(sql))
    return full


def _jsonable(v: Any) -> Any:
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def existe_alerta(*, fuente: str, tipo_alerta: str, n_lista: int, clave_producto: str) -> bool:
    asegurar_tabla()
    qschema, qtabla, _, _ = _ids()
    with engine().connect() as conn:
        row = conn.execute(
            text(
                f"""
                SELECT TOP 1 id FROM {qschema}.{qtabla}
                WHERE fuente=:fuente AND tipo_alerta=:tipo AND n_lista=:n AND clave_producto=:clave
                """
            ),
            {
                "fuente": fuente,
                "tipo": tipo_alerta,
                "n": int(n_lista),
                "clave": str(clave_producto)[:120],
            },
        ).first()
    return row is not None


def registrar_alerta(payload: dict[str, Any]) -> bool:
    """Inserta si no existe la misma molécula/evento. True si insertó."""
    asegurar_tabla()
    fuente = str(payload["fuente"])
    tipo = str(payload["tipo_alerta"])
    n_lista = int(payload["n_lista"])
    clave = str(payload.get("clave_producto") or n_lista)[:120]
    if existe_alerta(fuente=fuente, tipo_alerta=tipo, n_lista=n_lista, clave_producto=clave):
        return False
    qschema, qtabla, _, _ = _ids()
    detalle = payload.get("detalle") or payload.get("detalle_json") or {}
    if not isinstance(detalle, str):
        detalle = json.dumps(detalle, ensure_ascii=False, default=_jsonable)
    fd = payload.get("fecha_alerta") or date.today()
    if isinstance(fd, str):
        fd = date.fromisoformat(fd[:10])
    with engine().begin() as conn:
        conn.execute(
            text(
                f"""
                INSERT INTO {qschema}.{qtabla}
                (fecha_alerta, fuente, tipo_alerta, n_lista, medicamento_lista, clave_producto,
                 estado_anterior, estado_nuevo, detalle_json, leida)
                VALUES
                (:fecha, :fuente, :tipo, :n, :med, :clave, :ant, :nuevo, :detalle, 0)
                """
            ),
            {
                "fecha": fd,
                "fuente": fuente,
                "tipo": tipo,
                "n": n_lista,
                "med": (payload.get("medicamento_lista") or "")[:300] or None,
                "clave": clave,
                "ant": payload.get("estado_anterior"),
                "nuevo": payload.get("estado_nuevo"),
                "detalle": detalle,
            },
        )
    return True


def listar_alertas(
    *,
    fuente: str | None = None,
    tipo: str | None = None,
    solo_no_leidas: bool = False,
    limite: int = 200,
) -> list[dict[str, Any]]:
    asegurar_tabla()
    qschema, qtabla, _, _ = _ids()
    where = ["1=1"]
    params: dict[str, Any] = {"lim": max(1, min(int(limite), 2000))}
    if fuente:
        where.append("fuente = :fuente")
        params["fuente"] = fuente
    if tipo:
        where.append("tipo_alerta = :tipo")
        params["tipo"] = tipo
    if solo_no_leidas:
        where.append("leida = 0")
    sql = f"""
    SELECT TOP (:lim) id, fecha_alerta, fuente, tipo_alerta, n_lista, medicamento_lista,
           clave_producto, estado_anterior, estado_nuevo, detalle_json, leida, fecha_registro
    FROM {qschema}.{qtabla}
    WHERE {' AND '.join(where)}
    ORDER BY fecha_alerta DESC, id DESC
    """
    with engine().connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    out = []
    for row in rows:
        item = dict(row)
        raw = item.pop("detalle_json", None)
        if isinstance(raw, str) and raw.strip():
            try:
                item["detalle"] = json.loads(raw)
            except json.JSONDecodeError:
                item["detalle"] = {}
        else:
            item["detalle"] = raw if isinstance(raw, dict) else {}
        item["fecha_alerta"] = _jsonable(item.get("fecha_alerta"))
        item["fecha_registro"] = _jsonable(item.get("fecha_registro"))
        item["leida"] = bool(item.get("leida"))
        out.append(item)
    return out


def resumen_alertas() -> dict[str, Any]:
    asegurar_tabla()
    qschema, qtabla, _, _ = _ids()
    with engine().connect() as conn:
        total = conn.execute(text(f"SELECT COUNT(*) FROM {qschema}.{qtabla}")).scalar() or 0
        nuevas = conn.execute(text(f"SELECT COUNT(*) FROM {qschema}.{qtabla} WHERE leida = 0")).scalar() or 0
        por_fuente = conn.execute(
            text(
                f"""
                SELECT fuente, COUNT(*) AS n
                FROM {qschema}.{qtabla}
                WHERE leida = 0
                GROUP BY fuente
                """
            )
        ).mappings().all()
    return {
        "total": int(total),
        "no_leidas": int(nuevas),
        "por_fuente": {str(r["fuente"]): int(r["n"]) for r in por_fuente},
    }


def marcar_leidas(ids: list[int] | None = None, *, todas: bool = False) -> int:
    asegurar_tabla()
    qschema, qtabla, _, _ = _ids()
    with engine().begin() as conn:
        if todas:
            res = conn.execute(text(f"UPDATE {qschema}.{qtabla} SET leida = 1 WHERE leida = 0"))
            return int(res.rowcount or 0)
        if not ids:
            return 0
        n = 0
        for i in ids:
            res = conn.execute(
                text(f"UPDATE {qschema}.{qtabla} SET leida = 1 WHERE id = :id AND leida = 0"),
                {"id": int(i)},
            )
            n += int(res.rowcount or 0)
        return n
