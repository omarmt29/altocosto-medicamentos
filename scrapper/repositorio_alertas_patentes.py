"""Historial de alertas de patentes (FDA ahora; EMA cuando haya fuente)."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import text

from db import engine, resumen_config

TABLA = "medicamentos_alertas_patentes"

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
        patent_no NVARCHAR(80) NOT NULL,
        clave_producto NVARCHAR(80) NULL,
        estado_anterior NVARCHAR(40) NULL,
        estado_nuevo NVARCHAR(40) NULL,
        expiration_date DATE NULL,
        dias_restantes INT NULL,
        dias_actualizado_en DATE NULL,
        detalle_json NVARCHAR(MAX) NULL,
        leida BIT NOT NULL CONSTRAINT DF_{df}_leida DEFAULT 0,
        fecha_registro DATETIME NOT NULL CONSTRAINT DF_{df}_reg DEFAULT GETDATE(),
        CONSTRAINT UQ_{df} UNIQUE (fecha_alerta, fuente, tipo_alerta, n_lista, patent_no, clave_producto)
    );
    CREATE INDEX IX_{df}_fecha ON {qschema}.{qtabla} (fecha_alerta DESC, leida);
    CREATE INDEX IX_{df}_fuente ON {qschema}.{qtabla} (fuente, tipo_alerta);
    CREATE INDEX IX_{df}_dias ON {qschema}.{qtabla} (dias_restantes, dias_actualizado_en);
END
"""

ALTERS = (
    "IF COL_LENGTH(N'{full}', 'dias_restantes') IS NULL "
    "ALTER TABLE {qschema}.{qtabla} ADD dias_restantes INT NULL;",
    "IF COL_LENGTH(N'{full}', 'dias_actualizado_en') IS NULL "
    "ALTER TABLE {qschema}.{qtabla} ADD dias_actualizado_en DATE NULL;",
)


def _ids() -> tuple[str, str, str, str]:
    schema = resumen_config()["schema"]
    return f"[{schema}]", f"[{TABLA}]", f"{schema}.{TABLA}", "mac_ap"


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
        for stmt in ALTERS:
            conn.execute(
                text(
                    stmt.replace("{qschema}", qschema)
                    .replace("{qtabla}", qtabla)
                    .replace("{full}", full)
                )
            )
    return full


def _dias_hasta(exp: date | None, hoy: date | None = None) -> int | None:
    if exp is None:
        return None
    ref = hoy or date.today()
    return (exp - ref).days


def actualizar_dias_restantes(*, hoy: date | None = None) -> dict[str, Any]:
    """Recalcula dias_restantes de todas las alertas con expiration_date (uso diario vía cron)."""
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    ref = hoy or date.today()
    sql = f"""
    UPDATE {qschema}.{qtabla}
    SET
        dias_restantes = DATEDIFF(DAY, :hoy, expiration_date),
        dias_actualizado_en = :hoy
    WHERE expiration_date IS NOT NULL
    """
    with engine().begin() as conn:
        res = conn.execute(text(sql), {"hoy": ref})
        n = int(res.rowcount or 0)
    return {
        "ok": True,
        "actualizadas": n,
        "fecha": ref.isoformat(),
        "mensaje": f"Conteo de días actualizado en {n} alerta(s) ({ref.isoformat()}).",
    }


def _jsonable(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat(timespec="seconds")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, (bytes, bytearray)):
        return bool(int.from_bytes(v, "little") if len(v) else 0)
    return v


def registrar_alerta(fila: dict[str, Any]) -> bool:
    """Inserta si no existe el mismo evento el mismo día. True si insertó."""
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    payload = dict(fila)
    detalle = payload.get("detalle_json")
    if detalle is not None and not isinstance(detalle, str):
        payload["detalle_json"] = json.dumps(detalle, ensure_ascii=False)
    fd = payload.get("fecha_alerta")
    if isinstance(fd, datetime):
        payload["fecha_alerta"] = fd.date()
    elif isinstance(fd, str):
        payload["fecha_alerta"] = date.fromisoformat(fd[:10])
    exp = payload.get("expiration_date")
    if isinstance(exp, datetime):
        payload["expiration_date"] = exp.date()
    elif isinstance(exp, str) and exp.strip():
        payload["expiration_date"] = date.fromisoformat(exp[:10])
    elif exp == "":
        payload["expiration_date"] = None
    payload["clave_producto"] = str(payload.get("clave_producto") or "").strip() or ""
    payload["patent_no"] = str(payload.get("patent_no") or "").strip()
    payload["leida"] = 1 if payload.get("leida") else 0
    hoy_alerta = payload.get("fecha_alerta")
    if not isinstance(hoy_alerta, date):
        hoy_alerta = date.today()
    if payload.get("dias_restantes") is None:
        payload["dias_restantes"] = _dias_hasta(payload.get("expiration_date"), hoy_alerta)
    payload["dias_actualizado_en"] = hoy_alerta if isinstance(hoy_alerta, date) else date.today()

    sql_exists = f"""
    SELECT TOP 1 1 AS x
    FROM {qschema}.{qtabla}
    WHERE fecha_alerta = :fecha_alerta
      AND fuente = :fuente
      AND tipo_alerta = :tipo_alerta
      AND n_lista = :n_lista
      AND patent_no = :patent_no
      AND ISNULL(clave_producto, N'') = :clave_producto
    """
    sql_ins = f"""
    INSERT INTO {qschema}.{qtabla} (
        fecha_alerta, fuente, tipo_alerta, n_lista, medicamento_lista,
        patent_no, clave_producto, estado_anterior, estado_nuevo,
        expiration_date, dias_restantes, dias_actualizado_en,
        detalle_json, leida, fecha_registro
    ) VALUES (
        :fecha_alerta, :fuente, :tipo_alerta, :n_lista, :medicamento_lista,
        :patent_no, :clave_producto, :estado_anterior, :estado_nuevo,
        :expiration_date, :dias_restantes, :dias_actualizado_en,
        :detalle_json, :leida, GETDATE()
    )
    """
    with engine().begin() as conn:
        existe = conn.execute(text(sql_exists), payload).first()
        if existe:
            return False
        conn.execute(text(sql_ins), payload)
    return True



def listar_alertas(
    *,
    fuente: str | None = None,
    tipo: str | None = None,
    solo_no_leidas: bool = False,
    desde: str | date | None = None,
    hasta: str | date | None = None,
    limite: int = 200,
    refrescar_dias: bool = True,
) -> list[dict[str, Any]]:
    asegurar_tabla()
    if refrescar_dias:
        # Si el cron aún no corrió hoy, igual dejamos dias_restantes al día al servir.
        _asegurar_dias_hoy()
    qschema, qtabla, _full, _df = _ids()
    where = ["1=1"]
    params: dict[str, Any] = {"lim": max(1, min(int(limite), 1000))}
    if fuente:
        where.append("fuente = :fuente")
        params["fuente"] = fuente.strip().lower()
    if tipo:
        where.append("tipo_alerta = :tipo")
        params["tipo"] = tipo.strip()
    if solo_no_leidas:
        where.append("leida = 0")
    if desde:
        where.append("fecha_alerta >= :desde")
        params["desde"] = desde if isinstance(desde, date) else date.fromisoformat(str(desde)[:10])
    if hasta:
        where.append("fecha_alerta <= :hasta")
        params["hasta"] = hasta if isinstance(hasta, date) else date.fromisoformat(str(hasta)[:10])

    sql = (
        f"SELECT TOP (:lim) * FROM {qschema}.{qtabla} "
        f"WHERE {' AND '.join(where)} "
        f"ORDER BY fecha_alerta DESC, id DESC"
    )
    with engine().connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    out = []
    for row in rows:
        item = {k: _jsonable(v) for k, v in dict(row).items()}
        raw = item.get("detalle_json")
        if isinstance(raw, str) and raw.strip():
            try:
                item["detalle"] = json.loads(raw)
            except json.JSONDecodeError:
                item["detalle"] = {}
        else:
            item["detalle"] = {}
        out.append(item)
    return out


def _asegurar_dias_hoy(*, hoy: date | None = None) -> None:
    """Actualiza dias_restantes solo si aún no se hizo para la fecha de hoy."""
    ref = hoy or date.today()
    qschema, qtabla, _full, _df = _ids()
    sql = f"""
    SELECT TOP 1 1 AS x
    FROM {qschema}.{qtabla}
    WHERE expiration_date IS NOT NULL
      AND (dias_actualizado_en IS NULL OR dias_actualizado_en < :hoy)
    """
    with engine().connect() as conn:
        stale = conn.execute(text(sql), {"hoy": ref}).first()
    if stale:
        actualizar_dias_restantes(hoy=ref)


def resumen_alertas() -> dict[str, Any]:
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    sql = f"""
    SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN leida = 0 THEN 1 ELSE 0 END) AS no_leidas,
        SUM(CASE WHEN fuente = N'fda' THEN 1 ELSE 0 END) AS fda,
        SUM(CASE WHEN fuente = N'ema' THEN 1 ELSE 0 END) AS ema,
        SUM(CASE WHEN tipo_alerta = N'paso_a_expirada' THEN 1 ELSE 0 END) AS paso_a_expirada,
        SUM(CASE WHEN tipo_alerta = N'vence_hoy' THEN 1 ELSE 0 END) AS vence_hoy,
        SUM(CASE WHEN tipo_alerta LIKE N'vence_en_%' THEN 1 ELSE 0 END) AS vence_pronto
    FROM {qschema}.{qtabla}
    """
    with engine().connect() as conn:
        row = conn.execute(text(sql)).mappings().first() or {}
    return {k: int(v or 0) for k, v in dict(row).items()}


def marcar_leida(alerta_id: int, leida: bool = True) -> bool:
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    sql = f"UPDATE {qschema}.{qtabla} SET leida = :leida WHERE id = :id"
    with engine().begin() as conn:
        res = conn.execute(text(sql), {"id": int(alerta_id), "leida": 1 if leida else 0})
    return (res.rowcount or 0) > 0


def marcar_todas_leidas(*, fuente: str | None = None) -> int:
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    if fuente:
        sql = f"UPDATE {qschema}.{qtabla} SET leida = 1 WHERE leida = 0 AND fuente = :fuente"
        params = {"fuente": fuente.strip().lower()}
    else:
        sql = f"UPDATE {qschema}.{qtabla} SET leida = 1 WHERE leida = 0"
        params = {}
    with engine().begin() as conn:
        res = conn.execute(text(sql), params)
    return int(res.rowcount or 0)


def marcar_no_leidas_por_criterios(config_ids: list[int]) -> int:
    """Vuelve a marcar como no leídas las alertas de esos criterios (para el badge UI)."""
    ids = []
    for x in config_ids or []:
        try:
            ids.append(int(x))
        except (TypeError, ValueError):
            continue
    ids = sorted(set(i for i in ids if i > 0))
    if not ids:
        return 0
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    placeholders = ", ".join(f":t{i}" for i in range(len(ids)))
    params = {f"t{i}": f"criterio_{cid}" for i, cid in enumerate(ids)}
    sql = f"""
    UPDATE {qschema}.{qtabla}
    SET leida = 0
    WHERE tipo_alerta IN ({placeholders})
      AND leida = 1
      AND (
        expiration_date IS NULL
        OR CAST(expiration_date AS DATE) >= CAST(GETDATE() AS DATE)
      )
    """
    with engine().begin() as conn:
        res = conn.execute(text(sql), params)
    return int(res.rowcount or 0)


def existe_alerta(
    *,
    fuente: str,
    tipo_alerta: str,
    n_lista: int,
    patent_no: str,
    clave_producto: str = "",
) -> bool:
    """True si ya existe cualquier alerta con esa clave (útil para horizontes)."""
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    sql = f"""
    SELECT TOP 1 1 AS x
    FROM {qschema}.{qtabla}
    WHERE fuente = :fuente
      AND tipo_alerta = :tipo_alerta
      AND n_lista = :n_lista
      AND patent_no = :patent_no
      AND ISNULL(clave_producto, N'') = :clave_producto
    """
    with engine().connect() as conn:
        row = conn.execute(
            text(sql),
            {
                "fuente": fuente.strip().lower(),
                "tipo_alerta": tipo_alerta,
                "n_lista": int(n_lista),
                "patent_no": str(patent_no or "").strip(),
                "clave_producto": str(clave_producto or "").strip(),
            },
        ).first()
    return row is not None


def existe_alerta_patente(
    *,
    fuente: str,
    n_lista: int,
    patent_no: str,
    clave_producto: str = "",
) -> bool:
    """True si ya hubo alguna alerta (cualquier tipo) para esa patente/producto."""
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    sql = f"""
    SELECT TOP 1 1 AS x
    FROM {qschema}.{qtabla}
    WHERE fuente = :fuente
      AND n_lista = :n_lista
      AND patent_no = :patent_no
      AND ISNULL(clave_producto, N'') = :clave_producto
    """
    with engine().connect() as conn:
        row = conn.execute(
            text(sql),
            {
                "fuente": fuente.strip().lower(),
                "n_lista": int(n_lista),
                "patent_no": str(patent_no or "").strip(),
                "clave_producto": str(clave_producto or "").strip(),
            },
        ).first()
    return row is not None



# ── Criterios configurables (modal de alertas de patentes) ──────────────────

TABLA_CONFIG = "medicamentos_alertas_patentes_config"

DDL_CONFIG = """
IF NOT EXISTS (
    SELECT 1
    FROM sys.tables t
    INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE t.name = N'{tabla}' AND s.name = N'{schema}'
)
BEGIN
    CREATE TABLE {qschema}.{qtabla} (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        nombre NVARCHAR(200) NULL,
        activo BIT NOT NULL CONSTRAINT DF_{df}_act DEFAULT 1,
        dias_min INT NULL,
        dias_max INT NOT NULL,
        avisar_vence_hoy BIT NOT NULL CONSTRAINT DF_{df}_vh DEFAULT 1,
        avisar_paso_expirada BIT NOT NULL CONSTRAINT DF_{df}_pe DEFAULT 1,
        avisar_diario BIT NOT NULL CONSTRAINT DF_{df}_ad DEFAULT 1,
        intervalo_horas INT NOT NULL CONSTRAINT DF_{df}_ih DEFAULT 24,
        intervalo_minutos INT NOT NULL CONSTRAINT DF_{df}_im DEFAULT 1440,
        intervalo_unidad NVARCHAR(10) NOT NULL CONSTRAINT DF_{df}_iu DEFAULT N'horas',
        ultima_notificacion_en DATETIME NULL,
        fuente NVARCHAR(20) NULL,
        n_lista INT NULL,
        medicamento_lista NVARCHAR(300) NULL,
        fecha_creacion DATETIME NOT NULL CONSTRAINT DF_{df}_c DEFAULT GETDATE(),
        fecha_actualizacion DATETIME NOT NULL CONSTRAINT DF_{df}_u DEFAULT GETDATE()
    );
    CREATE INDEX IX_{df}_act ON {qschema}.{qtabla} (activo, dias_max);
END
"""


def _ids_config() -> tuple[str, str, str, str]:
    schema = resumen_config()["schema"]
    return f"[{schema}]", f"[{TABLA_CONFIG}]", f"{schema}.{TABLA_CONFIG}", "mac_apc2"


def asegurar_tabla_config() -> str:
    asegurar_tabla()
    qschema, qtabla, full, df = _ids_config()
    schema = resumen_config()["schema"]
    sql = (
        DDL_CONFIG.replace("{qschema}", qschema)
        .replace("{qtabla}", qtabla)
        .replace("{schema}", schema)
        .replace("{tabla}", TABLA_CONFIG)
        .replace("{df}", df)
    )
    alters = [
        f"""
        IF COL_LENGTH(N'{full}', 'intervalo_horas') IS NULL
        ALTER TABLE {qschema}.{qtabla} ADD intervalo_horas INT NOT NULL
            CONSTRAINT DF_{df}_ih DEFAULT 24;
        """,
        f"""
        IF COL_LENGTH(N'{full}', 'intervalo_minutos') IS NULL
        ALTER TABLE {qschema}.{qtabla} ADD intervalo_minutos INT NULL;
        """,
        f"""
        IF COL_LENGTH(N'{full}', 'intervalo_unidad') IS NULL
        ALTER TABLE {qschema}.{qtabla} ADD intervalo_unidad NVARCHAR(10) NULL;
        """,
        f"""
        UPDATE {qschema}.{qtabla}
        SET intervalo_minutos = CASE
                WHEN intervalo_minutos IS NULL OR intervalo_minutos < 1
                THEN ISNULL(NULLIF(intervalo_horas, 0), 24) * 60
                ELSE intervalo_minutos
            END,
            intervalo_unidad = CASE
                WHEN LOWER(LTRIM(RTRIM(ISNULL(intervalo_unidad, N'')))) IN (N'minutos', N'min', N'm')
                THEN N'minutos'
                ELSE N'horas'
            END
        WHERE intervalo_minutos IS NULL
           OR intervalo_unidad IS NULL
           OR intervalo_minutos < 1;
        """,
        f"""
        IF COL_LENGTH(N'{full}', 'intervalo_minutos') IS NOT NULL
           AND EXISTS (
             SELECT 1 FROM sys.columns
             WHERE object_id = OBJECT_ID(N'{full}')
               AND name = N'intervalo_minutos'
               AND is_nullable = 1
           )
        BEGIN
          ALTER TABLE {qschema}.{qtabla} ALTER COLUMN intervalo_minutos INT NOT NULL;
        END
        """,
        f"""
        IF COL_LENGTH(N'{full}', 'intervalo_unidad') IS NOT NULL
           AND EXISTS (
             SELECT 1 FROM sys.columns
             WHERE object_id = OBJECT_ID(N'{full}')
               AND name = N'intervalo_unidad'
               AND is_nullable = 1
           )
        BEGIN
          ALTER TABLE {qschema}.{qtabla} ALTER COLUMN intervalo_unidad NVARCHAR(10) NOT NULL;
        END
        """,
        f"""
        IF COL_LENGTH(N'{full}', 'ultima_notificacion_en') IS NULL
        ALTER TABLE {qschema}.{qtabla} ADD ultima_notificacion_en DATETIME NULL;
        """,
    ]
    with engine().begin() as conn:
        conn.execute(text(sql))
        for stmt in alters:
            conn.execute(text(stmt))
    return full


def _as_bit(v: Any, default: bool = True) -> int:
    if v is None:
        return 1 if default else 0
    if isinstance(v, (bytes, bytearray)):
        return 1 if int.from_bytes(v, "little") else 0
    return 1 if bool(v) else 0


def listar_configs(*, solo_activas: bool = False) -> list[dict[str, Any]]:
    asegurar_tabla_config()
    qschema, qtabla, _full, _df = _ids_config()
    where = "WHERE activo = 1" if solo_activas else ""
    sql = (
        f"SELECT * FROM {qschema}.{qtabla} {where} "
        f"ORDER BY activo DESC, dias_max ASC, id DESC"
    )
    with engine().connect() as conn:
        rows = conn.execute(text(sql)).mappings().all()
    return [{k: _jsonable(v) for k, v in dict(r).items()} for r in rows]


def obtener_config(config_id: int) -> dict[str, Any] | None:
    asegurar_tabla_config()
    qschema, qtabla, _full, _df = _ids_config()
    with engine().connect() as conn:
        row = conn.execute(
            text(f"SELECT TOP 1 * FROM {qschema}.{qtabla} WHERE id = :id"),
            {"id": int(config_id)},
        ).mappings().first()
    return {k: _jsonable(v) for k, v in dict(row).items()} if row else None


def guardar_config(fila: dict[str, Any]) -> dict[str, Any]:
    """Crea/actualiza un criterio. Requiere dias_max > 0 (ventana de vencimiento)."""
    asegurar_tabla_config()
    qschema, qtabla, _full, _df = _ids_config()
    try:
        dias_max = int(fila.get("dias_max"))
    except (TypeError, ValueError):
        raise ValueError("Indicá hasta cuántos días antes del vencimiento avisar.") from None
    if dias_max < 1:
        raise ValueError("El máximo de días debe ser al menos 1.")
    dias_min = fila.get("dias_min")
    if dias_min is None or dias_min == "":
        dias_min_n = 0
    else:
        try:
            dias_min_n = int(dias_min)
        except (TypeError, ValueError):
            raise ValueError("El mínimo de días no es válido.") from None
    if dias_min_n < 0:
        dias_min_n = 0
    if dias_min_n > dias_max:
        raise ValueError("El mínimo de días no puede ser mayor que el máximo.")

    n_lista = fila.get("n_lista")
    if n_lista in ("", None):
        n_lista_n = None
    else:
        try:
            n_lista_n = int(n_lista)
        except (TypeError, ValueError):
            raise ValueError("Medicamento inválido.") from None

    fuente = str(fila.get("fuente") or "").strip().lower() or "fda"
    if fuente not in ("fda", "ema"):
        raise ValueError("Fuente debe ser FDA o EMA.")

    raw_unidad = str(fila.get("intervalo_unidad") or "").strip().lower()
    if raw_unidad in ("minutos", "min", "m", "minute", "minutes"):
        intervalo_unidad = "minutos"
    else:
        intervalo_unidad = "horas"

    # Preferimos minutos canónicos; aceptamos valor+unidad o legado intervalo_horas.
    raw_mins = fila.get("intervalo_minutos")
    raw_valor = fila.get("intervalo_valor")
    raw_horas = fila.get("intervalo_horas")
    try:
        if raw_mins not in ("", None):
            intervalo_minutos = int(raw_mins)
        elif raw_valor not in ("", None):
            valor = int(raw_valor)
            intervalo_minutos = valor if intervalo_unidad == "minutos" else valor * 60
        elif raw_horas not in ("", None):
            valor = int(raw_horas)
            intervalo_minutos = valor if intervalo_unidad == "minutos" else valor * 60
        else:
            intervalo_minutos = 1440
    except (TypeError, ValueError):
        raise ValueError("El intervalo de notificación no es válido.") from None
    if intervalo_minutos < 1:
        intervalo_minutos = 1
    if intervalo_minutos > 43200:  # 30 días
        intervalo_minutos = 43200
    intervalo_horas = max(1, (intervalo_minutos + 59) // 60)

    payload = {
        "nombre": (str(fila.get("nombre") or "").strip() or None),
        "activo": _as_bit(fila.get("activo", True)),
        "dias_min": dias_min_n,
        "dias_max": dias_max,
        "avisar_vence_hoy": _as_bit(fila.get("avisar_vence_hoy", True)),
        "avisar_paso_expirada": _as_bit(fila.get("avisar_paso_expirada", True)),
        "avisar_diario": _as_bit(fila.get("avisar_diario", True)),
        "intervalo_horas": intervalo_horas,
        "intervalo_minutos": intervalo_minutos,
        "intervalo_unidad": intervalo_unidad,
        "fuente": fuente,
        "n_lista": n_lista_n,
        "medicamento_lista": (str(fila.get("medicamento_lista") or "").strip() or None),
    }

    cid = fila.get("id")
    with engine().begin() as conn:
        if cid:
            conn.execute(
                text(
                    f"""
                    UPDATE {qschema}.{qtabla} SET
                        nombre = :nombre,
                        activo = :activo,
                        dias_min = :dias_min,
                        dias_max = :dias_max,
                        avisar_vence_hoy = :avisar_vence_hoy,
                        avisar_paso_expirada = :avisar_paso_expirada,
                        avisar_diario = :avisar_diario,
                        intervalo_horas = :intervalo_horas,
                        intervalo_minutos = :intervalo_minutos,
                        intervalo_unidad = :intervalo_unidad,
                        fuente = :fuente,
                        n_lista = :n_lista,
                        medicamento_lista = :medicamento_lista,
                        fecha_actualizacion = GETDATE()
                    WHERE id = :id
                    """
                ),
                {**payload, "id": int(cid)},
            )
            out_id = int(cid)
        else:
            row = conn.execute(
                text(
                    f"""
                    INSERT INTO {qschema}.{qtabla} (
                        nombre, activo, dias_min, dias_max,
                        avisar_vence_hoy, avisar_paso_expirada, avisar_diario,
                        intervalo_horas, intervalo_minutos, intervalo_unidad,
                        fuente, n_lista, medicamento_lista
                    )
                    OUTPUT INSERTED.id
                    VALUES (
                        :nombre, :activo, :dias_min, :dias_max,
                        :avisar_vence_hoy, :avisar_paso_expirada, :avisar_diario,
                        :intervalo_horas, :intervalo_minutos, :intervalo_unidad,
                        :fuente, :n_lista, :medicamento_lista
                    )
                    """
                ),
                payload,
            ).first()
            out_id = int(row[0])
    got = obtener_config(out_id)
    if not got:
        raise RuntimeError("No se pudo leer el criterio guardado.")
    return got


def marcar_notificacion_configs(config_ids: list[int]) -> int:
    """Registra en BD el momento de la última notificación UI (sobrevive recargas)."""
    ids = []
    for x in config_ids or []:
        try:
            ids.append(int(x))
        except (TypeError, ValueError):
            continue
    if not ids:
        return 0
    asegurar_tabla_config()
    qschema, qtabla, _full, _df = _ids_config()
    # SQL Server: actualizar varios ids
    placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
    params = {f"id{i}": cid for i, cid in enumerate(ids)}
    sql = f"""
    UPDATE {qschema}.{qtabla}
    SET ultima_notificacion_en = GETDATE(),
        fecha_actualizacion = GETDATE()
    WHERE id IN ({placeholders})
    """
    with engine().begin() as conn:
        res = conn.execute(text(sql), params)
    return int(res.rowcount or 0)


def eliminar_config(config_id: int) -> bool:
    asegurar_tabla_config()
    qschema, qtabla, _full, _df = _ids_config()
    with engine().begin() as conn:
        res = conn.execute(
            text(f"DELETE FROM {qschema}.{qtabla} WHERE id = :id"),
            {"id": int(config_id)},
        )
    return (res.rowcount or 0) > 0


def set_config_activa(config_id: int, activo: bool) -> bool:
    asegurar_tabla_config()
    qschema, qtabla, _full, _df = _ids_config()
    with engine().begin() as conn:
        res = conn.execute(
            text(
                f"UPDATE {qschema}.{qtabla} SET activo = :a, fecha_actualizacion = GETDATE() "
                f"WHERE id = :id"
            ),
            {"id": int(config_id), "a": 1 if activo else 0},
        )
    return (res.rowcount or 0) > 0


def opciones_criterios_patentes() -> dict[str, Any]:
    """Medicamentos con alertas/patentes conocidas para el selector del modal."""
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    with engine().connect() as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT n_lista, MAX(medicamento_lista) AS medicamento_lista, COUNT(*) AS alertas
                FROM {qschema}.{qtabla}
                GROUP BY n_lista
                ORDER BY MAX(medicamento_lista)
                """
            )
        ).mappings().all()
    meds = [
        {
            "n_lista": int(r["n_lista"]),
            "medicamento_lista": r.get("medicamento_lista") or f"#{r['n_lista']}",
            "alertas": int(r.get("alertas") or 0),
        }
        for r in rows
        if r.get("n_lista") is not None
    ]
    return {
        "medicamentos": meds,
        "fuentes": [
            {"id": "fda", "label": "FDA"},
            {"id": "ema", "label": "EMA"},
        ],
        "presets_dias": [7, 15, 30, 60, 90, 180, 365],
    }


def horizonte_max_configs() -> int | None:
    """Máximo dias_max entre criterios activos (para UI / badge)."""
    configs = listar_configs(solo_activas=True)
    if not configs:
        return None
    return max(int(c.get("dias_max") or 0) for c in configs)
