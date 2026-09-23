"""Log durable de corridas del cron diario (cabecera + pasos por fuente)."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import text

from db import engine, resumen_config

TABLA_CORRIDA = "medicamentos_cron_corridas"
TABLA_PASO = "medicamentos_cron_pasos"

DDL_CORRIDA = """
IF NOT EXISTS (
    SELECT 1
    FROM sys.tables t
    INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE t.name = N'{tabla}' AND s.name = N'{schema}'
)
BEGIN
    CREATE TABLE {qschema}.{qtabla} (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        fecha_corrida DATE NOT NULL,
        inicio DATETIME NOT NULL,
        fin DATETIME NULL,
        estado NVARCHAR(30) NOT NULL,
        argv_json NVARCHAR(400) NULL,
        mensaje NVARCHAR(1000) NULL,
        total_pasos INT NOT NULL CONSTRAINT DF_{df}_tp DEFAULT 0,
        total_ok INT NOT NULL CONSTRAINT DF_{df}_tok DEFAULT 0,
        total_cache INT NOT NULL CONSTRAINT DF_{df}_tc DEFAULT 0,
        total_warn INT NOT NULL CONSTRAINT DF_{df}_tw DEFAULT 0,
        total_error INT NOT NULL CONSTRAINT DF_{df}_te DEFAULT 0,
        total_skip INT NOT NULL CONSTRAINT DF_{df}_ts DEFAULT 0
    );
    CREATE INDEX IX_{df}_fecha ON {qschema}.{qtabla} (fecha_corrida, id DESC);
END
"""

DDL_PASO = """
IF NOT EXISTS (
    SELECT 1
    FROM sys.tables t
    INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE t.name = N'{tabla}' AND s.name = N'{schema}'
)
BEGIN
    CREATE TABLE {qschema}.{qtabla} (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        corrida_id INT NOT NULL,
        orden INT NOT NULL,
        fuente_id NVARCHAR(60) NOT NULL,
        nombre NVARCHAR(120) NULL,
        script NVARCHAR(200) NULL,
        pais NVARCHAR(80) NULL,
        farmacia NVARCHAR(120) NULL,
        inicio DATETIME NOT NULL,
        fin DATETIME NULL,
        duracion_ms INT NULL,
        estado NVARCHAR(20) NOT NULL,
        exit_code INT NULL,
        filas_merge INT NULL,
        mensaje NVARCHAR(1000) NULL,
        detalle NVARCHAR(MAX) NULL
    );
    CREATE INDEX IX_{df}_corrida ON {qschema}.{qtabla} (corrida_id, orden);
    CREATE INDEX IX_{df}_fuente ON {qschema}.{qtabla} (fuente_id, fin DESC);
END
"""


def _ids_corrida() -> tuple[str, str, str, str]:
    schema = resumen_config()["schema"]
    return f"[{schema}]", f"[{TABLA_CORRIDA}]", f"{schema}.{TABLA_CORRIDA}", "mac_cr"


def _ids_paso() -> tuple[str, str, str, str]:
    schema = resumen_config()["schema"]
    return f"[{schema}]", f"[{TABLA_PASO}]", f"{schema}.{TABLA_PASO}", "mac_cp"


def asegurar_tablas() -> None:
    schema = resumen_config()["schema"]
    for tabla, ddl, ids_fn in (
        (TABLA_CORRIDA, DDL_CORRIDA, _ids_corrida),
        (TABLA_PASO, DDL_PASO, _ids_paso),
    ):
        qschema, qtabla, _full, df = ids_fn()
        sql = (
            ddl.replace("{qschema}", qschema)
            .replace("{qtabla}", qtabla)
            .replace("{schema}", schema)
            .replace("{tabla}", tabla)
            .replace("{df}", df)
        )
        with engine().begin() as conn:
            conn.execute(text(sql))


def _jsonable(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat(sep=" ", timespec="seconds")
    if isinstance(v, date):
        return v.isoformat()
    return v


def iniciar_corrida(*, argv: list[str] | None = None, mensaje: str | None = None) -> int:
    asegurar_tablas()
    qschema, qtabla, _full, _df = _ids_corrida()
    with engine().begin() as conn:
        row = conn.execute(
            text(
                f"INSERT INTO {qschema}.{qtabla} "
                "(fecha_corrida, inicio, estado, argv_json, mensaje) "
                "OUTPUT INSERTED.id "
                "VALUES (CAST(GETDATE() AS DATE), GETDATE(), N'running', :argv, :msg)"
            ),
            {
                "argv": json.dumps(argv or [], ensure_ascii=False)[:400],
                "msg": (mensaje or "")[:1000] or None,
            },
        ).first()
    return int(row[0])


def registrar_paso(
    corrida_id: int,
    *,
    orden: int,
    fuente_id: str,
    nombre: str | None = None,
    script: str | None = None,
    pais: str | None = None,
    farmacia: str | None = None,
    inicio: datetime | None = None,
    fin: datetime | None = None,
    estado: str,
    exit_code: int | None = None,
    filas_merge: int | None = None,
    mensaje: str | None = None,
    detalle: str | None = None,
) -> int:
    asegurar_tablas()
    qschema, qtabla, _full, _df = _ids_paso()
    t0 = inicio or datetime.now()
    t1 = fin or datetime.now()
    dur = max(0, int((t1 - t0).total_seconds() * 1000))
    with engine().begin() as conn:
        row = conn.execute(
            text(
                f"INSERT INTO {qschema}.{qtabla} "
                "(corrida_id, orden, fuente_id, nombre, script, pais, farmacia, "
                " inicio, fin, duracion_ms, estado, exit_code, filas_merge, mensaje, detalle) "
                "OUTPUT INSERTED.id "
                "VALUES (:cid, :ord, :fid, :nom, :scr, :pais, :farm, "
                " :ini, :fin, :dur, :est, :ec, :fm, :msg, :det)"
            ),
            {
                "cid": int(corrida_id),
                "ord": int(orden),
                "fid": str(fuente_id or "")[:60],
                "nom": (nombre or "")[:120] or None,
                "scr": (script or "")[:200] or None,
                "pais": (pais or "")[:80] or None,
                "farm": (farmacia or "")[:120] or None,
                "ini": t0,
                "fin": t1,
                "dur": dur,
                "est": str(estado or "ok")[:20],
                "ec": exit_code,
                "fm": filas_merge,
                "msg": (mensaje or "")[:1000] or None,
                "det": (detalle or "")[:20000] or None,
            },
        ).first()
    return int(row[0])


def finalizar_corrida(
    corrida_id: int,
    *,
    estado: str = "done",
    mensaje: str | None = None,
) -> dict[str, Any]:
    asegurar_tablas()
    qschema_c, qtabla_c, _fc, _dfc = _ids_corrida()
    qschema_p, qtabla_p, _fp, _dfp = _ids_paso()
    with engine().begin() as conn:
        counts = conn.execute(
            text(
                f"""
                SELECT
                  COUNT(*) AS total_pasos,
                  SUM(CASE WHEN estado = N'ok' THEN 1 ELSE 0 END) AS total_ok,
                  SUM(CASE WHEN estado = N'cache' THEN 1 ELSE 0 END) AS total_cache,
                  SUM(CASE WHEN estado = N'warn' THEN 1 ELSE 0 END) AS total_warn,
                  SUM(CASE WHEN estado = N'error' THEN 1 ELSE 0 END) AS total_error,
                  SUM(CASE WHEN estado = N'skip' THEN 1 ELSE 0 END) AS total_skip
                FROM {qschema_p}.{qtabla_p}
                WHERE corrida_id = :cid
                """
            ),
            {"cid": int(corrida_id)},
        ).mappings().first()
        conn.execute(
            text(
                f"UPDATE {qschema_c}.{qtabla_c} SET "
                "fin = GETDATE(), estado = :est, mensaje = :msg, "
                "total_pasos = :tp, total_ok = :tok, total_cache = :tc, "
                "total_warn = :tw, total_error = :te, total_skip = :ts "
                "WHERE id = :cid"
            ),
            {
                "cid": int(corrida_id),
                "est": str(estado or "done")[:30],
                "msg": (mensaje or "")[:1000] or None,
                "tp": int(counts["total_pasos"] or 0),
                "tok": int(counts["total_ok"] or 0),
                "tc": int(counts["total_cache"] or 0),
                "tw": int(counts["total_warn"] or 0),
                "te": int(counts["total_error"] or 0),
                "ts": int(counts["total_skip"] or 0),
            },
        )
    return obtener_corrida(int(corrida_id)) or {}


def obtener_corrida(corrida_id: int) -> dict[str, Any] | None:
    asegurar_tablas()
    qschema, qtabla, _full, _df = _ids_corrida()
    with engine().connect() as conn:
        row = conn.execute(
            text(f"SELECT TOP 1 * FROM {qschema}.{qtabla} WHERE id = :id"),
            {"id": int(corrida_id)},
        ).mappings().first()
    return {k: _jsonable(v) for k, v in dict(row).items()} if row else None


def listar_corridas(*, limite: int = 20) -> list[dict[str, Any]]:
    asegurar_tablas()
    qschema, qtabla, _full, _df = _ids_corrida()
    with engine().connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT TOP (:lim) * FROM {qschema}.{qtabla} "
                "ORDER BY id DESC"
            ),
            {"lim": int(limite)},
        ).mappings().all()
    return [{k: _jsonable(v) for k, v in dict(r).items()} for r in rows]


def listar_pasos(corrida_id: int) -> list[dict[str, Any]]:
    asegurar_tablas()
    qschema, qtabla, _full, _df = _ids_paso()
    with engine().connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT * FROM {qschema}.{qtabla} "
                "WHERE corrida_id = :cid ORDER BY orden, id"
            ),
            {"cid": int(corrida_id)},
        ).mappings().all()
    return [{k: _jsonable(v) for k, v in dict(r).items()} for r in rows]


def ultima_corrida_completa() -> dict[str, Any] | None:
    """Última corrida finalizada + pasos (para UI Fuentes)."""
    corridas = listar_corridas(limite=5)
    for c in corridas:
        if str(c.get("estado") or "") in ("done", "done_parcial", "error"):
            c = dict(c)
            c["pasos"] = listar_pasos(int(c["id"]))
            return c
    if corridas:
        c = dict(corridas[0])
        c["pasos"] = listar_pasos(int(c["id"]))
        return c
    return None


def estados_por_fuente_desde_cron() -> dict[str, dict[str, Any]]:
    """Último paso cron por fuente_id (para complementar la cola de jobs)."""
    asegurar_tablas()
    qschema, qtabla, _full, _df = _ids_paso()
    with engine().connect() as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT p.*
                FROM {qschema}.{qtabla} p
                INNER JOIN (
                    SELECT fuente_id, MAX(id) AS max_id
                    FROM {qschema}.{qtabla}
                    GROUP BY fuente_id
                ) u ON u.max_id = p.id
                """
            )
        ).mappings().all()
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        d = {k: _jsonable(v) for k, v in dict(r).items()}
        fid = str(d.get("fuente_id") or "")
        if not fid:
            continue
        out[fid] = d
    return out
