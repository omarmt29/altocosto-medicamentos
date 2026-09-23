"""Historial de precios por medicamento, país y farmacia (para tendencias)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import bindparam, text

from db import engine, resumen_config
from scrapper.matching import norm
from scrapper.precios import normalizar_fila_precios

TABLA = "medicamentos_precios_historial"
FARMACIA_FALLBACK = "sin_farmacia"

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
        n_lista INT NOT NULL,
        medicamento_lista NVARCHAR(300) NOT NULL,
        programa NVARCHAR(40) NULL,
        producto_key NVARCHAR(500) NOT NULL,
        pais NVARCHAR(80) NOT NULL,
        farmacia NVARCHAR(80) NOT NULL,
        nombre_comercial NVARCHAR(500) NULL,
        concentracion NVARCHAR(300) NULL,
        presentacion NVARCHAR(120) NULL,
        precio DECIMAL(18, 4) NULL,
        moneda CHAR(3) NULL,
        precio_usd DECIMAL(18, 6) NULL,
        precio_lista DECIMAL(18, 4) NULL,
        precio_oferta DECIMAL(18, 4) NULL,
        fuente_url NVARCHAR(500) NULL,
        fecha_dato DATE NOT NULL,
        fecha_vista DATE NOT NULL,
        fecha_registro DATE NOT NULL CONSTRAINT DF_{df}_reg DEFAULT CONVERT(date, GETDATE()),
        CONSTRAINT UQ_{df} UNIQUE (fecha_dato, n_lista, pais, farmacia, producto_key)
    );
END
"""

MERGE_SQL = """
MERGE {qschema}.{qtabla} AS t
USING (SELECT
    :n_lista AS n_lista,
    :medicamento_lista AS medicamento_lista,
    :programa AS programa,
    :producto_key AS producto_key,
    :pais AS pais,
    :farmacia AS farmacia,
    :nombre_comercial AS nombre_comercial,
    :concentracion AS concentracion,
    :presentacion AS presentacion,
    :precio AS precio,
    :moneda AS moneda,
    :precio_usd AS precio_usd,
    :precio_lista AS precio_lista,
    :precio_oferta AS precio_oferta,
    :fuente_url AS fuente_url,
    :fecha_dato AS fecha_dato
) AS s
ON t.fecha_dato = s.fecha_dato
   AND t.n_lista = s.n_lista
   AND t.pais = s.pais
   AND t.farmacia = s.farmacia
   AND t.producto_key = s.producto_key
WHEN MATCHED THEN UPDATE SET
    medicamento_lista = s.medicamento_lista,
    programa = s.programa,
    nombre_comercial = s.nombre_comercial,
    concentracion = s.concentracion,
    presentacion = s.presentacion,
    precio = s.precio,
    moneda = s.moneda,
    precio_usd = s.precio_usd,
    precio_lista = COALESCE(s.precio_lista, t.precio_lista),
    precio_oferta = COALESCE(s.precio_oferta, t.precio_oferta),
    fuente_url = COALESCE(s.fuente_url, t.fuente_url),
    fecha_vista = s.fecha_dato
WHEN NOT MATCHED THEN INSERT (
    n_lista, medicamento_lista, programa, producto_key, pais, farmacia, nombre_comercial,
    concentracion, presentacion, precio, moneda, precio_usd, precio_lista, precio_oferta,
    fuente_url, fecha_dato, fecha_vista, fecha_registro
) VALUES (
    s.n_lista, s.medicamento_lista, s.programa, s.producto_key, s.pais, s.farmacia, s.nombre_comercial,
    s.concentracion, s.presentacion, s.precio, s.moneda, s.precio_usd, s.precio_lista, s.precio_oferta,
    s.fuente_url, s.fecha_dato, s.fecha_dato,
    CAST(GETDATE() AS DATE)
);
"""

# Precio vigente por producto+farmacia justo antes de una fecha: decide si hubo cambio.
PREVIOS_SQL = """
SELECT id, n_lista, pais, farmacia, producto_key, precio, moneda, fecha_dato, fecha_vista
FROM (
    SELECT id, n_lista, pais, farmacia, producto_key, precio, moneda, fecha_dato, fecha_vista,
           ROW_NUMBER() OVER (
               PARTITION BY n_lista, pais, farmacia, producto_key ORDER BY fecha_dato DESC
           ) AS rn
    FROM {qschema}.{qtabla}
    WHERE fecha_dato < :fd
) x
WHERE rn = 1
"""

# Precio sin cambios: se estira la ventana de la fila vigente en vez de crear una nueva.
TOCAR_SQL = """
UPDATE {qschema}.{qtabla}
SET fecha_vista = :fd,
    fuente_url = COALESCE(:fuente_url, fuente_url)
WHERE id = :id AND fecha_vista < :fd
"""

# Al registrar un precio nuevo, la fila anterior deja de estar vigente el día previo.
# Solo aplica si una corrida parcial del mismo día ya había estirado su ventana.
CERRAR_SQL = """
UPDATE {qschema}.{qtabla}
SET fecha_vista = DATEADD(day, -1, :fd)
WHERE id = :id AND fecha_vista >= :fd
"""

# Limpia la fila del día cuando, tras recalcular, resulta igual al precio vigente previo.
BORRAR_REDUNDANTE_SQL = """
DELETE FROM {qschema}.{qtabla}
WHERE fecha_dato = :fd AND n_lista = :n_lista AND pais = :pais
  AND farmacia = :farmacia AND producto_key = :producto_key
"""

EXISTENTES_SQL = """
SELECT n_lista, pais, farmacia, producto_key FROM {qschema}.{qtabla} WHERE fecha_dato = :fd
"""


def producto_key(
    nombre_comercial: str | None = None,
    concentracion: str | None = None,
    presentacion: str | None = None,
    *,
    cantidad_concentracion: str | None = None,
    unidad_concentracion: str | None = None,
) -> str:
    conc = (concentracion or "").strip()
    if not conc and (cantidad_concentracion or unidad_concentracion):
        conc = f"{cantidad_concentracion or ''} {unidad_concentracion or ''}".strip()
    parts = [norm(nombre_comercial or ""), norm(conc), norm(presentacion or "")]
    key = "|".join(p for p in parts if p)
    return key or "sin_identificar"


def producto_key_fila(fila: dict[str, Any]) -> str:
    return producto_key(
        fila.get("nombre_comercial"),
        fila.get("concentracion"),
        fila.get("presentacion"),
        cantidad_concentracion=fila.get("cantidad_concentracion"),
        unidad_concentracion=fila.get("unidad_concentracion"),
    )


def score_fuente_url(url: str | None) -> int:
    """Prioridad de enlace para serie/historial. Más alto = mejor."""
    u = str(url or "").strip().lower()
    if not u or not u.startswith(("http://", "https://")):
        return 0
    if "farmacias.do" in u:
        return 1  # agregador: peor que el PDP de la farmacia
    if "farmavalue.com" in u:
        return 6
    if "farmaciacarol.com" in u or "tiendafarmaciacarol" in u:
        return 5
    if "farmaciasloshidalgos" in u or "hidalgos" in u:
        return 5
    if "qualipharma" in u:
        return 5
    return 3


def elegir_fuente_url(*urls: str | None) -> str | None:
    """Elige la mejor URL no vacía según score_fuente_url."""
    best: str | None = None
    best_s = -1
    for raw in urls:
        u = str(raw or "").strip() or None
        if not u:
            continue
        s = score_fuente_url(u)
        if s > best_s:
            best_s = s
            best = u
    return best


def limpiar_fuentes_serie_medicamento(*, dry_run: bool = False) -> dict[str, int]:
    """Unifica fuente_url por (n_lista, pais, farmacia, producto_key) en historial
    y elimina en vivo filas de agregador (farmacias.do) cuando hay PDP propio.
    """
    from scrapper.repositorio import TABLA as TABLA_LIVE

    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    schema = resumen_config()["schema"]
    qlive = f"[{schema}].[{TABLA_LIVE}]"
    stats = {
        "grupos_historial": 0,
        "filas_historial_actualizadas": 0,
        "live_farmacias_do_borradas": 0,
    }

    sql_groups = f"""
    SELECT n_lista, pais, farmacia, producto_key,
           MAX(CASE WHEN fuente_url IS NOT NULL AND LTRIM(RTRIM(fuente_url)) <> N''
                    THEN fuente_url END) AS cualquiera
    FROM {qschema}.{qtabla}
    GROUP BY n_lista, pais, farmacia, producto_key
    """
    with engine().connect() as conn:
        groups = [dict(r) for r in conn.execute(text(sql_groups)).mappings().all()]

    updates: list[dict[str, Any]] = []
    for g in groups:
        stats["grupos_historial"] += 1
        sql_urls = f"""
        SELECT DISTINCT fuente_url
        FROM {qschema}.{qtabla}
        WHERE n_lista = :n AND pais = :pais AND farmacia = :far AND producto_key = :pk
        """
        with engine().connect() as conn:
            urls = [
                r[0]
                for r in conn.execute(
                    text(sql_urls),
                    {
                        "n": int(g["n_lista"]),
                        "pais": g["pais"],
                        "far": g["farmacia"],
                        "pk": g["producto_key"],
                    },
                ).fetchall()
            ]
        canon = elegir_fuente_url(*urls)
        if not canon:
            continue
        # ¿Hay filas con otra URL o NULL?
        needs = any((str(u or "").strip() or None) != canon for u in urls) or any(u is None or str(u).strip() == "" for u in urls)
        if not needs and len([u for u in urls if str(u or "").strip()]) == 1:
            continue
        updates.append(
            {
                "n": int(g["n_lista"]),
                "pais": g["pais"],
                "far": g["farmacia"],
                "pk": g["producto_key"],
                "url": canon,
            }
        )

    if not dry_run and updates:
        with engine().begin() as conn:
            for u in updates:
                res = conn.execute(
                    text(
                        f"""
                        UPDATE {qschema}.{qtabla}
                        SET fuente_url = :url
                        WHERE n_lista = :n AND pais = :pais AND farmacia = :far
                          AND producto_key = :pk
                          AND (
                            fuente_url IS NULL
                            OR LTRIM(RTRIM(fuente_url)) = N''
                            OR fuente_url <> :url
                          )
                        """
                    ),
                    u,
                )
                stats["filas_historial_actualizadas"] += int(res.rowcount or 0)

    # Live: borrar FarmaValue/Carol/Hidalgos/Qualipharma con URL de agregador
    # si existe otra fila de la misma farmacia+n_lista con PDP propio.
    sql_del_live = f"""
    DELETE t
    FROM {qlive} t
    WHERE t.fuente_url LIKE N'%farmacias.do%'
      AND t.farmacia IN (N'FarmaValue', N'Carol', N'Los Hidalgos', N'Qualipharma')
      AND EXISTS (
        SELECT 1 FROM {qlive} t2
        WHERE t2.pais = t.pais
          AND t2.farmacia = t.farmacia
          AND t2.n_lista = t.n_lista
          AND t2.id <> t.id
          AND t2.fuente_url IS NOT NULL
          AND t2.fuente_url NOT LIKE N'%farmacias.do%'
      )
    """
    # FarmaValue solo-agregador: se recrea desde el scraper oficial.
    sql_del_fv_agg = f"""
    DELETE FROM {qlive}
    WHERE farmacia = N'FarmaValue'
      AND fuente_url LIKE N'%farmacias.do%'
    """
    if not dry_run:
        with engine().begin() as conn:
            r1 = conn.execute(text(sql_del_live))
            stats["live_farmacias_do_borradas"] += int(r1.rowcount or 0)
            r2 = conn.execute(text(sql_del_fv_agg))
            stats["live_farmacias_do_borradas"] += int(r2.rowcount or 0)
    else:
        with engine().connect() as conn:
            n1 = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*) FROM {qlive}
                    WHERE fuente_url LIKE N'%farmacias.do%'
                      AND farmacia IN (N'FarmaValue', N'Carol', N'Los Hidalgos', N'Qualipharma')
                    """
                )
            ).scalar_one()
            stats["live_farmacias_do_borradas"] = int(n1 or 0)

    stats["grupos_a_unificar"] = len(updates)
    return stats


def producto_label(fila: dict[str, Any]) -> str:
    nc = str(fila.get("nombre_comercial") or "").strip() or "—"
    conc = str(fila.get("concentracion") or "").strip()
    if not conc:
        qty = str(fila.get("cantidad_concentracion") or "").strip()
        unit = str(fila.get("unidad_concentracion") or "").strip()
        if qty or unit:
            conc = f"{qty} {unit}".strip()
    pres = str(fila.get("presentacion") or "").strip()
    lista = str(fila.get("medicamento_lista") or "").strip()
    bits = [nc]
    if conc:
        bits.append(conc)
    if pres:
        bits.append(pres)
    label = " · ".join(bits)
    if lista and norm(lista) not in norm(nc):
        label = f"{label} ({lista})"
    return label


def _ids() -> tuple[str, str, str, str]:
    schema = resumen_config()["schema"]
    return f"[{schema}]", f"[{TABLA}]", f"{schema}.{TABLA}", "mac_ph"


# Nombre completo de la tabla una vez migrada en este proceso.
_TABLA_LISTA: str | None = None


def _columnas(conn, schema: str) -> dict[str, tuple[str, bool]]:
    """Mapa columna -> (tipo, admite NULL) para decidir qué migración falta."""
    rows = conn.execute(
        text(
            """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :tabla
            """
        ),
        {"schema": schema, "tabla": TABLA},
    ).fetchall()
    return {str(r[0]): (str(r[1]).lower(), str(r[2]).upper() == "YES") for r in rows}


def asegurar_tabla(*, forzar: bool = False) -> str:
    """Crea la tabla y aplica solo las migraciones que falten.

    Cada lectura de tendencias entra por aquí. Antes se reescribía la tabla
    completa en cada llamada (UPDATE de fecha_registro y de fecha_vista, ALTER
    COLUMN incondicionales), lo que bloqueaba la tabla durante segundos y
    provocaba deadlocks contra el scraper. Ahora cada paso va condicionado al
    estado real del esquema y el resultado se memoiza por proceso.
    """
    global _TABLA_LISTA
    qschema, qtabla, full, df = _ids()
    if _TABLA_LISTA == full and not forzar:
        return full
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
        cols = _columnas(conn, schema)
        # Normalizar fecha_registro a solo día (DATE).
        tipo = (cols.get("fecha_registro") or (None, True))[0]
        if tipo and tipo != "date":
            conn.execute(
                text(
                    f"UPDATE {qschema}.{qtabla} "
                    f"SET fecha_registro = CAST(fecha_registro AS DATE) "
                    f"WHERE fecha_registro IS NOT NULL"
                )
            )
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
                {"schema": schema, "tabla": TABLA},
            )
            conn.execute(
                text(f"ALTER TABLE {qschema}.{qtabla} ALTER COLUMN fecha_registro DATE NOT NULL")
            )
            conn.execute(
                text(
                    f"IF NOT EXISTS ("
                    f"  SELECT 1 FROM sys.default_constraints dc "
                    f"  INNER JOIN sys.columns c ON c.default_object_id = dc.object_id "
                    f"  INNER JOIN sys.tables t ON t.object_id = c.object_id "
                    f"  INNER JOIN sys.schemas s ON s.schema_id = t.schema_id "
                    f"  WHERE s.name = N'{schema}' AND t.name = N'{TABLA}' "
                    f"    AND c.name = N'fecha_registro'"
                    f") ALTER TABLE {qschema}.{qtabla} "
                    f"ADD CONSTRAINT DF_{df}_reg DEFAULT CONVERT(date, GETDATE()) FOR fecha_registro"
                )
            )
        # Migración: historial por medicamento (no solo por principio).
        # Si la columna ya es NOT NULL el backfill está hecho y no hay nada que tocar.
        pk_meta = cols.get("producto_key")
        if not pk_meta:
            conn.execute(
                text(f"ALTER TABLE {qschema}.{qtabla} ADD producto_key NVARCHAR(500) NULL")
            )
        if not pk_meta or pk_meta[1]:
            rows_pk = conn.execute(
                text(
                    f"SELECT id, nombre_comercial, concentracion, presentacion "
                    f"FROM {qschema}.{qtabla} WHERE producto_key IS NULL OR producto_key = ''"
                )
            ).mappings().all()
            for row in rows_pk:
                pk = producto_key(
                    row.get("nombre_comercial"),
                    row.get("concentracion"),
                    row.get("presentacion"),
                )
                conn.execute(
                    text(f"UPDATE {qschema}.{qtabla} SET producto_key = :pk WHERE id = :id"),
                    {"pk": pk, "id": row["id"]},
                )
            conn.execute(
                text(
                    f"UPDATE {qschema}.{qtabla} SET producto_key = N'sin_identificar' "
                    f"WHERE producto_key IS NULL OR producto_key = ''"
                )
            )
            conn.execute(
                text(f"ALTER TABLE {qschema}.{qtabla} ALTER COLUMN producto_key NVARCHAR(500) NOT NULL")
            )
        # Migración: farmacia NOT NULL + UNIQUE incluye farmacia (serie por farmacia).
        far_meta = cols.get("farmacia")
        if not far_meta:
            conn.execute(
                text(f"ALTER TABLE {qschema}.{qtabla} ADD farmacia NVARCHAR(80) NULL")
            )
        conn.execute(
            text(
                f"UPDATE {qschema}.{qtabla} SET farmacia = N'{FARMACIA_FALLBACK}' "
                f"WHERE farmacia IS NULL OR LTRIM(RTRIM(farmacia)) = N''"
            )
        )
        far_meta2 = _columnas(conn, schema).get("farmacia")
        if far_meta2 and far_meta2[1]:
            # SQL Server no permite ALTER COLUMN si hay índices que incluyen la columna.
            for ix in (f"IX_{df}_ventana", f"IX_{df}_vigencia", f"IX_{df}_vigencia_far"):
                conn.execute(
                    text(
                        f"IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'{ix}' "
                        f"  AND object_id = OBJECT_ID(N'{schema}.{TABLA}')) "
                        f"DROP INDEX [{ix}] ON {qschema}.{qtabla}"
                    )
                )
            conn.execute(
                text(f"ALTER TABLE {qschema}.{qtabla} ALTER COLUMN farmacia NVARCHAR(80) NOT NULL")
            )
        uq_old = conn.execute(
            text(
                """
                SELECT kc.name
                FROM sys.key_constraints kc
                INNER JOIN sys.tables t ON t.object_id = kc.parent_object_id
                INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
                WHERE kc.[type] = 'UQ'
                  AND s.name = :schema AND t.name = :tabla
                  AND kc.name = :uq_name
                """
            ),
            {"schema": schema, "tabla": TABLA, "uq_name": f"UQ_{df}"},
        ).scalar()
        if uq_old:
            uq_cols = conn.execute(
                text(
                    """
                    SELECT c.name
                    FROM sys.index_columns ic
                    INNER JOIN sys.columns c
                      ON c.object_id = ic.object_id AND c.column_id = ic.column_id
                    INNER JOIN sys.indexes i ON i.object_id = ic.object_id AND i.index_id = ic.index_id
                    INNER JOIN sys.key_constraints kc ON kc.parent_object_id = i.object_id AND kc.unique_index_id = i.index_id
                    WHERE kc.name = :uq_name
                    ORDER BY ic.key_ordinal
                    """
                ),
                {"uq_name": uq_old},
            ).fetchall()
            col_names = [r[0] for r in uq_cols]
            wanted = ["fecha_dato", "n_lista", "pais", "farmacia", "producto_key"]
            if col_names != wanted:
                conn.execute(text(f"ALTER TABLE {qschema}.{qtabla} DROP CONSTRAINT [{uq_old}]"))
                uq_old = None
        uq_new = conn.execute(
            text(
                """
                SELECT 1
                FROM sys.key_constraints kc
                INNER JOIN sys.tables t ON t.object_id = kc.parent_object_id
                INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
                WHERE kc.[type] = 'UQ'
                  AND s.name = :schema AND t.name = :tabla
                  AND kc.name = :uq_name
                """
            ),
            {"schema": schema, "tabla": TABLA, "uq_name": f"UQ_{df}"},
        ).scalar()
        if not uq_new:
            conn.execute(
                text(
                    f"ALTER TABLE {qschema}.{qtabla} "
                    f"ADD CONSTRAINT UQ_{df} UNIQUE (fecha_dato, n_lista, pais, farmacia, producto_key)"
                )
            )
        # Migración: ventana de vigencia. Un registro deja de escribirse cada día y pasa
        # a cubrir el rango [fecha_dato, fecha_vista] mientras el precio no cambie.
        fv_meta = cols.get("fecha_vista")
        if not fv_meta:
            conn.execute(text(f"ALTER TABLE {qschema}.{qtabla} ADD fecha_vista DATE NULL"))
        if not fv_meta or fv_meta[1]:
            conn.execute(
                text(
                    f"UPDATE {qschema}.{qtabla} SET fecha_vista = fecha_dato "
                    f"WHERE fecha_vista IS NULL OR fecha_vista < fecha_dato"
                )
            )
            conn.execute(
                text(f"ALTER TABLE {qschema}.{qtabla} ALTER COLUMN fecha_vista DATE NOT NULL")
            )
        conn.execute(
            text(
                f"IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_{df}_vigencia' "
                f"  AND object_id = OBJECT_ID(N'{schema}.{TABLA}')) "
                f"DROP INDEX IX_{df}_vigencia ON {qschema}.{qtabla}"
            )
        )
        conn.execute(
            text(
                f"IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_{df}_vigencia_far') "
                f"CREATE INDEX IX_{df}_vigencia_far ON {qschema}.{qtabla} "
                f"(n_lista, producto_key, pais, farmacia, fecha_dato) "
                f"INCLUDE (fecha_vista, precio, moneda, precio_usd)"
            )
        )
        # El explorador filtra por ventana de vigencia + país / farmacia sin pasar por n_lista.
        conn.execute(
            text(
                f"IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_{df}_ventana') "
                f"CREATE INDEX IX_{df}_ventana ON {qschema}.{qtabla} "
                f"(fecha_dato, fecha_vista) "
                f"INCLUDE (n_lista, pais, producto_key, farmacia, precio, moneda, precio_usd)"
            )
        )
        # Enlace al producto en la farmacia (para la tabla de serie).
        if "fuente_url" not in _columnas(conn, schema):
            conn.execute(
                text(f"ALTER TABLE {qschema}.{qtabla} ADD fuente_url NVARCHAR(500) NULL")
            )
        cols2 = _columnas(conn, schema)
        if "precio_lista" not in cols2:
            conn.execute(
                text(f"ALTER TABLE {qschema}.{qtabla} ADD precio_lista DECIMAL(18, 4) NULL")
            )
        if "precio_oferta" not in cols2:
            conn.execute(
                text(f"ALTER TABLE {qschema}.{qtabla} ADD precio_oferta DECIMAL(18, 4) NULL")
            )
    _TABLA_LISTA = full
    return full


def _jsonable(v: Any) -> Any:
    if isinstance(v, datetime):
        # Solo día para fechas de historial / tendencias.
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def _a_date(v: Any) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def _clave_params(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "n_lista": row["n_lista"],
        "pais": row["pais"],
        "farmacia": row["farmacia"],
        "producto_key": row["producto_key"],
    }


def _norm_farmacia(v: Any) -> str:
    s = str(v or "").strip()
    return s or FARMACIA_FALLBACK


def _mismo_precio(prev: Any, row: dict[str, Any]) -> bool:
    """¿El precio de hoy es el mismo que el vigente?

    Solo se comparan precio local y moneda. `precio_usd` queda fuera a propósito:
    la tasa de cambio se mueve todos los días y haría que cada corrida pareciera
    un cambio de precio, que es justo lo que se quiere evitar.
    """
    if str(prev.get("moneda") or "").upper() != str(row.get("moneda") or "").upper():
        return False
    ant, hoy = prev.get("precio"), row.get("precio")
    if ant is None or hoy is None:
        return ant is None and hoy is None
    try:
        # La columna es DECIMAL(18,4): comparar con esa precisión evita falsos cambios.
        return round(float(ant), 4) == round(float(hoy), 4)
    except (TypeError, ValueError):
        return False


def snapshot_desde_actual(fecha_dato: date | None = None) -> int:
    """Registra el precio por (n_lista, país, farmacia, producto) solo si cambió.

    Devuelve la cantidad de precios efectivamente escritos, no la de productos
    revisados: si un precio sigue igual al vigente no se crea fila nueva, solo se
    estira su `fecha_vista`.
    """
    from scrapper.repositorio import fecha_snapshot, listar_filas

    asegurar_tabla()
    fd = fecha_dato or fecha_snapshot()
    if fd is None:
        return 0
    filas = listar_filas(fecha_dato=fd)
    fx = None
    try:
        import requests
        from generar_comparativo import a_usd, tasas

        fx = tasas(requests.Session())
    except Exception:
        fx = None

    # Una fila por farmacia (ya no se colapsa al mínimo del país).
    por_far: dict[tuple[int, str, str, str], dict[str, Any]] = {}
    for f in filas:
        try:
            n = int(f.get("n_lista") or 0)
        except Exception:
            continue
        pais = str(f.get("pais") or "").strip()
        farmacia = _norm_farmacia(f.get("farmacia"))
        if not n or not pais:
            continue
        precio = f.get("precio")
        if precio is None:
            continue
        try:
            precio_f = float(precio)
        except Exception:
            continue
        moneda = str(f.get("moneda") or "USD").upper()
        usd = None
        if fx is not None:
            try:
                usd = a_usd(precio_f, moneda, fx)
            except Exception:
                usd = None
        if usd is None and moneda == "USD":
            usd = precio_f
        pk = producto_key_fila(f)
        key = (n, pais, farmacia, pk)
        # Duplicados mismo día: priorizar la fila con mejor fuente_url (PDP > agregador).
        # Si empatan en calidad de URL, quedarse con el precio más bajo.
        # (Antes se mezclaba precio barato de farmacias.do + URL de FarmaValue → saltos falsos.)
        fuente_url = str(f.get("fuente_url") or "").strip() or None
        url_score = score_fuente_url(fuente_url)
        prev = por_far.get(key)
        score = usd if usd is not None else precio_f
        prev_score = None
        prev_url_score = -1
        if prev:
            prev_score = prev.get("precio_usd")
            if prev_score is None:
                prev_score = prev.get("precio")
            prev_url_score = score_fuente_url(prev.get("fuente_url"))
        take = False
        if prev is None:
            take = True
        elif url_score > prev_url_score:
            take = True
        elif url_score == prev_url_score and score is not None and prev_score is not None and score < float(prev_score):
            take = True
        if take:
            row = {
                "n_lista": n,
                "medicamento_lista": f.get("medicamento_lista") or "",
                "programa": f.get("programa"),
                "producto_key": pk,
                "pais": pais,
                "farmacia": farmacia,
                "nombre_comercial": f.get("nombre_comercial"),
                "concentracion": f.get("concentracion"),
                "presentacion": f.get("presentacion"),
                "precio": precio_f,
                "moneda": moneda,
                "precio_usd": float(usd) if usd is not None else None,
                "precio_lista": _as_float(f.get("precio_lista")),
                "precio_oferta": _as_float(f.get("precio_oferta")),
                "fuente_url": fuente_url,
                "fecha_dato": fd if isinstance(fd, date) else date.fromisoformat(str(fd)[:10]),
            }
            if prev is not None:
                row["fuente_url"] = elegir_fuente_url(prev.get("fuente_url"), row.get("fuente_url"))
            normalizar_fila_precios(row)
            por_far[key] = row
        elif prev is not None:
            # No reemplazar precio: solo mejorar fuente_url si aplica.
            mejor = elegir_fuente_url(prev.get("fuente_url"), fuente_url)
            if mejor and mejor != prev.get("fuente_url"):
                prev["fuente_url"] = mejor
                por_far[key] = prev
    qschema, qtabla, _full, _df = _ids()

    def _sql(plantilla: str) -> str:
        return plantilla.replace("{qschema}", qschema).replace("{qtabla}", qtabla)

    fd_date = fd if isinstance(fd, date) else date.fromisoformat(str(fd)[:10])
    n = 0
    with engine().begin() as conn:
        previos = {
            (
                int(r["n_lista"]),
                str(r["pais"]),
                _norm_farmacia(r.get("farmacia")),
                str(r["producto_key"]),
            ): r
            for r in conn.execute(text(_sql(PREVIOS_SQL)), {"fd": fd_date}).mappings().all()
        }
        del_sql = _sql(BORRAR_REDUNDANTE_SQL)
        existentes = {
            (
                int(r["n_lista"]),
                str(r["pais"]),
                _norm_farmacia(r.get("farmacia")),
                str(r["producto_key"]),
            )
            for r in conn.execute(text(_sql(EXISTENTES_SQL)), {"fd": fd_date}).mappings().all()
        }
        for key, row in por_far.items():
            prev = previos.get(key)
            if prev is not None and _mismo_precio(prev, row):
                if _a_date(prev.get("fecha_vista")) != fd_date:
                    conn.execute(
                        text(_sql(TOCAR_SQL)),
                        {
                            "id": int(prev["id"]),
                            "fd": fd_date,
                            "fuente_url": row.get("fuente_url"),
                        },
                    )
                if key in existentes:
                    conn.execute(text(del_sql), {"fd": fd_date, **_clave_params(row)})
                    existentes.discard(key)
                continue
            if prev is not None and _a_date(prev.get("fecha_vista")) >= fd_date:
                conn.execute(text(_sql(CERRAR_SQL)), {"id": int(prev["id"]), "fd": fd_date})
            conn.execute(text(_sql(MERGE_SQL)), row)
            existentes.add(key)
            n += 1
    return n


def fechas_dato_en_precios() -> list[date]:
    """Todas las fecha_dato presentes en la tabla viva de precios."""
    from scrapper.repositorio import _ids as ids_precios

    qschema, qtabla, _full, _df = ids_precios()
    sql = f"SELECT DISTINCT fecha_dato FROM {qschema}.{qtabla} ORDER BY fecha_dato"
    with engine().connect() as conn:
        rows = conn.execute(text(sql)).fetchall()
    out: list[date] = []
    for r in rows:
        v = r[0]
        if isinstance(v, datetime):
            out.append(v.date())
        elif isinstance(v, date):
            out.append(v)
        elif v:
            out.append(date.fromisoformat(str(v)[:10]))
    return out


def reconstruir_historial(*, fechas: list[date] | None = None) -> dict[str, int]:
    """Rellena el historial con cada fecha_dato de la tabla de medicamentos.

    Por defecto toma todas las fechas distintas de medicamentos_altos_costos_america.
    """
    targets = fechas if fechas is not None else fechas_dato_en_precios()
    total = 0
    por_fecha: dict[str, int] = {}
    for fd in targets:
        n = snapshot_desde_actual(fd)
        por_fecha[fd.isoformat()] = n
        total += n
    return {"fechas": len(targets), "filas": total, "detalle": por_fecha}


def fechas_disponibles() -> list[str]:
    """Fechas con precio conocido: días de cambio más el último día observado.

    Como un precio estable ya no genera fila por día, `fecha_dato` sola dejaría
    fuera los días en que solo se confirmó el precio anterior.
    """
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    sql = (
        f"SELECT fecha_dato AS f FROM {qschema}.{qtabla} "
        f"UNION SELECT fecha_vista FROM {qschema}.{qtabla} "
        f"ORDER BY f"
    )
    with engine().connect() as conn:
        rows = conn.execute(text(sql)).fetchall()
    return [r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0])[:10] for r in rows]


def _parse_lista_csv(raw: str | list[str] | None) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        items = [str(x or "").strip() for x in raw]
    else:
        items = [p.strip() for p in str(raw).split("|") if p.strip()]
        if len(items) <= 1:
            items = [p.strip() for p in str(raw).split(",") if p.strip()]
    out = [x for x in items if x]
    return out or None


def _usd_de(f: dict[str, Any]) -> float | None:
    v = f.get("precio_usd")
    if v is None:
        if str(f.get("moneda") or "").upper() == "USD" and f.get("precio") is not None:
            try:
                return float(f["precio"])
            except (TypeError, ValueError):
                return None
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _as_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def serie_medicamento(
    n_lista: int,
    producto_key_val: str,
    *,
    agrupar: str = "pais",
    paises: str | list[str] | None = None,
    farmacias: str | list[str] | None = None,
) -> dict[str, Any]:
    """Serie histórica de un producto.

    agrupar:
      - pais: mínimo USD por país en cada fecha de cambio (compatible con UI previa)
      - farmacia: una serie por farmacia (+ país)
    """
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    pk = str(producto_key_val or "").strip()
    modo = str(agrupar or "pais").strip().lower()
    if modo not in ("pais", "farmacia"):
        modo = "pais"
    filtro_paises = _parse_lista_csv(paises)
    filtro_farms = _parse_lista_csv(farmacias)

    sql = (
        f"SELECT * FROM {qschema}.{qtabla} "
        f"WHERE n_lista = :n AND producto_key = :pk "
        f"ORDER BY fecha_dato, pais, farmacia"
    )
    with engine().connect() as conn:
        rows = conn.execute(text(sql), {"n": int(n_lista), "pk": pk}).mappings().all()
    filas = [{k: _jsonable(v) for k, v in dict(r).items()} for r in rows]
    for f in filas:
        f["farmacia"] = _norm_farmacia(f.get("farmacia"))

    paises_disp = sorted({str(f.get("pais")) for f in filas if f.get("pais")})
    farms_disp_map: dict[str, str] = {}
    for f in filas:
        far = str(f.get("farmacia") or "")
        pais = str(f.get("pais") or "")
        if far and pais:
            farms_disp_map[f"{far}||{pais}"] = far
    farmacias_disponibles = []
    for key in sorted(
        farms_disp_map.keys(),
        key=lambda k: (k.split("||", 1)[0].lower(), k.split("||", 1)[1].lower()),
    ):
        far, pais = key.split("||", 1)
        farmacias_disponibles.append({"farmacia": far, "pais": pais, "id": key})

    def _pasa_filtros(f: dict[str, Any]) -> bool:
        if filtro_paises and str(f.get("pais") or "") not in filtro_paises:
            return False
        if filtro_farms:
            far = str(f.get("farmacia") or "")
            pais = str(f.get("pais") or "")
            ids = {f"{far}||{pais}", far}
            if not any(x in filtro_farms for x in ids):
                return False
        return True

    filas_f = [f for f in filas if _pasa_filtros(f)]

    series: list[dict[str, Any]] = []
    if modo == "farmacia":
        grupos: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for f in filas_f:
            key = (str(f.get("farmacia") or ""), str(f.get("pais") or ""))
            grupos.setdefault(key, []).append(f)
        for (far, pais) in sorted(grupos.keys(), key=lambda k: (k[0].lower(), k[1].lower())):
            pts = []
            for f in grupos[(far, pais)]:
                pts.append(
                    {
                        "fecha": str(f.get("fecha_dato"))[:10],
                        "vigente_hasta": str(f.get("fecha_vista") or f.get("fecha_dato"))[:10],
                        "precio": f.get("precio"),
                        "precio_usd": f.get("precio_usd"),
                        "moneda": f.get("moneda"),
                        "farmacia": far,
                        "pais": pais,
                        "nombre_comercial": f.get("nombre_comercial"),
                        "concentracion": f.get("concentracion"),
                        "presentacion": f.get("presentacion"),
                        "fuente_url": f.get("fuente_url"),
                        "precio_lista": f.get("precio_lista"),
                        "precio_oferta": f.get("precio_oferta"),
                    }
                )
            series.append(
                {
                    "id": f"{far}||{pais}",
                    "label": f"{far} · {pais}",
                    "pais": pais,
                    "farmacia": far,
                    "puntos": pts,
                }
            )
    else:
        # País: en cada fecha de cambio, mínimo USD entre farmacias vigentes ese día.
        fechas_cambio = sorted(
            {str(f.get("fecha_dato"))[:10] for f in filas_f if f.get("fecha_dato")}
        )
        por_pais: dict[str, list[dict[str, Any]]] = {}
        for f in filas_f:
            por_pais.setdefault(str(f.get("pais") or ""), []).append(f)

        for pais in sorted(por_pais.keys()):
            rows_p = por_pais[pais]
            pts = []
            for fd in fechas_cambio:
                vigentes = [
                    f
                    for f in rows_p
                    if str(f.get("fecha_dato"))[:10] <= fd
                    and str(f.get("fecha_vista") or f.get("fecha_dato"))[:10] >= fd
                ]
                if not vigentes:
                    continue
                best = None
                best_usd = None
                for f in vigentes:
                    usd = _usd_de(f)
                    if usd is None:
                        continue
                    if best is None or usd < best_usd:
                        best = f
                        best_usd = usd
                if best is None:
                    continue
                # Solo emitir punto si alguna farmacia de este país cambió ese día
                # o si es la primera fecha global (mantiene densidad razonable).
                cambio_local = any(str(f.get("fecha_dato"))[:10] == fd for f in rows_p)
                if not cambio_local and pts:
                    continue
                pts.append(
                    {
                        "fecha": fd,
                        "vigente_hasta": str(best.get("fecha_vista") or best.get("fecha_dato"))[:10],
                        "precio": best.get("precio"),
                        "precio_usd": best.get("precio_usd"),
                        "moneda": best.get("moneda"),
                        "farmacia": best.get("farmacia"),
                        "pais": pais,
                        "nombre_comercial": best.get("nombre_comercial"),
                        "concentracion": best.get("concentracion"),
                        "presentacion": best.get("presentacion"),
                        "fuente_url": best.get("fuente_url"),
                        "precio_lista": best.get("precio_lista"),
                        "precio_oferta": best.get("precio_oferta"),
                    }
                )
            if pts:
                series.append(
                    {
                        "id": pais,
                        "label": pais,
                        "pais": pais,
                        "farmacia": None,
                        "puntos": pts,
                    }
                )

    fechas = sorted(
        {
            str(p.get("fecha"))[:10]
            for s in series
            for p in (s.get("puntos") or [])
            if p.get("fecha")
        }
    )
    meta = filas[0] if filas else {}
    return {
        "n_lista": int(n_lista),
        "producto_key": pk,
        "agrupar": modo,
        "medicamento_lista": meta.get("medicamento_lista"),
        "nombre_comercial": meta.get("nombre_comercial"),
        "concentracion": meta.get("concentracion"),
        "presentacion": meta.get("presentacion"),
        "producto_label": producto_label(meta) if meta else None,
        "fechas": fechas,
        "series": series,
        "paises_disponibles": paises_disp,
        "farmacias_disponibles": farmacias_disponibles,
        "total_puntos": sum(len(s.get("puntos") or []) for s in series),
        "nota_historial": (
            "Las series por farmacia se completan con scrapes futuros; "
            "el histórico previo suele tener solo la farmacia del mínimo del país."
        ),
    }


def serie_principio(n_lista: int) -> dict[str, Any]:
    """Compatibilidad: devuelve el medicamento con más fechas del principio."""
    meds = listar_medicamentos_con_historial(n_lista=int(n_lista), limite=500)
    if not meds:
        return serie_medicamento(int(n_lista), "sin_identificar")
    best = max(meds, key=lambda m: (int(m.get("fechas") or 0), str(m.get("producto_label") or "")))
    return serie_medicamento(int(n_lista), str(best.get("producto_key") or "sin_identificar"))


def listar_medicamentos_con_historial(
    *,
    n_lista: int | None = None,
    limite: int = 500,
) -> list[dict[str, Any]]:
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    where = "WHERE t.n_lista = :n" if n_lista is not None else ""
    params: dict[str, Any] = {}
    if n_lista is not None:
        params["n"] = int(n_lista)
    sql = (
        f"SELECT TOP ({int(limite)}) t.n_lista, t.producto_key, "
        f"MAX(t.medicamento_lista) AS medicamento_lista, "
        f"MAX(t.nombre_comercial) AS nombre_comercial, "
        f"MAX(t.concentracion) AS concentracion, "
        f"MAX(t.presentacion) AS presentacion, "
        f"COUNT(DISTINCT t.fecha_dato) AS fechas, COUNT(DISTINCT t.pais) AS paises, "
        f"COUNT(DISTINCT t.farmacia) AS farmacias, "
        f"STUFF(("
        f"SELECT DISTINCT '|' + CAST(p2.pais AS NVARCHAR(80)) "
        f"FROM {qschema}.{qtabla} p2 "
        f"WHERE p2.n_lista = t.n_lista AND p2.producto_key = t.producto_key "
        f"FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, '') AS paises_list "
        f"FROM {qschema}.{qtabla} t {where} "
        f"GROUP BY t.n_lista, t.producto_key "
        f"ORDER BY MAX(t.medicamento_lista), MAX(t.nombre_comercial), t.producto_key"
    )
    with engine().connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    out = []
    for r in rows:
        item = {k: _jsonable(v) for k, v in dict(r).items()}
        item["producto_label"] = producto_label(item)
        out.append(item)
    return out


def listar_medicamentos_por_pais(
    pais: str,
    *,
    fecha_dato: str | None = None,
    limite: int = 500,
) -> list[dict[str, Any]]:
    """Presentaciones con precio en un país (última fecha o fecha indicada)."""
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    p = str(pais or "").strip()
    if not p:
        return []
    fd = str(fecha_dato or "").strip()[:10] if fecha_dato else None
    if not fd:
        fechas = fechas_disponibles()
        fd = fechas[-1] if fechas else None
    if not fd:
        return []
    sql = (
        f"SELECT TOP ({int(limite)}) n_lista, producto_key, "
        f"MAX(medicamento_lista) AS medicamento_lista, "
        f"MAX(nombre_comercial) AS nombre_comercial, "
        f"MAX(concentracion) AS concentracion, "
        f"MAX(presentacion) AS presentacion, "
        f"MIN(precio_usd) AS min_precio_usd, "
        f"MAX(farmacia) AS farmacia "
        f"FROM {qschema}.{qtabla} "
        f"WHERE pais = :pais AND fecha_dato <= :fd AND fecha_vista >= :fd "
        f"GROUP BY n_lista, producto_key "
        f"ORDER BY MAX(medicamento_lista), MAX(nombre_comercial), producto_key"
    )
    with engine().connect() as conn:
        rows = conn.execute(text(sql), {"pais": p, "fd": fd}).mappings().all()
    out = []
    for r in rows:
        item = {k: _jsonable(v) for k, v in dict(r).items()}
        item["producto_label"] = producto_label(item)
        out.append(item)
    return out


def listar_medicamentos_por_fecha(
    fecha_dato: str,
    *,
    limite: int = 300,
) -> list[dict[str, Any]]:
    """Presentaciones con precio en una fecha de scrape."""
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    fd = str(fecha_dato or "").strip()[:10]
    if not fd:
        return []
    sql = (
        f"SELECT TOP ({int(limite)}) n_lista, producto_key, pais, "
        f"MAX(medicamento_lista) AS medicamento_lista, "
        f"MAX(nombre_comercial) AS nombre_comercial, "
        f"MAX(concentracion) AS concentracion, "
        f"MAX(presentacion) AS presentacion, "
        f"MIN(precio_usd) AS min_precio_usd, "
        f"MAX(farmacia) AS farmacia "
        f"FROM {qschema}.{qtabla} "
        f"WHERE fecha_dato <= :fd AND fecha_vista >= :fd "
        f"GROUP BY n_lista, producto_key, pais "
        f"ORDER BY MAX(medicamento_lista), pais, MAX(nombre_comercial)"
    )
    with engine().connect() as conn:
        rows = conn.execute(text(sql), {"fd": fd}).mappings().all()
    out = []
    for r in rows:
        item = {k: _jsonable(v) for k, v in dict(r).items()}
        item["producto_label"] = producto_label(item)
        out.append(item)
    return out


def listar_principios_con_historial(limite: int = 200) -> list[dict[str, Any]]:
    """Resumen por principio (agrupa medicamentos del mismo n_lista)."""
    meds = listar_medicamentos_con_historial(limite=max(int(limite) * 4, 500))
    by_n: dict[int, dict[str, Any]] = {}
    for m in meds:
        n = int(m.get("n_lista") or 0)
        if not n:
            continue
        cur = by_n.get(n)
        if not cur:
            by_n[n] = {
                "n_lista": n,
                "medicamento_lista": m.get("medicamento_lista"),
                "fechas": int(m.get("fechas") or 0),
                "paises": int(m.get("paises") or 0),
                "medicamentos": 1,
            }
            continue
        cur["fechas"] = max(int(cur.get("fechas") or 0), int(m.get("fechas") or 0))
        cur["paises"] = max(int(cur.get("paises") or 0), int(m.get("paises") or 0))
        cur["medicamentos"] = int(cur.get("medicamentos") or 0) + 1
    return sorted(by_n.values(), key=lambda x: str(x.get("medicamento_lista") or ""))[: int(limite)]


def resumen_indicadores_tendencias() -> dict[str, Any]:
    """Agregados para paneles de tendencias (snapshot última fecha + series temporales)."""
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    fechas = fechas_disponibles()
    ultima = fechas[-1] if fechas else None

    with engine().connect() as conn:
        meds_por_principio = conn.execute(
            text(
                f"""
                SELECT n_lista,
                       MAX(medicamento_lista) AS medicamento_lista,
                       COUNT(DISTINCT producto_key) AS medicamentos
                FROM {qschema}.{qtabla}
                GROUP BY n_lista
                ORDER BY COUNT(DISTINCT producto_key) DESC, MAX(medicamento_lista)
                """
            )
        ).mappings().all()

        # Cada fila cubre un rango de días, así que el conteo por fecha se resuelve
        # cruzando los días conocidos contra las ventanas de vigencia.
        puntos_por_fecha = conn.execute(
            text(
                f"""
                WITH dias AS (
                    SELECT fecha_dato AS f FROM {qschema}.{qtabla}
                    UNION
                    SELECT fecha_vista FROM {qschema}.{qtabla}
                )
                SELECT d.f AS fecha_dato,
                       COUNT(*) AS puntos,
                       COUNT(DISTINCT h.producto_key) AS medicamentos,
                       COUNT(DISTINCT h.n_lista) AS principios,
                       COUNT(DISTINCT h.pais) AS paises
                FROM dias d
                INNER JOIN {qschema}.{qtabla} h
                    ON h.fecha_dato <= d.f AND h.fecha_vista >= d.f
                GROUP BY d.f
                ORDER BY d.f
                """
            )
        ).mappings().all()

        por_pais: list[Any] = []
        fd_indicadores = None
        try:
            from scrapper.repositorio import fecha_snapshot as fd_precios

            fd_p = fd_precios()
            if fd_p is not None:
                fd_s = fd_p.isoformat() if hasattr(fd_p, "isoformat") else str(fd_p)[:10]
                if fd_s in fechas:
                    fd_indicadores = fd_p
        except Exception:
            fd_indicadores = None
        if fd_indicadores is None:
            fd_indicadores = ultima
        if fd_indicadores:
            por_pais = conn.execute(
                text(
                    f"""
                    SELECT pais,
                           COUNT(DISTINCT n_lista) AS principios,
                           COUNT(DISTINCT producto_key) AS medicamentos,
                           COUNT(DISTINCT farmacia) AS farmacias
                    FROM {qschema}.{qtabla}
                    WHERE fecha_dato <= :fd
                      AND fecha_vista >= :fd
                      AND precio IS NOT NULL
                      AND precio > 0
                    GROUP BY pais
                    ORDER BY COUNT(DISTINCT n_lista) DESC, pais
                    """
                ),
                {"fd": fd_indicadores},
            ).mappings().all()

        totales_row = conn.execute(
            text(
                f"""
                SELECT COUNT(DISTINCT producto_key) AS medicamentos,
                       COUNT(DISTINCT n_lista) AS principios,
                       COUNT(DISTINCT pais) AS paises,
                       COUNT(*) AS puntos
                FROM {qschema}.{qtabla}
                """
            )
        ).mappings().first()

    totales = {k: _jsonable(v) for k, v in dict(totales_row or {}).items()}
    totales["fechas"] = len(fechas)

    return {
        "ultima_fecha": _jsonable(fd_indicadores if fd_indicadores else ultima),
        "totales": totales,
        "meds_por_principio": [
            {
                "n_lista": _jsonable(r["n_lista"]),
                "label": r.get("medicamento_lista") or f"Principio #{r.get('n_lista')}",
                "valor": int(r.get("medicamentos") or 0),
            }
            for r in meds_por_principio
        ],
        "por_pais": [
            {
                "pais": r.get("pais"),
                "principios": int(r.get("principios") or 0),
                "medicamentos": int(r.get("medicamentos") or 0),
                "farmacias": int(r.get("farmacias") or 0),
            }
            for r in por_pais
        ],
        "puntos_por_fecha": [
            {
                "fecha": _jsonable(r.get("fecha_dato")),
                "puntos": int(r.get("puntos") or 0),
                "medicamentos": int(r.get("medicamentos") or 0),
                "principios": int(r.get("principios") or 0),
                "paises": int(r.get("paises") or 0),
            }
            for r in puntos_por_fecha
        ],
    }


ORDENES_BUSQUEDA = {
    "precio_asc": "precio_usd ASC, medicamento_lista ASC, pais ASC",
    "precio_desc": "precio_usd DESC, medicamento_lista ASC, pais ASC",
    "dispersion": "dispersion DESC, medicamento_lista ASC, precio_usd ASC",
    "paises": "paises_principio DESC, medicamento_lista ASC, precio_usd ASC",
    "nombre": "medicamento_lista ASC, precio_usd ASC, pais ASC",
}

# Comparación sin mayúsculas ni tildes para el texto libre.
_COLL = "COLLATE Latin1_General_CI_AI"


def _norm_lista(vals: Any) -> list[str]:
    out: list[str] = []
    for v in vals or []:
        s = str(v or "").strip()
        if s and s not in out:
            out.append(s)
    return out


def _sql_filtro_modo_precio(modo: str) -> str:
    """Excluye o aísla PVP al detalle / por unidad (***DET, 'detalle', etc.)."""
    m = str(modo or "paquete").strip().lower()
    blob = "UPPER(CONCAT(ISNULL(nombre_comercial, N''), N' ', ISNULL(presentacion, N'')))"
    es_unidad = (
        f"("
        f"{blob} LIKE N'%***DET%' OR "
        f"{blob} LIKE N'%DETALLE%' OR "
        f"{blob} LIKE N'%POR UNIDAD%' OR "
        f"{blob} LIKE N'%NO CAJA%'"
        f")"
    )
    if m in ("unidad", "detalle", "por_unidad"):
        return f"AND {es_unidad}"
    if m in ("todos", "all", "ambos"):
        return ""
    # paquete / empaque (default): sin precios al detalle
    return f"AND NOT {es_unidad}"


def _fila_es_precio_unidad(item: dict[str, Any]) -> bool:
    blob = f"{item.get('nombre_comercial') or ''} {item.get('presentacion') or ''}".lower()
    return any(
        x in blob
        for x in ("***det", "detalle", "por unidad", "no caja")
    )


def buscar_precios(
    *,
    q: str | None = None,
    n_lista: int | None = None,
    paises: list[str] | None = None,
    farmacias: list[str] | None = None,
    programas: list[str] | None = None,
    fecha: str | None = None,
    precio_min_usd: float | None = None,
    precio_max_usd: float | None = None,
    solo_min: bool = False,
    min_paises: int = 0,
    todas_presentaciones: bool = False,
    modo_precio: str = "paquete",
    orden: str = "precio_asc",
    limite: int = 300,
) -> dict[str, Any]:
    """Precios vigentes a una fecha, con el ranking entre países ya resuelto.

    La unidad de comparación es el principio activo: `producto_key` incluye la
    marca comercial y por eso nunca cruza fronteras. Por defecto cada país
    aporta una sola fila (su presentación más barata del principio), que es lo
    comparable; con `todas_presentaciones` se devuelven todas.

    ``modo_precio``:
      - ``paquete`` (default): excluye PVP al detalle / por unidad (***DET).
      - ``unidad``: solo esos precios al detalle.
      - ``todos``: ambos.

    El ranking (`pos_principio`, `min_usd_principio`, `dispersion`) se calcula
    antes de aplicar los filtros de país o farmacia, así «es el más barato»
    sigue significando lo mismo aunque la vista esté filtrada a un solo país.
    """
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()

    fechas = fechas_disponibles()
    fd = (str(fecha or "").strip()[:10]) or None
    if not fd:
        fd = fechas[-1] if fechas else None
    if not fd:
        return {
            "fecha": None,
            "fechas": [],
            "total": 0,
            "filas": [],
            "facetas": {"paises": [], "farmacias": [], "programas": []},
            "modo_precio": "paquete",
        }

    paises = _norm_lista(paises)
    farmacias = _norm_lista(farmacias)
    programas = _norm_lista(programas)
    lim = max(1, min(int(limite or 300), 2000))
    orden_sql = ORDENES_BUSQUEDA.get(str(orden or ""), ORDENES_BUSQUEDA["precio_asc"])
    modo = str(modo_precio or "paquete").strip().lower() or "paquete"
    if modo not in ("paquete", "unidad", "detalle", "por_unidad", "todos", "all", "ambos"):
        modo = "paquete"
    if modo in ("detalle", "por_unidad"):
        modo = "unidad"
    if modo in ("all", "ambos"):
        modo = "todos"

    params: dict[str, Any] = {"fd": fd, "lim": lim}
    binds: list[Any] = []

    # Filtros que solo eligen qué productos mirar: van antes del ranking.
    pre: list[str] = []
    filtro_modo = _sql_filtro_modo_precio(modo)
    if filtro_modo:
        pre.append(filtro_modo)
    if n_lista is not None:
        pre.append("AND n_lista = :n")
        params["n"] = int(n_lista)
    texto = str(q or "").strip()
    if texto:
        campos = ("medicamento_lista", "nombre_comercial", "concentracion", "presentacion")
        cond = " OR ".join(f"ISNULL({c}, N'') {_COLL} LIKE :q {_COLL}" for c in campos)
        pre.append(f"AND ({cond})")
        params["q"] = f"%{texto}%"
    if programas:
        pre.append("AND programa IN :programas")
        params["programas"] = programas
        binds.append(bindparam("programas", expanding=True))

    # Filtros de presentación: se aplican después, para no falsear el ranking.
    post: list[str] = []
    if paises:
        post.append("AND pais IN :paises")
        params["paises"] = paises
        binds.append(bindparam("paises", expanding=True))
    if farmacias:
        post.append("AND ISNULL(farmacia, N'') IN :farmacias")
        params["farmacias"] = farmacias
        binds.append(bindparam("farmacias", expanding=True))
    if precio_min_usd is not None:
        post.append("AND precio_usd >= :pmin")
        params["pmin"] = float(precio_min_usd)
    if precio_max_usd is not None:
        post.append("AND precio_usd <= :pmax")
        params["pmax"] = float(precio_max_usd)
    if int(min_paises or 0) > 1:
        post.append("AND paises_principio >= :minp")
        params["minp"] = int(min_paises)
    if solo_min:
        post.append("AND pos_principio = 1")

    # Sin agrupar, un país con varias presentaciones inunda el ranking del principio.
    filtro_pais = "" if todas_presentaciones else "WHERE pos_pais = 1"

    sql = f"""
WITH vig AS (
    SELECT n_lista, medicamento_lista, programa, producto_key, pais, farmacia,
           nombre_comercial, concentracion, presentacion,
           precio, moneda, precio_usd, fecha_dato, fecha_vista,
           ROW_NUMBER() OVER (
               PARTITION BY n_lista, pais, producto_key ORDER BY precio_usd ASC, fecha_dato DESC
           ) AS rn
    FROM {qschema}.{qtabla}
    WHERE fecha_dato <= :fd AND fecha_vista >= :fd
      AND precio_usd IS NOT NULL AND precio_usd > 0
      {" ".join(pre)}
),
por_pais AS (
    SELECT v.*,
           ROW_NUMBER() OVER (
               PARTITION BY n_lista, pais ORDER BY precio_usd, producto_key
           ) AS pos_pais,
           COUNT(*) OVER (PARTITION BY n_lista, pais) AS presentaciones_pais
    FROM vig v
    WHERE v.rn = 1
),
sel AS (
    SELECT * FROM por_pais
    {filtro_pais}
),
rankeado AS (
    SELECT s.*,
           MIN(precio_usd) OVER (PARTITION BY n_lista) AS min_usd_principio,
           MAX(precio_usd) OVER (PARTITION BY n_lista) AS max_usd_principio,
           -- SQL Server no admite COUNT(DISTINCT) como ventana; los dos DENSE_RANK sí.
           DENSE_RANK() OVER (PARTITION BY n_lista ORDER BY pais)
             + DENSE_RANK() OVER (PARTITION BY n_lista ORDER BY pais DESC) - 1 AS paises_principio,
           ROW_NUMBER() OVER (PARTITION BY n_lista ORDER BY precio_usd, pais) AS pos_principio
    FROM sel s
),
listo AS (
    SELECT *,
           CASE WHEN min_usd_principio > 0
                THEN max_usd_principio / min_usd_principio END AS dispersion
    FROM rankeado
)
SELECT TOP (:lim) *, COUNT(*) OVER () AS total_filas
FROM listo
WHERE 1 = 1
  {" ".join(post)}
ORDER BY {orden_sql}
"""
    stmt = text(sql)
    if binds:
        stmt = stmt.bindparams(*binds)

    facetas_sql = f"""
SELECT DISTINCT pais, ISNULL(farmacia, N'') AS farmacia, ISNULL(programa, N'') AS programa
FROM {qschema}.{qtabla}
WHERE fecha_dato <= :fd AND fecha_vista >= :fd
  AND precio_usd IS NOT NULL AND precio_usd > 0
"""
    with engine().connect() as conn:
        rows = conn.execute(stmt, params).mappings().all()
        fac = conn.execute(text(facetas_sql), {"fd": fd}).mappings().all()

    filas: list[dict[str, Any]] = []
    total = 0
    for r in rows:
        item = {k: _jsonable(v) for k, v in dict(r).items()}
        total = int(item.pop("total_filas", 0) or 0)
        item.pop("rn", None)
        item["producto_label"] = producto_label(item)
        minimo = item.get("min_usd_principio")
        precio_usd = item.get("precio_usd")
        item["es_min"] = int(item.get("pos_principio") or 0) == 1
        item["es_precio_unidad"] = _fila_es_precio_unidad(item)
        item["sobrecosto_pct"] = (
            round((precio_usd / minimo - 1) * 100, 1)
            if minimo and precio_usd and minimo > 0
            else None
        )
        filas.append(item)

    return {
        "fecha": fd,
        "fechas": fechas,
        "total": total,
        "filas": filas,
        "truncado": total > len(filas),
        "modo_precio": modo,
        "facetas": {
            "paises": sorted({str(r["pais"]) for r in fac if r["pais"]}),
            "farmacias": sorted({str(r["farmacia"]) for r in fac if r["farmacia"]}),
            "programas": sorted({str(r["programa"]) for r in fac if r["programa"]}),
        },
    }
