"""Tabla P_aguila.medicamentos_fda_purple_book (snapshots mensuales por principio activo)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

from sqlalchemy import text

from db import engine, resumen_config

TABLA = "medicamentos_fda_purple_book"

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
        cambio_nr_u NVARCHAR(10) NULL,
        solicitante NVARCHAR(300) NULL,
        bla_number NVARCHAR(40) NOT NULL,
        nombre_comercial NVARCHAR(500) NULL,
        nombre_propio NVARCHAR(500) NULL,
        tipo_licencia NVARCHAR(80) NULL,
        concentracion NVARCHAR(120) NULL,
        forma_dosificacion NVARCHAR(120) NULL,
        via_administracion NVARCHAR(120) NULL,
        presentacion NVARCHAR(200) NULL,
        estado_marketing NVARCHAR(40) NULL,
        licensure NVARCHAR(40) NULL,
        fecha_aprobacion NVARCHAR(80) NULL,
        fecha_intercambio NVARCHAR(80) NULL,
        ref_nombre_propio NVARCHAR(500) NULL,
        ref_nombre_comercial NVARCHAR(500) NULL,
        supplement_number NVARCHAR(40) NULL,
        submission_type NVARCHAR(80) NULL,
        license_number NVARCHAR(40) NULL,
        product_number NVARCHAR(40) NOT NULL,
        center NVARCHAR(40) NULL,
        fecha_primera_licencia NVARCHAR(80) NULL,
        exclusividad_expira NVARCHAR(80) NULL,
        exclusividad_intercambio_expira NVARCHAR(80) NULL,
        exclusividad_ref_expira NVARCHAR(80) NULL,
        exclusividad_orphan_expira NVARCHAR(80) NULL,
        patent_list NVARCHAR(20) NULL,
        fuente_url NVARCHAR(500) NULL,
        periodo_etiqueta NVARCHAR(40) NULL,
        fecha_dato DATE NOT NULL,
        fecha_registro DATETIME NOT NULL CONSTRAINT DF_{df}_reg DEFAULT GETDATE(),
        fecha_actualizacion DATETIME NOT NULL CONSTRAINT DF_{df}_upd DEFAULT GETDATE(),
        CONSTRAINT UQ_{df} UNIQUE (
            fecha_dato, n_lista, bla_number, product_number, concentracion, presentacion
        )
    );
END
"""

ALTERS = [
    "IF COL_LENGTH(N'{full}', 'es_biosimilar') IS NULL ALTER TABLE {qschema}.{qtabla} ADD es_biosimilar BIT NULL;",
    "IF COL_LENGTH(N'{full}', 'es_intercambiable') IS NULL ALTER TABLE {qschema}.{qtabla} ADD es_intercambiable BIT NULL;",
    "IF COL_LENGTH(N'{full}', 'clase_producto') IS NULL ALTER TABLE {qschema}.{qtabla} ADD clase_producto NVARCHAR(40) NULL;",
]

MERGE_SQL = """
MERGE {qschema}.{qtabla} AS t
USING (SELECT
    :n_lista AS n_lista,
    :medicamento_lista AS medicamento_lista,
    :programa AS programa,
    :cambio_nr_u AS cambio_nr_u,
    :solicitante AS solicitante,
    :bla_number AS bla_number,
    :nombre_comercial AS nombre_comercial,
    :nombre_propio AS nombre_propio,
    :tipo_licencia AS tipo_licencia,
    :concentracion AS concentracion,
    :forma_dosificacion AS forma_dosificacion,
    :via_administracion AS via_administracion,
    :presentacion AS presentacion,
    :estado_marketing AS estado_marketing,
    :licensure AS licensure,
    :fecha_aprobacion AS fecha_aprobacion,
    :fecha_intercambio AS fecha_intercambio,
    :ref_nombre_propio AS ref_nombre_propio,
    :ref_nombre_comercial AS ref_nombre_comercial,
    :supplement_number AS supplement_number,
    :submission_type AS submission_type,
    :license_number AS license_number,
    :product_number AS product_number,
    :center AS center,
    :fecha_primera_licencia AS fecha_primera_licencia,
    :exclusividad_expira AS exclusividad_expira,
    :exclusividad_intercambio_expira AS exclusividad_intercambio_expira,
    :exclusividad_ref_expira AS exclusividad_ref_expira,
    :exclusividad_orphan_expira AS exclusividad_orphan_expira,
    :patent_list AS patent_list,
    :es_biosimilar AS es_biosimilar,
    :es_intercambiable AS es_intercambiable,
    :clase_producto AS clase_producto,
    :fuente_url AS fuente_url,
    :periodo_etiqueta AS periodo_etiqueta,
    :fecha_dato AS fecha_dato
) AS s
ON t.fecha_dato = s.fecha_dato
   AND t.n_lista = s.n_lista
   AND t.bla_number = s.bla_number
   AND t.product_number = s.product_number
   AND ISNULL(t.concentracion, N'') = ISNULL(s.concentracion, N'')
   AND ISNULL(t.presentacion, N'') = ISNULL(s.presentacion, N'')
WHEN MATCHED THEN UPDATE SET
    medicamento_lista = s.medicamento_lista,
    programa = s.programa,
    cambio_nr_u = s.cambio_nr_u,
    solicitante = s.solicitante,
    nombre_comercial = s.nombre_comercial,
    nombre_propio = s.nombre_propio,
    tipo_licencia = s.tipo_licencia,
    forma_dosificacion = s.forma_dosificacion,
    via_administracion = s.via_administracion,
    estado_marketing = s.estado_marketing,
    licensure = s.licensure,
    fecha_aprobacion = s.fecha_aprobacion,
    fecha_intercambio = s.fecha_intercambio,
    ref_nombre_propio = s.ref_nombre_propio,
    ref_nombre_comercial = s.ref_nombre_comercial,
    supplement_number = s.supplement_number,
    submission_type = s.submission_type,
    license_number = s.license_number,
    center = s.center,
    fecha_primera_licencia = s.fecha_primera_licencia,
    exclusividad_expira = s.exclusividad_expira,
    exclusividad_intercambio_expira = s.exclusividad_intercambio_expira,
    exclusividad_ref_expira = s.exclusividad_ref_expira,
    exclusividad_orphan_expira = s.exclusividad_orphan_expira,
    patent_list = s.patent_list,
    es_biosimilar = s.es_biosimilar,
    es_intercambiable = s.es_intercambiable,
    clase_producto = s.clase_producto,
    fuente_url = s.fuente_url,
    periodo_etiqueta = s.periodo_etiqueta,
    fecha_actualizacion = GETDATE()
WHEN NOT MATCHED THEN INSERT (
    n_lista, medicamento_lista, programa, cambio_nr_u, solicitante,
    bla_number, nombre_comercial, nombre_propio, tipo_licencia,
    concentracion, forma_dosificacion, via_administracion, presentacion,
    estado_marketing, licensure, fecha_aprobacion, fecha_intercambio,
    ref_nombre_propio, ref_nombre_comercial, supplement_number, submission_type,
    license_number, product_number, center, fecha_primera_licencia,
    exclusividad_expira, exclusividad_intercambio_expira, exclusividad_ref_expira,
    exclusividad_orphan_expira, patent_list, es_biosimilar, es_intercambiable,
    clase_producto, fuente_url, periodo_etiqueta,
    fecha_dato, fecha_registro, fecha_actualizacion
) VALUES (
    s.n_lista, s.medicamento_lista, s.programa, s.cambio_nr_u, s.solicitante,
    s.bla_number, s.nombre_comercial, s.nombre_propio, s.tipo_licencia,
    s.concentracion, s.forma_dosificacion, s.via_administracion, s.presentacion,
    s.estado_marketing, s.licensure, s.fecha_aprobacion, s.fecha_intercambio,
    s.ref_nombre_propio, s.ref_nombre_comercial, s.supplement_number, s.submission_type,
    s.license_number, s.product_number, s.center, s.fecha_primera_licencia,
    s.exclusividad_expira, s.exclusividad_intercambio_expira, s.exclusividad_ref_expira,
    s.exclusividad_orphan_expira, s.patent_list, s.es_biosimilar, s.es_intercambiable,
    s.clase_producto, s.fuente_url, s.periodo_etiqueta,
    s.fecha_dato, GETDATE(), GETDATE()
);
"""


def _ids() -> tuple[str, str, str, str]:
    schema = resumen_config()["schema"]
    qschema = f"[{schema}]"
    qtabla = f"[{TABLA}]"
    full = f"{schema}.{TABLA}"
    df = "mac_pb"
    return qschema, qtabla, full, df


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
        for alter in ALTERS:
            conn.execute(
                text(
                    alter.replace("{qschema}", qschema)
                    .replace("{qtabla}", qtabla)
                    .replace("{full}", full)
                )
            )
    return full


def _clip(v: Any, n: int) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.upper() in ("N/A", "NA", "-"):
        return None
    return s[:n]


def _norm_fila(fila: dict[str, Any]) -> dict[str, Any]:
    out = dict(fila)
    out["n_lista"] = int(out["n_lista"])
    out["medicamento_lista"] = _clip(out.get("medicamento_lista"), 300) or ""
    out["programa"] = _clip(out.get("programa"), 40)
    out["cambio_nr_u"] = _clip(out.get("cambio_nr_u"), 10)
    out["solicitante"] = _clip(out.get("solicitante"), 300)
    out["bla_number"] = _clip(out.get("bla_number"), 40) or ""
    out["nombre_comercial"] = _clip(out.get("nombre_comercial"), 500)
    out["nombre_propio"] = _clip(out.get("nombre_propio"), 500)
    out["tipo_licencia"] = _clip(out.get("tipo_licencia"), 80)
    out["concentracion"] = _clip(out.get("concentracion"), 120) or ""
    out["forma_dosificacion"] = _clip(out.get("forma_dosificacion"), 120)
    out["via_administracion"] = _clip(out.get("via_administracion"), 120)
    out["presentacion"] = _clip(out.get("presentacion"), 200) or ""
    out["estado_marketing"] = _clip(out.get("estado_marketing"), 40)
    out["licensure"] = _clip(out.get("licensure"), 40)
    out["fecha_aprobacion"] = _clip(out.get("fecha_aprobacion"), 80)
    out["fecha_intercambio"] = _clip(out.get("fecha_intercambio"), 80)
    out["ref_nombre_propio"] = _clip(out.get("ref_nombre_propio"), 500)
    out["ref_nombre_comercial"] = _clip(out.get("ref_nombre_comercial"), 500)
    out["supplement_number"] = _clip(out.get("supplement_number"), 40)
    out["submission_type"] = _clip(out.get("submission_type"), 80)
    out["license_number"] = _clip(out.get("license_number"), 40)
    out["product_number"] = _clip(out.get("product_number"), 40) or "0"
    out["center"] = _clip(out.get("center"), 40)
    out["fecha_primera_licencia"] = _clip(out.get("fecha_primera_licencia"), 80)
    out["exclusividad_expira"] = _clip(out.get("exclusividad_expira"), 80)
    out["exclusividad_intercambio_expira"] = _clip(
        out.get("exclusividad_intercambio_expira"), 80
    )
    out["exclusividad_ref_expira"] = _clip(out.get("exclusividad_ref_expira"), 80)
    out["exclusividad_orphan_expira"] = _clip(out.get("exclusividad_orphan_expira"), 80)
    out["patent_list"] = _clip(out.get("patent_list"), 20)
    clase = _clip(out.get("clase_producto"), 40)
    if not clase:
        tipo = (out.get("tipo_licencia") or "").lower()
        inter = bool(out.get("fecha_intercambio"))
        if "interchangeable" in tipo or inter:
            clase = "intercambiable"
        elif "biosimilar" in tipo or "351(k)" in tipo:
            clase = "biosimilar"
        elif "351(a)" in tipo:
            clase = "referencia"
        else:
            clase = "biologico"
    out["clase_producto"] = clase
    out["es_biosimilar"] = 1 if (
        out.get("es_biosimilar")
        if out.get("es_biosimilar") is not None
        else clase in ("biosimilar", "intercambiable")
    ) else 0
    out["es_intercambiable"] = 1 if (
        out.get("es_intercambiable")
        if out.get("es_intercambiable") is not None
        else clase == "intercambiable"
    ) else 0
    out["fuente_url"] = _clip(out.get("fuente_url"), 500)
    out["periodo_etiqueta"] = _clip(out.get("periodo_etiqueta"), 40)
    fd = out.get("fecha_dato")
    if isinstance(fd, datetime):
        out["fecha_dato"] = fd.date()
    elif isinstance(fd, str):
        out["fecha_dato"] = date.fromisoformat(fd[:10])
    return out


def guardar_filas(filas: Iterable[dict[str, Any]]) -> dict[str, int]:
    qschema, qtabla, full, _df = _ids()
    sql = MERGE_SQL.replace("{qschema}", qschema).replace("{qtabla}", qtabla)
    lote = [_norm_fila(f) for f in filas]
    n = 0
    # Commits por lote para no dejar una sola transacción enorme abierta.
    with engine().begin() as conn:
        for i in range(0, len(lote), 50):
            chunk = lote[i : i + 50]
            for fila in chunk:
                conn.execute(text(sql), fila)
                n += 1
        total = conn.execute(text(f"SELECT COUNT(*) FROM {qschema}.{qtabla}")).scalar_one()
    return {"upserts": n, "total_tabla": int(total or 0), "tabla": full}


def _jsonable(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat(timespec="seconds")
    if isinstance(v, date):
        return v.isoformat()
    return v


def listar_por_n(
    n_lista: int,
    fecha_dato: str | date | None = None,
    solo_ultimo: bool = True,
) -> list[dict[str, Any]]:
    qschema, qtabla, _full, _df = _ids()
    params: dict[str, Any] = {"n": int(n_lista)}
    where = ["n_lista = :n"]
    if fecha_dato:
        if isinstance(fecha_dato, date):
            params["fd"] = fecha_dato
        else:
            params["fd"] = date.fromisoformat(str(fecha_dato)[:10])
        where.append("fecha_dato = :fd")
    elif solo_ultimo:
        where.append(
            "fecha_dato = (SELECT MAX(fecha_dato) FROM {qschema}.{qtabla} WHERE n_lista = :n)".format(
                qschema=qschema, qtabla=qtabla
            )
        )
    sql = (
        f"SELECT id, n_lista, medicamento_lista, programa, cambio_nr_u, solicitante, "
        f"bla_number, nombre_comercial, nombre_propio, tipo_licencia, concentracion, "
        f"forma_dosificacion, via_administracion, presentacion, estado_marketing, "
        f"licensure, fecha_aprobacion, fecha_intercambio, ref_nombre_propio, "
        f"ref_nombre_comercial, supplement_number, submission_type, license_number, "
        f"product_number, center, fecha_primera_licencia, exclusividad_expira, "
        f"exclusividad_intercambio_expira, exclusividad_ref_expira, "
        f"exclusividad_orphan_expira, patent_list, es_biosimilar, es_intercambiable, "
        f"clase_producto, fuente_url, periodo_etiqueta, "
        f"fecha_dato, fecha_registro, fecha_actualizacion "
        f"FROM {qschema}.{qtabla} "
        f"WHERE {' AND '.join(where)} "
        f"ORDER BY nombre_propio, nombre_comercial, bla_number, product_number"
    )
    with engine().connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    out = [{k: _jsonable(v) for k, v in dict(r).items()} for r in rows]
    # Defensa: coformulaciones "X and …" no bajo principios únicos de la lista.
    filtradas: list[dict[str, Any]] = []
    for f in out:
        lista_combo = "/" in str(f.get("medicamento_lista") or "")
        pn = str(f.get("nombre_propio") or "").lower()
        combo = " and " in pn or ";" in pn
        if not lista_combo and combo:
            continue
        filtradas.append(f)
    return filtradas


def purgar_combinados_en_principios_unicos() -> int:
    """Borra Purple Book 'X and …' asociados a principios de lista sin '/'."""
    qschema, qtabla, _full, _df = _ids()
    sql = f"""
    DELETE FROM {qschema}.{qtabla}
    WHERE medicamento_lista NOT LIKE N'%/%'
      AND (
            CHARINDEX(N' and ', LOWER(ISNULL(nombre_propio, N''))) > 0
         OR CHARINDEX(N';', ISNULL(nombre_propio, N'')) > 0
      )
    """
    with engine().begin() as conn:
        res = conn.execute(text(sql))
        return int(res.rowcount or 0)


def periodos_disponibles(n_lista: int | None = None) -> list[dict[str, Any]]:
    qschema, qtabla, _full, _df = _ids()
    params: dict[str, Any] = {}
    where = ""
    if n_lista is not None:
        where = "WHERE n_lista = :n"
        params["n"] = int(n_lista)
    sql = (
        f"SELECT fecha_dato, MAX(periodo_etiqueta) AS periodo_etiqueta, COUNT(*) AS filas "
        f"FROM {qschema}.{qtabla} {where} "
        f"GROUP BY fecha_dato ORDER BY fecha_dato DESC"
    )
    with engine().connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [{k: _jsonable(v) for k, v in dict(r).items()} for r in rows]


def resumen_cobertura(fecha_dato: str | date | None = None) -> dict[str, Any]:
    qschema, qtabla, full, _df = _ids()
    params: dict[str, Any] = {}
    fd_filter = ""
    if fecha_dato:
        params["fd"] = (
            fecha_dato
            if isinstance(fecha_dato, date)
            else date.fromisoformat(str(fecha_dato)[:10])
        )
        fd_filter = "WHERE fecha_dato = :fd"
    else:
        fd_filter = (
            f"WHERE fecha_dato = (SELECT MAX(fecha_dato) FROM {qschema}.{qtabla})"
        )
    sql = (
        f"SELECT COUNT(*) AS filas, COUNT(DISTINCT n_lista) AS moleculas, "
        f"MAX(fecha_dato) AS fecha_dato, MAX(periodo_etiqueta) AS periodo_etiqueta "
        f"FROM {qschema}.{qtabla} {fd_filter}"
    )
    with engine().connect() as conn:
        row = conn.execute(text(sql), params).mappings().first()
    return {
        "tabla": full,
        "filas": int((row or {}).get("filas") or 0),
        "moleculas": int((row or {}).get("moleculas") or 0),
        "fecha_dato": _jsonable((row or {}).get("fecha_dato")),
        "periodo_etiqueta": (row or {}).get("periodo_etiqueta"),
    }
