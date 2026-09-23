"""Configuración y registros de alertas por variación de precio."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from db import engine, resumen_config
from scrapper.repositorio_historial import TABLA as TABLA_HIST

TABLA_CONFIG = "medicamentos_alertas_precios_config"
TABLA_ALERTAS = "medicamentos_alertas_precios"

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
        n_lista INT NULL,
        medicamento_lista NVARCHAR(300) NULL,
        producto_key NVARCHAR(500) NULL,
        nombre_comercial NVARCHAR(500) NULL,
        pais NVARCHAR(80) NULL,
        farmacia NVARCHAR(80) NULL,
        presentacion NVARCHAR(120) NULL,
        concentracion NVARCHAR(300) NULL,
        umbral_baja_pct DECIMAL(9, 2) NULL,
        umbral_sube_pct DECIMAL(9, 2) NULL,
        fecha_creacion DATETIME NOT NULL CONSTRAINT DF_{df}_c DEFAULT GETDATE(),
        fecha_actualizacion DATETIME NOT NULL CONSTRAINT DF_{df}_u DEFAULT GETDATE()
    );
    CREATE INDEX IX_{df}_act ON {qschema}.{qtabla} (activo, n_lista);
END
"""

ALTERS_CONFIG = (
    "IF COL_LENGTH(N'{full}', 'producto_key') IS NULL "
    "ALTER TABLE {qschema}.{qtabla} ADD producto_key NVARCHAR(500) NULL;",
    "IF COL_LENGTH(N'{full}', 'nombre_comercial') IS NULL "
    "ALTER TABLE {qschema}.{qtabla} ADD nombre_comercial NVARCHAR(500) NULL;",
    "IF COL_LENGTH(N'{full}', 'intervalo_horas') IS NULL "
    "ALTER TABLE {qschema}.{qtabla} ADD intervalo_horas INT NOT NULL CONSTRAINT DF_mac_apc_ih DEFAULT 24;",
    "IF COL_LENGTH(N'{full}', 'intervalo_minutos') IS NULL "
    "ALTER TABLE {qschema}.{qtabla} ADD intervalo_minutos INT NULL;",
    "IF COL_LENGTH(N'{full}', 'intervalo_unidad') IS NULL "
    "ALTER TABLE {qschema}.{qtabla} ADD intervalo_unidad NVARCHAR(10) NULL;",
    "IF COL_LENGTH(N'{full}', 'ultima_notificacion_en') IS NULL "
    "ALTER TABLE {qschema}.{qtabla} ADD ultima_notificacion_en DATETIME NULL;",
    """
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
    # Criterios escalables: país/farmacia sin medicamento → n_lista opcional.
    """
    IF COL_LENGTH(N'{full}', 'n_lista') IS NOT NULL
       AND EXISTS (
            SELECT 1 FROM sys.columns
            WHERE object_id = OBJECT_ID(N'{full}')
              AND name = N'n_lista'
              AND is_nullable = 0
       )
    ALTER TABLE {qschema}.{qtabla} ALTER COLUMN n_lista INT NULL;
    """,
)

DDL_ALERTAS = """
IF NOT EXISTS (
    SELECT 1
    FROM sys.tables t
    INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE t.name = N'{tabla}' AND s.name = N'{schema}'
)
BEGIN
    CREATE TABLE {qschema}.{qtabla} (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        config_id INT NULL,
        fecha_alerta DATE NOT NULL,
        tipo_alerta NVARCHAR(20) NOT NULL,
        n_lista INT NOT NULL,
        medicamento_lista NVARCHAR(300) NULL,
        pais NVARCHAR(80) NULL,
        farmacia NVARCHAR(80) NULL,
        presentacion NVARCHAR(120) NULL,
        concentracion NVARCHAR(300) NULL,
        producto_key NVARCHAR(500) NULL,
        precio_anterior_usd DECIMAL(18, 6) NULL,
        precio_nuevo_usd DECIMAL(18, 6) NULL,
        variacion_pct DECIMAL(12, 4) NULL,
        umbral_pct DECIMAL(9, 2) NULL,
        fecha_dato_anterior DATE NULL,
        fecha_dato_nuevo DATE NULL,
        detalle_json NVARCHAR(MAX) NULL,
        leida BIT NOT NULL CONSTRAINT DF_{df}_leida DEFAULT 0,
        fecha_registro DATETIME NOT NULL CONSTRAINT DF_{df}_reg DEFAULT GETDATE(),
        CONSTRAINT UQ_{df} UNIQUE (
            fecha_alerta, config_id, tipo_alerta, n_lista,
            pais, farmacia, producto_key, fecha_dato_nuevo
        )
    );
    CREATE INDEX IX_{df}_fecha ON {qschema}.{qtabla} (fecha_alerta DESC, leida);
    CREATE INDEX IX_{df}_cfg ON {qschema}.{qtabla} (config_id, fecha_alerta DESC);
END
"""


def _schema() -> str:
    return resumen_config()["schema"]


def _q(tabla: str) -> tuple[str, str, str]:
    schema = _schema()
    return f"[{schema}]", f"[{tabla}]", f"{schema}.{tabla}"


def asegurar_tablas() -> dict[str, str]:
    schema = _schema()
    with engine().begin() as conn:
        for tabla, ddl, df, alters in (
            (TABLA_CONFIG, DDL_CONFIG, "mac_apc", ALTERS_CONFIG),
            (TABLA_ALERTAS, DDL_ALERTAS, "mac_apa", ()),
        ):
            qschema, qtabla, full = _q(tabla)
            sql = (
                ddl.replace("{qschema}", qschema)
                .replace("{qtabla}", qtabla)
                .replace("{schema}", schema)
                .replace("{tabla}", tabla)
                .replace("{df}", df)
            )
            conn.execute(text(sql))
            for stmt in alters:
                conn.execute(
                    text(
                        stmt.replace("{qschema}", qschema)
                        .replace("{qtabla}", qtabla)
                        .replace("{full}", full)
                    )
                )
    return {"config": f"{schema}.{TABLA_CONFIG}", "alertas": f"{schema}.{TABLA_ALERTAS}"}


def _jsonable(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat(timespec="seconds")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (bytes, bytearray)):
        return bool(int.from_bytes(v, "little") if len(v) else 0)
    return v


def _norm_opt(v: Any) -> str | None:
    s = str(v or "").strip()
    return s or None


def _num_pct(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return round(n, 2)


def listar_configs(*, solo_activas: bool = False) -> list[dict[str, Any]]:
    asegurar_tablas()
    qschema, qtabla, _ = _q(TABLA_CONFIG)
    where = "WHERE activo = 1" if solo_activas else ""
    sql = (
        f"SELECT * FROM {qschema}.{qtabla} {where} "
        f"ORDER BY activo DESC, fecha_actualizacion DESC, id DESC"
    )
    with engine().connect() as conn:
        rows = conn.execute(text(sql)).mappings().all()
    return [{k: _jsonable(v) for k, v in dict(r).items()} for r in rows]


def obtener_config(config_id: int) -> dict[str, Any] | None:
    asegurar_tablas()
    qschema, qtabla, _ = _q(TABLA_CONFIG)
    sql = f"SELECT TOP 1 * FROM {qschema}.{qtabla} WHERE id = :id"
    with engine().connect() as conn:
        row = conn.execute(text(sql), {"id": int(config_id)}).mappings().first()
    return {k: _jsonable(v) for k, v in dict(row).items()} if row else None


def guardar_config(fila: dict[str, Any]) -> dict[str, Any]:
    """Crea o actualiza un criterio. Campos vacíos = todos. Requiere al menos un umbral."""
    asegurar_tablas()
    qschema, qtabla, _ = _q(TABLA_CONFIG)
    n_raw = fila.get("n_lista")
    if n_raw in ("", None):
        n_lista = None
    else:
        try:
            n_lista = int(n_raw)
        except (TypeError, ValueError):
            raise ValueError("Medicamento / producto inválido.") from None
    baja = _num_pct(fila.get("umbral_baja_pct"))
    sube = _num_pct(fila.get("umbral_sube_pct"))
    if baja is None and sube is None:
        raise ValueError("Indicá al menos un umbral: baja % o sube %.")

    raw_unidad = str(fila.get("intervalo_unidad") or "").strip().lower()
    if raw_unidad in ("minutos", "min", "m", "minute", "minutes"):
        intervalo_unidad = "minutos"
    else:
        intervalo_unidad = "horas"
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
    if intervalo_minutos > 43200:
        intervalo_minutos = 43200
    intervalo_horas = max(1, (intervalo_minutos + 59) // 60)

    payload = {
        "nombre": _norm_opt(fila.get("nombre")),
        "activo": 1 if fila.get("activo", True) else 0,
        "n_lista": n_lista,
        "medicamento_lista": _norm_opt(fila.get("medicamento_lista")),
        "producto_key": _norm_opt(fila.get("producto_key")),
        "nombre_comercial": _norm_opt(fila.get("nombre_comercial")),
        "pais": _norm_opt(fila.get("pais")),
        "farmacia": _norm_opt(fila.get("farmacia")),
        "presentacion": _norm_opt(fila.get("presentacion")),
        "concentracion": _norm_opt(fila.get("concentracion")),
        "umbral_baja_pct": baja,
        "umbral_sube_pct": sube,
        "intervalo_horas": intervalo_horas,
        "intervalo_minutos": intervalo_minutos,
        "intervalo_unidad": intervalo_unidad,
    }
    cid = fila.get("id")
    with engine().begin() as conn:
        if cid:
            payload["id"] = int(cid)
            sql = f"""
            UPDATE {qschema}.{qtabla}
            SET nombre = :nombre,
                activo = :activo,
                n_lista = :n_lista,
                medicamento_lista = :medicamento_lista,
                producto_key = :producto_key,
                nombre_comercial = :nombre_comercial,
                pais = :pais,
                farmacia = :farmacia,
                presentacion = :presentacion,
                concentracion = :concentracion,
                umbral_baja_pct = :umbral_baja_pct,
                umbral_sube_pct = :umbral_sube_pct,
                intervalo_horas = :intervalo_horas,
                intervalo_minutos = :intervalo_minutos,
                intervalo_unidad = :intervalo_unidad,
                fecha_actualizacion = GETDATE()
            WHERE id = :id
            """
            res = conn.execute(text(sql), payload)
            if not (res.rowcount or 0):
                raise ValueError("No se encontró el criterio a actualizar.")
            out_id = int(cid)
        else:
            sql = f"""
            INSERT INTO {qschema}.{qtabla} (
                nombre, activo, n_lista, medicamento_lista, producto_key, nombre_comercial,
                pais, farmacia, presentacion, concentracion, umbral_baja_pct, umbral_sube_pct,
                intervalo_horas, intervalo_minutos, intervalo_unidad,
                fecha_creacion, fecha_actualizacion
            )
            OUTPUT INSERTED.id
            VALUES (
                :nombre, :activo, :n_lista, :medicamento_lista, :producto_key, :nombre_comercial,
                :pais, :farmacia, :presentacion, :concentracion, :umbral_baja_pct, :umbral_sube_pct,
                :intervalo_horas, :intervalo_minutos, :intervalo_unidad,
                GETDATE(), GETDATE()
            )
            """
            out_id = int(conn.execute(text(sql), payload).scalar())
    row = obtener_config(out_id)
    if not row:
        raise RuntimeError("No se pudo leer el criterio guardado.")
    return row


def set_config_activa(config_id: int, activo: bool) -> bool:
    asegurar_tablas()
    qschema, qtabla, _ = _q(TABLA_CONFIG)
    sql = f"""
    UPDATE {qschema}.{qtabla}
    SET activo = :activo, fecha_actualizacion = GETDATE()
    WHERE id = :id
    """
    with engine().begin() as conn:
        res = conn.execute(text(sql), {"id": int(config_id), "activo": 1 if activo else 0})
    return (res.rowcount or 0) > 0


def eliminar_config(config_id: int) -> bool:
    asegurar_tablas()
    qschema, qtabla, _ = _q(TABLA_CONFIG)
    sql = f"DELETE FROM {qschema}.{qtabla} WHERE id = :id"
    with engine().begin() as conn:
        res = conn.execute(text(sql), {"id": int(config_id)})
    return (res.rowcount or 0) > 0


def registrar_alerta(fila: dict[str, Any]) -> bool:
    """Inserta alerta si no existe la misma clave. True si insertó."""
    asegurar_tablas()
    qschema, qtabla, _ = _q(TABLA_ALERTAS)
    payload = dict(fila)
    detalle = payload.get("detalle_json")
    if detalle is not None and not isinstance(detalle, str):
        payload["detalle_json"] = json.dumps(detalle, ensure_ascii=False)
    elif "detalle_json" not in payload:
        payload["detalle_json"] = None
    fd = payload.get("fecha_alerta") or date.today()
    if isinstance(fd, datetime):
        fd = fd.date()
    elif isinstance(fd, str):
        fd = date.fromisoformat(fd[:10])
    payload["fecha_alerta"] = fd
    for key in ("fecha_dato_anterior", "fecha_dato_nuevo"):
        v = payload.get(key)
        if isinstance(v, datetime):
            payload[key] = v.date()
        elif isinstance(v, str) and v.strip():
            payload[key] = date.fromisoformat(v[:10])
        elif not v:
            payload[key] = None
    payload["config_id"] = int(payload["config_id"]) if payload.get("config_id") not in (None, "") else None
    payload["n_lista"] = int(payload["n_lista"])
    payload["pais"] = _norm_opt(payload.get("pais")) or ""
    payload["farmacia"] = _norm_opt(payload.get("farmacia")) or ""
    payload["producto_key"] = _norm_opt(payload.get("producto_key")) or ""
    payload["presentacion"] = _norm_opt(payload.get("presentacion"))
    payload["concentracion"] = _norm_opt(payload.get("concentracion"))
    payload["medicamento_lista"] = _norm_opt(payload.get("medicamento_lista"))
    payload["tipo_alerta"] = str(payload.get("tipo_alerta") or "").strip().lower()
    payload["leida"] = 1 if payload.get("leida") else 0
    if payload["tipo_alerta"] not in ("baja", "sube"):
        raise ValueError("tipo_alerta debe ser 'baja' o 'sube'.")

    sql_exists = f"""
    SELECT TOP 1 1 AS x
    FROM {qschema}.{qtabla}
    WHERE fecha_alerta = :fecha_alerta
      AND ISNULL(config_id, 0) = ISNULL(:config_id, 0)
      AND tipo_alerta = :tipo_alerta
      AND n_lista = :n_lista
      AND ISNULL(pais, N'') = :pais
      AND ISNULL(farmacia, N'') = :farmacia
      AND ISNULL(producto_key, N'') = :producto_key
      AND (
            (fecha_dato_nuevo IS NULL AND :fecha_dato_nuevo IS NULL)
            OR fecha_dato_nuevo = :fecha_dato_nuevo
          )
    """
    sql_ins = f"""
    INSERT INTO {qschema}.{qtabla} (
        config_id, fecha_alerta, tipo_alerta, n_lista, medicamento_lista,
        pais, farmacia, presentacion, concentracion, producto_key,
        precio_anterior_usd, precio_nuevo_usd, variacion_pct, umbral_pct,
        fecha_dato_anterior, fecha_dato_nuevo, detalle_json, leida, fecha_registro
    ) VALUES (
        :config_id, :fecha_alerta, :tipo_alerta, :n_lista, :medicamento_lista,
        :pais, :farmacia, :presentacion, :concentracion, :producto_key,
        :precio_anterior_usd, :precio_nuevo_usd, :variacion_pct, :umbral_pct,
        :fecha_dato_anterior, :fecha_dato_nuevo, :detalle_json, :leida, GETDATE()
    )
    """
    with engine().begin() as conn:
        if conn.execute(text(sql_exists), payload).first():
            return False
        conn.execute(text(sql_ins), payload)
    return True


def listar_alertas(
    *,
    config_id: int | None = None,
    tipo: str | None = None,
    solo_no_leidas: bool = False,
    limite: int = 200,
) -> list[dict[str, Any]]:
    asegurar_tablas()
    qschema, qtabla, _ = _q(TABLA_ALERTAS)
    where = ["1=1"]
    params: dict[str, Any] = {"lim": max(1, min(int(limite), 1000))}
    if config_id is not None:
        where.append("config_id = :config_id")
        params["config_id"] = int(config_id)
    if tipo:
        where.append("tipo_alerta = :tipo")
        params["tipo"] = tipo.strip().lower()
    if solo_no_leidas:
        where.append("leida = 0")
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


def marcar_leida(alerta_id: int, leida: bool = True) -> bool:
    asegurar_tablas()
    qschema, qtabla, _ = _q(TABLA_ALERTAS)
    sql = f"UPDATE {qschema}.{qtabla} SET leida = :leida WHERE id = :id"
    with engine().begin() as conn:
        res = conn.execute(text(sql), {"id": int(alerta_id), "leida": 1 if leida else 0})
    return (res.rowcount or 0) > 0


def marcar_todas_leidas() -> int:
    asegurar_tablas()
    qschema, qtabla, _ = _q(TABLA_ALERTAS)
    sql = f"UPDATE {qschema}.{qtabla} SET leida = 1 WHERE leida = 0"
    with engine().begin() as conn:
        res = conn.execute(text(sql))
    return int(res.rowcount or 0)


def marcar_no_leidas_por_configs(config_ids: list[int]) -> int:
    ids = []
    for x in config_ids or []:
        try:
            ids.append(int(x))
        except (TypeError, ValueError):
            continue
    ids = sorted(set(i for i in ids if i > 0))
    if not ids:
        return 0
    asegurar_tablas()
    qschema, qtabla, _ = _q(TABLA_ALERTAS)
    placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
    params = {f"id{i}": cid for i, cid in enumerate(ids)}
    sql = f"""
    UPDATE {qschema}.{qtabla}
    SET leida = 0
    WHERE config_id IN ({placeholders}) AND leida = 1
    """
    with engine().begin() as conn:
        res = conn.execute(text(sql), params)
    return int(res.rowcount or 0)


def marcar_notificacion_configs(config_ids: list[int]) -> int:
    ids = []
    for x in config_ids or []:
        try:
            ids.append(int(x))
        except (TypeError, ValueError):
            continue
    ids = sorted(set(i for i in ids if i > 0))
    if not ids:
        return 0
    asegurar_tablas()
    qschema, qtabla, _ = _q(TABLA_CONFIG)
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


def resumen_alertas() -> dict[str, Any]:
    asegurar_tablas()
    qschema_a, qtabla_a, _ = _q(TABLA_ALERTAS)
    qschema_c, qtabla_c, _ = _q(TABLA_CONFIG)
    sql = f"""
    SELECT
        (SELECT COUNT(*) FROM {qschema_a}.{qtabla_a}) AS total,
        (SELECT SUM(CASE WHEN leida = 0 THEN 1 ELSE 0 END) FROM {qschema_a}.{qtabla_a}) AS no_leidas,
        (SELECT SUM(CASE WHEN tipo_alerta = N'baja' THEN 1 ELSE 0 END) FROM {qschema_a}.{qtabla_a}) AS bajas,
        (SELECT SUM(CASE WHEN tipo_alerta = N'sube' THEN 1 ELSE 0 END) FROM {qschema_a}.{qtabla_a}) AS subes,
        (SELECT COUNT(*) FROM {qschema_c}.{qtabla_c} WHERE activo = 1) AS configs_activas,
        (SELECT COUNT(*) FROM {qschema_c}.{qtabla_c}) AS configs_total
    """
    with engine().connect() as conn:
        row = conn.execute(text(sql)).mappings().first() or {}
    return {k: int(v or 0) for k, v in dict(row).items()}


def opciones_filtros(
    *,
    pais: str | None = None,
    farmacia: str | None = None,
    producto_key: str | None = None,
    n_lista: int | None = None,
    presentacion: str | None = None,
) -> dict[str, Any]:
    """Opciones en cascada desde el historial de precios (productos, no solo principios)."""
    asegurar_tablas()
    from scrapper.repositorio_historial import producto_label

    qschema, qtabla, _ = _q(TABLA_HIST)
    where = ["precio_usd IS NOT NULL", "precio_usd > 0"]
    params: dict[str, Any] = {}
    if pais:
        where.append("pais = :pais")
        params["pais"] = pais.strip()
    if farmacia:
        where.append("farmacia = :farmacia")
        params["farmacia"] = farmacia.strip()
    if producto_key:
        where.append("producto_key = :producto_key")
        params["producto_key"] = producto_key.strip()
    elif n_lista is not None:
        where.append("n_lista = :n_lista")
        params["n_lista"] = int(n_lista)
    if presentacion:
        where.append("presentacion = :presentacion")
        params["presentacion"] = presentacion.strip()
    wsql = " AND ".join(where)

    with engine().connect() as conn:
        paises = [
            r[0]
            for r in conn.execute(
                text(
                    f"SELECT DISTINCT pais FROM {qschema}.{qtabla} "
                    f"WHERE precio_usd IS NOT NULL AND precio_usd > 0 AND pais IS NOT NULL AND pais <> N'' "
                    f"ORDER BY pais"
                )
            ).fetchall()
            if r[0]
        ]
        farm_where = ["precio_usd IS NOT NULL", "precio_usd > 0", "farmacia IS NOT NULL", "farmacia <> N''"]
        farm_params: dict[str, Any] = {}
        if pais:
            farm_where.append("pais = :pais")
            farm_params["pais"] = pais.strip()
        farmacias = [
            r[0]
            for r in conn.execute(
                text(
                    f"SELECT DISTINCT farmacia FROM {qschema}.{qtabla} "
                    f"WHERE {' AND '.join(farm_where)} ORDER BY farmacia"
                ),
                farm_params,
            ).fetchall()
            if r[0]
        ]
        prod_where = ["precio_usd IS NOT NULL", "precio_usd > 0", "producto_key IS NOT NULL", "producto_key <> N''"]
        prod_params: dict[str, Any] = {}
        if pais:
            prod_where.append("pais = :pais")
            prod_params["pais"] = pais.strip()
        if farmacia:
            prod_where.append("farmacia = :farmacia")
            prod_params["farmacia"] = farmacia.strip()
        productos_raw = conn.execute(
            text(
                f"""
                SELECT
                    producto_key,
                    MAX(n_lista) AS n_lista,
                    MAX(medicamento_lista) AS medicamento_lista,
                    MAX(nombre_comercial) AS nombre_comercial,
                    MAX(concentracion) AS concentracion,
                    MAX(presentacion) AS presentacion
                FROM {qschema}.{qtabla}
                WHERE {' AND '.join(prod_where)}
                GROUP BY producto_key
                ORDER BY MAX(nombre_comercial), MAX(medicamento_lista), producto_key
                """
            ),
            prod_params,
        ).mappings().all()
        presentaciones: list[str] = []
        concentraciones: list[str] = []
        if producto_key or n_lista is not None:
            p_where = [
                "precio_usd IS NOT NULL",
                "precio_usd > 0",
                "presentacion IS NOT NULL",
                "presentacion <> N''",
            ]
            p_params: dict[str, Any] = {}
            if producto_key:
                p_where.append("producto_key = :producto_key")
                p_params["producto_key"] = producto_key.strip()
            else:
                p_where.append("n_lista = :n_lista")
                p_params["n_lista"] = int(n_lista)
            if pais:
                p_where.append("pais = :pais")
                p_params["pais"] = pais.strip()
            if farmacia:
                p_where.append("farmacia = :farmacia")
                p_params["farmacia"] = farmacia.strip()
            presentaciones = [
                r[0]
                for r in conn.execute(
                    text(
                        f"SELECT DISTINCT presentacion FROM {qschema}.{qtabla} "
                        f"WHERE {' AND '.join(p_where)} ORDER BY presentacion"
                    ),
                    p_params,
                ).fetchall()
                if r[0]
            ]
            c_where = [
                "precio_usd IS NOT NULL",
                "precio_usd > 0",
                "concentracion IS NOT NULL",
                "concentracion <> N''",
            ]
            c_params: dict[str, Any] = {}
            if producto_key:
                c_where.append("producto_key = :producto_key")
                c_params["producto_key"] = producto_key.strip()
            else:
                c_where.append("n_lista = :n_lista")
                c_params["n_lista"] = int(n_lista)
            if pais:
                c_where.append("pais = :pais")
                c_params["pais"] = pais.strip()
            if farmacia:
                c_where.append("farmacia = :farmacia")
                c_params["farmacia"] = farmacia.strip()
            if presentacion:
                c_where.append("presentacion = :presentacion")
                c_params["presentacion"] = presentacion.strip()
            concentraciones = [
                r[0]
                for r in conn.execute(
                    text(
                        f"SELECT DISTINCT concentracion FROM {qschema}.{qtabla} "
                        f"WHERE {' AND '.join(c_where)} ORDER BY concentracion"
                    ),
                    c_params,
                ).fetchall()
                if r[0]
            ]

    productos = []
    for m in productos_raw:
        item = {
            "producto_key": m.get("producto_key"),
            "n_lista": int(m["n_lista"]) if m.get("n_lista") is not None else None,
            "medicamento_lista": m.get("medicamento_lista"),
            "nombre_comercial": m.get("nombre_comercial"),
            "concentracion": m.get("concentracion"),
            "presentacion": m.get("presentacion"),
        }
        item["label"] = producto_label(item)
        productos.append(item)

    return {
        "paises": paises,
        "farmacias": farmacias,
        "productos": productos,
        # compat: UI antigua
        "medicamentos": productos,
        "presentaciones": presentaciones,
        "concentraciones": concentraciones,
    }
