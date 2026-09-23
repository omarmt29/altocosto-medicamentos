"""Tabla compartida P_aguila.medicamentos_altos_costos_america (upsert diario)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import text

from db import engine, resumen_config
from scrapper.estructura_producto import enriquecer_fila_estructurada
from scrapper.precios import normalizar_fila_precios

TABLA = "medicamentos_altos_costos_america"

DDL = """
IF OBJECT_ID(N'{qschema}.{qtabla}', 'U') IS NULL
BEGIN
    CREATE TABLE {qschema}.{qtabla} (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        pais NVARCHAR(80) NOT NULL,
        farmacia NVARCHAR(80) NOT NULL,
        fuente_url NVARCHAR(500) NULL,
        id_producto_farmacia NVARCHAR(80) NOT NULL,
        sku NVARCHAR(80) NULL,
        n_lista INT NOT NULL,
        medicamento_lista NVARCHAR(300) NOT NULL,
        programa NVARCHAR(40) NULL,
        nombre_comercial NVARCHAR(500) NULL,
        principio_activo NVARCHAR(500) NULL,
        concentracion NVARCHAR(300) NULL,
        cantidad_concentracion NVARCHAR(80) NULL,
        unidad_concentracion NVARCHAR(40) NULL,
        presentacion NVARCHAR(120) NULL,
        tipo_presentacion NVARCHAR(80) NULL,
        cantidad_presentacion NVARCHAR(80) NULL,
        alcance_presentacion NVARCHAR(20) NULL,
        laboratorio NVARCHAR(200) NULL,
        precio DECIMAL(18, 4) NULL,
        precio_lista DECIMAL(18, 4) NULL,
        precio_oferta DECIMAL(18, 4) NULL,
        moneda CHAR(3) NOT NULL,
        disponibilidad NVARCHAR(40) NULL,
        calidad NVARCHAR(20) NOT NULL,
        observacion NVARCHAR(400) NULL,
        fecha_publicacion DATETIME NULL,
        fecha_dato DATE NOT NULL,
        fecha_registro DATE NOT NULL CONSTRAINT DF_{df}_reg DEFAULT CONVERT(date, GETDATE()),
        fecha_actualizacion DATETIME NOT NULL CONSTRAINT DF_{df}_upd DEFAULT GETDATE(),
        CONSTRAINT UQ_{df} UNIQUE (pais, farmacia, id_producto_farmacia, n_lista)
    );
END
"""

ALTERS = [
    "IF COL_LENGTH(N'{full}', 'cantidad_concentracion') IS NULL ALTER TABLE {qschema}.{qtabla} ADD cantidad_concentracion NVARCHAR(80) NULL;",
    "IF COL_LENGTH(N'{full}', 'unidad_concentracion') IS NULL ALTER TABLE {qschema}.{qtabla} ADD unidad_concentracion NVARCHAR(40) NULL;",
    "IF COL_LENGTH(N'{full}', 'tipo_presentacion') IS NULL ALTER TABLE {qschema}.{qtabla} ADD tipo_presentacion NVARCHAR(80) NULL;",
    "IF COL_LENGTH(N'{full}', 'cantidad_presentacion') IS NULL ALTER TABLE {qschema}.{qtabla} ADD cantidad_presentacion NVARCHAR(80) NULL;",
    "IF COL_LENGTH(N'{full}', 'alcance_presentacion') IS NULL ALTER TABLE {qschema}.{qtabla} ADD alcance_presentacion NVARCHAR(20) NULL;",
    "IF COL_LENGTH(N'{full}', 'precio_lista') IS NULL ALTER TABLE {qschema}.{qtabla} ADD precio_lista DECIMAL(18, 4) NULL;",
    "IF COL_LENGTH(N'{full}', 'precio_oferta') IS NULL ALTER TABLE {qschema}.{qtabla} ADD precio_oferta DECIMAL(18, 4) NULL;",
]

MERGE_SQL = """
MERGE {qschema}.{qtabla} AS t
USING (SELECT
    :pais AS pais,
    :farmacia AS farmacia,
    :fuente_url AS fuente_url,
    :id_producto_farmacia AS id_producto_farmacia,
    :sku AS sku,
    :n_lista AS n_lista,
    :medicamento_lista AS medicamento_lista,
    :programa AS programa,
    :nombre_comercial AS nombre_comercial,
    :principio_activo AS principio_activo,
    :concentracion AS concentracion,
    :cantidad_concentracion AS cantidad_concentracion,
    :unidad_concentracion AS unidad_concentracion,
    :presentacion AS presentacion,
    :tipo_presentacion AS tipo_presentacion,
    :cantidad_presentacion AS cantidad_presentacion,
    :alcance_presentacion AS alcance_presentacion,
    :laboratorio AS laboratorio,
    :precio AS precio,
    :precio_lista AS precio_lista,
    :precio_oferta AS precio_oferta,
    :moneda AS moneda,
    :disponibilidad AS disponibilidad,
    :calidad AS calidad,
    :observacion AS observacion,
    :fecha_publicacion AS fecha_publicacion,
    :fecha_dato AS fecha_dato
) AS s
ON t.pais = s.pais
   AND t.farmacia = s.farmacia
   AND t.id_producto_farmacia = s.id_producto_farmacia
   AND t.n_lista = s.n_lista
WHEN MATCHED THEN UPDATE SET
    fuente_url = s.fuente_url,
    sku = s.sku,
    medicamento_lista = s.medicamento_lista,
    programa = s.programa,
    nombre_comercial = s.nombre_comercial,
    principio_activo = s.principio_activo,
    concentracion = s.concentracion,
    cantidad_concentracion = s.cantidad_concentracion,
    unidad_concentracion = s.unidad_concentracion,
    presentacion = s.presentacion,
    tipo_presentacion = s.tipo_presentacion,
    cantidad_presentacion = s.cantidad_presentacion,
    alcance_presentacion = s.alcance_presentacion,
    laboratorio = s.laboratorio,
    precio = s.precio,
    precio_lista = s.precio_lista,
    precio_oferta = s.precio_oferta,
    moneda = s.moneda,
    disponibilidad = s.disponibilidad,
    calidad = s.calidad,
    observacion = s.observacion,
    fecha_publicacion = s.fecha_publicacion,
    fecha_dato = s.fecha_dato,
    fecha_actualizacion = GETDATE()
WHEN NOT MATCHED THEN INSERT (
    pais, farmacia, fuente_url, id_producto_farmacia, sku,
    n_lista, medicamento_lista, programa, nombre_comercial,
    principio_activo, concentracion, cantidad_concentracion, unidad_concentracion,
    presentacion, tipo_presentacion, cantidad_presentacion, alcance_presentacion, laboratorio,
    precio, precio_lista, precio_oferta, moneda, disponibilidad, calidad, observacion,
    fecha_publicacion, fecha_dato, fecha_registro, fecha_actualizacion
) VALUES (
    s.pais, s.farmacia, s.fuente_url, s.id_producto_farmacia, s.sku,
    s.n_lista, s.medicamento_lista, s.programa, s.nombre_comercial,
    s.principio_activo, s.concentracion, s.cantidad_concentracion, s.unidad_concentracion,
    s.presentacion, s.tipo_presentacion, s.cantidad_presentacion, s.alcance_presentacion, s.laboratorio,
    s.precio, s.precio_lista, s.precio_oferta, s.moneda, s.disponibilidad, s.calidad, s.observacion,
    s.fecha_publicacion, s.fecha_dato, CAST(GETDATE() AS DATE), GETDATE()
);
"""


def _ids() -> tuple[str, str, str, str]:
    schema = resumen_config()["schema"]
    qschema = f"[{schema}]"
    qtabla = f"[{TABLA}]"
    full = f"{schema}.{TABLA}"
    df = "mac_ame"
    return qschema, qtabla, full, df


def _migrar_fecha_registro_solo_dia(conn, qschema: str, qtabla: str, full: str, df: str) -> None:
    """Asegura fecha_registro como DATE (solo año-mes-día), sin hora."""
    tipo = conn.execute(
        text(
            """
            SELECT DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :tabla AND COLUMN_NAME = N'fecha_registro'
            """
        ),
        {"schema": resumen_config()["schema"], "tabla": TABLA},
    ).scalar()
    if not tipo:
        return
    # Quitar hora en valores existentes (sirve para datetime o date).
    conn.execute(
        text(
            f"UPDATE {qschema}.{qtabla} "
            f"SET fecha_registro = CAST(fecha_registro AS DATE) "
            f"WHERE fecha_registro IS NOT NULL"
        )
    )
    if str(tipo).lower() == "date":
        return
    # Pasar columna DATETIME → DATE (recrear default).
    conn.execute(
        text(
            f"""
            DECLARE @df sysname;
            SELECT @df = dc.name
            FROM sys.default_constraints dc
            INNER JOIN sys.columns c
              ON c.default_object_id = dc.object_id
             AND c.object_id = dc.parent_object_id
            INNER JOIN sys.tables t ON t.object_id = c.object_id
            INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
            WHERE s.name = :schema AND t.name = :tabla AND c.name = N'fecha_registro';
            IF @df IS NOT NULL
              EXEC(N'ALTER TABLE {qschema}.{qtabla} DROP CONSTRAINT [' + @df + N']');
            """
        ),
        {"schema": resumen_config()["schema"], "tabla": TABLA},
    )
    conn.execute(text(f"ALTER TABLE {qschema}.{qtabla} ALTER COLUMN fecha_registro DATE NOT NULL"))
    conn.execute(
        text(
            f"IF NOT EXISTS ("
            f"  SELECT 1 FROM sys.default_constraints dc "
            f"  INNER JOIN sys.columns c ON c.default_object_id = dc.object_id "
            f"  INNER JOIN sys.tables t ON t.object_id = c.object_id "
            f"  INNER JOIN sys.schemas s ON s.schema_id = t.schema_id "
            f"  WHERE s.name = N'{resumen_config()['schema']}' AND t.name = N'{TABLA}' "
            f"    AND c.name = N'fecha_registro'"
            f") ALTER TABLE {qschema}.{qtabla} "
            f"ADD CONSTRAINT DF_{df}_reg DEFAULT CONVERT(date, GETDATE()) FOR fecha_registro"
        )
    )


def asegurar_tabla() -> str:
    qschema, qtabla, full, df = _ids()
    sql = (
        DDL.replace("{qschema}", qschema)
        .replace("{qtabla}", qtabla)
        .replace("{df}", df)
    )
    with engine().begin() as conn:
        conn.execute(text(sql))
        for alter in ALTERS:
            conn.execute(
                text(
                    alter.replace("{qschema}", qschema)
                    .replace("{qtabla}", qtabla)
                    .replace("{full}", full)
                )
            )
        _migrar_fecha_registro_solo_dia(conn, qschema, qtabla, full, df)
    return full


def guardar_filas(filas: Iterable[dict[str, Any]]) -> dict[str, int]:
    qschema, qtabla, full, _df = _ids()
    sql = MERGE_SQL.replace("{qschema}", qschema).replace("{qtabla}", qtabla)
    n = 0
    fechas_batch: set[date] = set()
    with engine().begin() as conn:
        for fila in filas:
            payload = enriquecer_fila_estructurada(fila)
            payload = normalizar_fila_precios(payload)
            fd = _parse_fecha_dato(payload.get("fecha_dato"))
            if fd is not None:
                fechas_batch.add(fd)
            conn.execute(text(sql), payload)
            n += 1
        total = conn.execute(text(f"SELECT COUNT(*) FROM {qschema}.{qtabla}")).scalar_one()
        rd = conn.execute(
            text(
                f"SELECT COUNT(*) FROM {qschema}.{qtabla} "
                "WHERE pais = :pais AND farmacia = :far"
            ),
            {"pais": "República Dominicana", "far": "FarmaValue"},
        ).scalar_one()
    try:
        from scrapper.repositorio_historial import snapshot_desde_actual

        # Historial por cada fecha_dato del lote (no solo el día activo).
        targets = sorted(fechas_batch) or [fecha_snapshot()]
        snap = 0
        for fd in targets:
            if fd is None:
                continue
            snap += int(snapshot_desde_actual(fd) or 0)
    except Exception:
        snap = 0
    return {
        "upserts": n,
        "total_tabla": int(total or 0),
        "rd_farmavalue": int(rd or 0),
        "tabla": full,
        "historial": int(snap or 0),
    }


def purgar_obsoletos(pais: str, farmacia: str, vigentes: Iterable[tuple[str, int]]) -> int:
    """Quita filas de esa farmacia que ya no salen en el cruce de hoy."""
    vigentes = list(vigentes)
    qschema, qtabla, _full, _df = _ids()
    with engine().begin() as conn:
        if not vigentes:
            res = conn.execute(
                text(f"DELETE FROM {qschema}.{qtabla} WHERE pais = :pais AND farmacia = :farmacia"),
                {"pais": pais, "farmacia": farmacia},
            )
            return res.rowcount or 0
        params = {"pais": pais, "farmacia": farmacia}
        for i, (pid, n) in enumerate(vigentes):
            params[f"k{i}"] = f"{pid}|{n}"
        sql = (
            f"DELETE FROM {qschema}.{qtabla} "
            f"WHERE pais = :pais AND farmacia = :farmacia "
            f"AND CONCAT(id_producto_farmacia, '|', CAST(n_lista AS VARCHAR(12))) NOT IN ("
            + ",".join(f":k{i}" for i in range(len(vigentes)))
            + ")"
        )
        res = conn.execute(text(sql), params)
        return res.rowcount or 0


def purgar_obsoletos_fuente(
    pais: str,
    url_host: str,
    vigentes: Iterable[tuple[str, str, int]],
) -> int:
    """Purga filas cuya fuente_url pertenece al agregador (p. ej. farmacias.do).

    vigentes: (farmacia, id_producto_farmacia, n_lista)
    """
    vigentes = list(vigentes)
    qschema, qtabla, _full, _df = _ids()
    like = f"%{url_host}%"
    with engine().begin() as conn:
        if not vigentes:
            res = conn.execute(
                text(
                    f"DELETE FROM {qschema}.{qtabla} "
                    f"WHERE pais = :pais AND fuente_url LIKE :like"
                ),
                {"pais": pais, "like": like},
            )
            return res.rowcount or 0
        params: dict[str, Any] = {"pais": pais, "like": like}
        for i, (far, pid, n) in enumerate(vigentes):
            params[f"k{i}"] = f"{far}|{pid}|{n}"
        sql = (
            f"DELETE FROM {qschema}.{qtabla} "
            f"WHERE pais = :pais AND fuente_url LIKE :like "
            f"AND CONCAT(farmacia, '|', id_producto_farmacia, '|', CAST(n_lista AS VARCHAR(12))) NOT IN ("
            + ",".join(f":k{i}" for i in range(len(vigentes)))
            + ")"
        )
        res = conn.execute(text(sql), params)
        return res.rowcount or 0


def _jsonable(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        # Fechas de auditoría / snapshot: solo día (sin hora).
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return v


def _parse_fecha_dato(valor: date | datetime | str | None) -> date | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor)[:10])


def fecha_snapshot(*, preferir_hoy: bool = True) -> date | None:
    """Día de datos que debe usar la plataforma.

    Con cron diario la fuente de verdad es ``fecha_dato`` (solo día).
    Preferimos el día de hoy en SQL Server; si aún no hay filas de hoy
    (cron pendiente), caemos al ``MAX(fecha_dato)`` disponible.
    """
    qschema, qtabla, _full, _df = _ids()
    with engine().connect() as conn:
        hoy = conn.execute(text("SELECT CAST(GETDATE() AS DATE)")).scalar_one()
        if preferir_hoy:
            n_hoy = conn.execute(
                text(f"SELECT COUNT(*) FROM {qschema}.{qtabla} WHERE fecha_dato = :d"),
                {"d": hoy},
            ).scalar_one()
            if int(n_hoy or 0) > 0:
                return hoy if isinstance(hoy, date) else date.fromisoformat(str(hoy)[:10])
        max_fd = conn.execute(
            text(f"SELECT MAX(fecha_dato) FROM {qschema}.{qtabla}")
        ).scalar_one()
    return _parse_fecha_dato(max_fd)


def listar_filas(*, fecha_dato: date | str | None = None, todos: bool = False) -> list[dict[str, Any]]:
    """Lista precios. Por defecto solo el snapshot del día activo (hoy / último)."""
    qschema, qtabla, _full, _df = _ids()
    params: dict[str, Any] = {}
    where = ""
    if not todos:
        fd = _parse_fecha_dato(fecha_dato) if fecha_dato is not None else fecha_snapshot()
        if fd is not None:
            where = "WHERE fecha_dato = :fd"
            params["fd"] = fd
    sql = (
        f"SELECT id, pais, farmacia, fuente_url, id_producto_farmacia, sku, "
        f"n_lista, medicamento_lista, programa, nombre_comercial, "
        f"principio_activo, concentracion, cantidad_concentracion, unidad_concentracion, "
        f"presentacion, tipo_presentacion, cantidad_presentacion, alcance_presentacion, laboratorio, "
        f"precio, precio_lista, precio_oferta, moneda, disponibilidad, calidad, observacion, "
        f"fecha_publicacion, fecha_dato, fecha_registro, fecha_actualizacion "
        f"FROM {qschema}.{qtabla} "
        f"{where} "
        f"ORDER BY n_lista, pais, farmacia, precio"
    )
    with engine().connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [{k: _jsonable(v) for k, v in dict(r).items()} for r in rows]


def contar(
    pais: str | None = None,
    farmacia: str | None = None,
    *,
    fecha_dato: date | str | None = None,
    todos: bool = False,
) -> int:
    qschema, qtabla, _full, _df = _ids()
    sql = f"SELECT COUNT(*) FROM {qschema}.{qtabla}"
    params: dict[str, Any] = {}
    clauses: list[str] = []
    if pais and farmacia:
        clauses.append("pais = :pais AND farmacia = :farmacia")
        params["pais"] = pais
        params["farmacia"] = farmacia
    if not todos:
        fd = _parse_fecha_dato(fecha_dato) if fecha_dato is not None else fecha_snapshot()
        if fd is not None:
            clauses.append("fecha_dato = :fd")
            params["fd"] = fd
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    with engine().connect() as conn:
        return int(conn.execute(text(sql), params).scalar_one() or 0)
