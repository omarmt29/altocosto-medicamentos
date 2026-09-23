"""Tabla resumen FDA por principio activo (indicaciones, genérico/biosimilar, TA)."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import text

from db import engine, resumen_config

TABLA = "medicamentos_fda_principio_info"

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
        indicaciones_uso NVARCHAR(MAX) NULL,
        fuente_indicaciones NVARCHAR(500) NULL,
        es_biologico BIT NOT NULL CONSTRAINT DF_{df}_bio DEFAULT 0,
        tiene_referencia BIT NOT NULL CONSTRAINT DF_{df}_ref DEFAULT 0,
        tiene_biosimilar BIT NOT NULL CONSTRAINT DF_{df}_bs DEFAULT 0,
        tiene_intercambiable BIT NOT NULL CONSTRAINT DF_{df}_ic DEFAULT 0,
        tiene_generico BIT NOT NULL CONSTRAINT DF_{df}_gen DEFAULT 0,
        resumen_clase NVARCHAR(200) NULL,
        exclusividad_proxima NVARCHAR(80) NULL,
        patente_proxima NVARCHAR(80) NULL,
        tentative_json NVARCHAR(MAX) NULL,
        patentes_json NVARCHAR(MAX) NULL,
        exclusividades_json NVARCHAR(MAX) NULL,
        productos_fda_json NVARCHAR(MAX) NULL,
        fuentes_json NVARCHAR(MAX) NULL,
        fuente_url NVARCHAR(500) NULL,
        periodo_etiqueta NVARCHAR(40) NULL,
        fecha_dato DATE NOT NULL,
        fecha_registro DATETIME NOT NULL CONSTRAINT DF_{df}_reg DEFAULT GETDATE(),
        fecha_actualizacion DATETIME NOT NULL CONSTRAINT DF_{df}_upd DEFAULT GETDATE(),
        CONSTRAINT UQ_{df} UNIQUE (fecha_dato, n_lista)
    );
END
"""

ALTERS = [
    "IF COL_LENGTH(N'{full}', 'patentes_json') IS NULL ALTER TABLE {qschema}.{qtabla} ADD patentes_json NVARCHAR(MAX) NULL;",
    "IF COL_LENGTH(N'{full}', 'exclusividades_json') IS NULL ALTER TABLE {qschema}.{qtabla} ADD exclusividades_json NVARCHAR(MAX) NULL;",
    "IF COL_LENGTH(N'{full}', 'productos_fda_json') IS NULL ALTER TABLE {qschema}.{qtabla} ADD productos_fda_json NVARCHAR(MAX) NULL;",
    "IF COL_LENGTH(N'{full}', 'fuentes_json') IS NULL ALTER TABLE {qschema}.{qtabla} ADD fuentes_json NVARCHAR(MAX) NULL;",
]

MERGE_SQL = """
MERGE {qschema}.{qtabla} AS t
USING (SELECT
    :n_lista AS n_lista,
    :medicamento_lista AS medicamento_lista,
    :programa AS programa,
    :indicaciones_uso AS indicaciones_uso,
    :fuente_indicaciones AS fuente_indicaciones,
    :es_biologico AS es_biologico,
    :tiene_referencia AS tiene_referencia,
    :tiene_biosimilar AS tiene_biosimilar,
    :tiene_intercambiable AS tiene_intercambiable,
    :tiene_generico AS tiene_generico,
    :resumen_clase AS resumen_clase,
    :exclusividad_proxima AS exclusividad_proxima,
    :patente_proxima AS patente_proxima,
    :tentative_json AS tentative_json,
    :patentes_json AS patentes_json,
    :exclusividades_json AS exclusividades_json,
    :productos_fda_json AS productos_fda_json,
    :fuentes_json AS fuentes_json,
    :fuente_url AS fuente_url,
    :periodo_etiqueta AS periodo_etiqueta,
    :fecha_dato AS fecha_dato
) AS s
ON t.fecha_dato = s.fecha_dato AND t.n_lista = s.n_lista
WHEN MATCHED THEN UPDATE SET
    medicamento_lista = s.medicamento_lista,
    programa = s.programa,
    indicaciones_uso = s.indicaciones_uso,
    fuente_indicaciones = s.fuente_indicaciones,
    es_biologico = s.es_biologico,
    tiene_referencia = s.tiene_referencia,
    tiene_biosimilar = s.tiene_biosimilar,
    tiene_intercambiable = s.tiene_intercambiable,
    tiene_generico = s.tiene_generico,
    resumen_clase = s.resumen_clase,
    exclusividad_proxima = s.exclusividad_proxima,
    patente_proxima = s.patente_proxima,
    tentative_json = s.tentative_json,
    patentes_json = s.patentes_json,
    exclusividades_json = s.exclusividades_json,
    productos_fda_json = s.productos_fda_json,
    fuentes_json = s.fuentes_json,
    fuente_url = s.fuente_url,
    periodo_etiqueta = s.periodo_etiqueta,
    fecha_actualizacion = GETDATE()
WHEN NOT MATCHED THEN INSERT (
    n_lista, medicamento_lista, programa, indicaciones_uso, fuente_indicaciones,
    es_biologico, tiene_referencia, tiene_biosimilar, tiene_intercambiable, tiene_generico,
    resumen_clase, exclusividad_proxima, patente_proxima, tentative_json,
    patentes_json, exclusividades_json, productos_fda_json, fuentes_json,
    fuente_url, periodo_etiqueta, fecha_dato, fecha_registro, fecha_actualizacion
) VALUES (
    s.n_lista, s.medicamento_lista, s.programa, s.indicaciones_uso, s.fuente_indicaciones,
    s.es_biologico, s.tiene_referencia, s.tiene_biosimilar, s.tiene_intercambiable, s.tiene_generico,
    s.resumen_clase, s.exclusividad_proxima, s.patente_proxima, s.tentative_json,
    s.patentes_json, s.exclusividades_json, s.productos_fda_json, s.fuentes_json,
    s.fuente_url, s.periodo_etiqueta, s.fecha_dato, GETDATE(), GETDATE()
);
"""


def _ids() -> tuple[str, str, str, str]:
    schema = resumen_config()["schema"]
    return f"[{schema}]", f"[{TABLA}]", f"{schema}.{TABLA}", "mac_fi"


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


def _jsonable(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat(timespec="seconds")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, (bytes, bytearray)):
        return bool(v)
    return v


def guardar_info(fila: dict[str, Any]) -> None:
    qschema, qtabla, _full, _df = _ids()
    sql = MERGE_SQL.replace("{qschema}", qschema).replace("{qtabla}", qtabla)
    payload = dict(fila)
    for key in (
        "tentative_json",
        "patentes_json",
        "exclusividades_json",
        "productos_fda_json",
        "fuentes_json",
    ):
        val = payload.get(key)
        if val is not None and not isinstance(val, str):
            payload[key] = json.dumps(val, ensure_ascii=False)
        elif key not in payload:
            payload[key] = None
    fd = payload.get("fecha_dato")
    if isinstance(fd, datetime):
        payload["fecha_dato"] = fd.date()
    elif isinstance(fd, str):
        payload["fecha_dato"] = date.fromisoformat(fd[:10])
    for bit in (
        "es_biologico",
        "tiene_referencia",
        "tiene_biosimilar",
        "tiene_intercambiable",
        "tiene_generico",
    ):
        payload[bit] = 1 if payload.get(bit) else 0
    with engine().begin() as conn:
        conn.execute(text(sql), payload)


def obtener_info(n_lista: int, fecha_dato: str | date | None = None) -> dict[str, Any] | None:
    qschema, qtabla, _full, _df = _ids()
    params: dict[str, Any] = {"n": int(n_lista)}
    if fecha_dato:
        params["fd"] = (
            fecha_dato
            if isinstance(fecha_dato, date)
            else date.fromisoformat(str(fecha_dato)[:10])
        )
        where_fd = "fecha_dato = :fd"
    else:
        where_fd = (
            f"fecha_dato = (SELECT MAX(fecha_dato) FROM {qschema}.{qtabla} WHERE n_lista = :n)"
        )
    sql = (
        f"SELECT TOP 1 * FROM {qschema}.{qtabla} "
        f"WHERE n_lista = :n AND {where_fd}"
    )
    with engine().connect() as conn:
        row = conn.execute(text(sql), params).mappings().first()
    if not row:
        return None
    out = {k: _jsonable(v) for k, v in dict(row).items()}
    for key, dest in (
        ("tentative_json", "tentative"),
        ("patentes_json", "patentes"),
        ("exclusividades_json", "exclusividades"),
        ("productos_fda_json", "productos_fda"),
        ("fuentes_json", "fuentes"),
    ):
        raw = out.get(key)
        if isinstance(raw, str) and raw.strip():
            try:
                out[dest] = json.loads(raw)
            except json.JSONDecodeError:
                out[dest] = [] if dest != "fuentes" else []
        else:
            out[dest] = [] if dest != "fuentes" else []

    # Recuperar PDF / openFDA desde el listado de fuentes guardado.
    for f in out.get("fuentes") or []:
        if not isinstance(f, dict):
            continue
        nombre = str(f.get("nombre") or "").lower()
        url = str(f.get("url") or "").strip()
        if not url:
            continue
        if "drugsatfda_docs/label" in url.lower() and not out.get("fuente_indicaciones_pdf"):
            out["fuente_indicaciones_pdf"] = url
        if (
            "pdf" in nombre
            and "dailymed" in url
            and not out.get("fuente_indicaciones_pdf")
        ):
            out["fuente_indicaciones_pdf"] = url
        if "openfda" in nombre and "label" in nombre and "api.fda.gov" in url:
            out["fuente_indicaciones_api"] = url
    # Si hay Drugs@FDA y DailyMed, preferir Drugs@FDA.
    for f in out.get("fuentes") or []:
        if not isinstance(f, dict):
            continue
        url = str(f.get("url") or "").strip()
        if "drugsatfda_docs/label" in url.lower():
            out["fuente_indicaciones_pdf"] = url
            break

    try:
        from scrapper.fda_openfda_info import resolver_fuentes_indicaciones

        out = resolver_fuentes_indicaciones(out)
    except Exception:
        pass
    return out
