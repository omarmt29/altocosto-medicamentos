"""Tabla P_aguila.medicamentos_ema_medicines (snapshot EMA por principio activo)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import text

from db import engine, resumen_config

TABLA = "medicamentos_ema_medicines"

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
        categoria NVARCHAR(40) NULL,
        nombre_medicamento NVARCHAR(500) NOT NULL,
        ema_product_number NVARCHAR(80) NOT NULL,
        medicine_status NVARCHAR(80) NULL,
        opinion_status NVARCHAR(120) NULL,
        inn NVARCHAR(500) NULL,
        active_substance NVARCHAR(500) NULL,
        therapeutic_area NVARCHAR(1000) NULL,
        atc_code NVARCHAR(80) NULL,
        pharmacotherapeutic_group NVARCHAR(300) NULL,
        therapeutic_indication NVARCHAR(MAX) NULL,
        es_biosimilar BIT NOT NULL CONSTRAINT DF_{df}_bs DEFAULT 0,
        es_generic BIT NOT NULL CONSTRAINT DF_{df}_gen DEFAULT 0,
        es_orphan BIT NOT NULL CONSTRAINT DF_{df}_orp DEFAULT 0,
        es_advanced_therapy BIT NOT NULL CONSTRAINT DF_{df}_at DEFAULT 0,
        es_conditional BIT NOT NULL CONSTRAINT DF_{df}_cond DEFAULT 0,
        additional_monitoring BIT NOT NULL CONSTRAINT DF_{df}_am DEFAULT 0,
        patient_safety BIT NOT NULL CONSTRAINT DF_{df}_ps DEFAULT 0,
        mah NVARCHAR(500) NULL,
        marketing_authorisation_date NVARCHAR(40) NULL,
        ec_decision_date NVARCHAR(40) NULL,
        first_published_date NVARCHAR(40) NULL,
        last_updated_date NVARCHAR(40) NULL,
        medicine_url NVARCHAR(500) NULL,
        fuente_url NVARCHAR(500) NULL,
        periodo_etiqueta NVARCHAR(40) NULL,
        fecha_dato DATE NOT NULL,
        fecha_registro DATETIME NOT NULL CONSTRAINT DF_{df}_reg DEFAULT GETDATE(),
        fecha_actualizacion DATETIME NOT NULL CONSTRAINT DF_{df}_upd DEFAULT GETDATE(),
        CONSTRAINT UQ_{df} UNIQUE (fecha_dato, n_lista, ema_product_number, nombre_medicamento)
    );
END
"""

MERGE_SQL = """
MERGE {qschema}.{qtabla} AS t
USING (SELECT
    :n_lista AS n_lista,
    :medicamento_lista AS medicamento_lista,
    :programa AS programa,
    :categoria AS categoria,
    :nombre_medicamento AS nombre_medicamento,
    :ema_product_number AS ema_product_number,
    :medicine_status AS medicine_status,
    :opinion_status AS opinion_status,
    :inn AS inn,
    :active_substance AS active_substance,
    :therapeutic_area AS therapeutic_area,
    :atc_code AS atc_code,
    :pharmacotherapeutic_group AS pharmacotherapeutic_group,
    :therapeutic_indication AS therapeutic_indication,
    :es_biosimilar AS es_biosimilar,
    :es_generic AS es_generic,
    :es_orphan AS es_orphan,
    :es_advanced_therapy AS es_advanced_therapy,
    :es_conditional AS es_conditional,
    :additional_monitoring AS additional_monitoring,
    :patient_safety AS patient_safety,
    :mah AS mah,
    :marketing_authorisation_date AS marketing_authorisation_date,
    :ec_decision_date AS ec_decision_date,
    :first_published_date AS first_published_date,
    :last_updated_date AS last_updated_date,
    :medicine_url AS medicine_url,
    :fuente_url AS fuente_url,
    :periodo_etiqueta AS periodo_etiqueta,
    :fecha_dato AS fecha_dato
) AS s
ON t.fecha_dato = s.fecha_dato
   AND t.n_lista = s.n_lista
   AND t.ema_product_number = s.ema_product_number
   AND t.nombre_medicamento = s.nombre_medicamento
WHEN MATCHED THEN UPDATE SET
    medicamento_lista = s.medicamento_lista,
    programa = s.programa,
    categoria = s.categoria,
    medicine_status = s.medicine_status,
    opinion_status = s.opinion_status,
    inn = s.inn,
    active_substance = s.active_substance,
    therapeutic_area = s.therapeutic_area,
    atc_code = s.atc_code,
    pharmacotherapeutic_group = s.pharmacotherapeutic_group,
    therapeutic_indication = s.therapeutic_indication,
    es_biosimilar = s.es_biosimilar,
    es_generic = s.es_generic,
    es_orphan = s.es_orphan,
    es_advanced_therapy = s.es_advanced_therapy,
    es_conditional = s.es_conditional,
    additional_monitoring = s.additional_monitoring,
    patient_safety = s.patient_safety,
    mah = s.mah,
    marketing_authorisation_date = s.marketing_authorisation_date,
    ec_decision_date = s.ec_decision_date,
    first_published_date = s.first_published_date,
    last_updated_date = s.last_updated_date,
    medicine_url = s.medicine_url,
    fuente_url = s.fuente_url,
    periodo_etiqueta = s.periodo_etiqueta,
    fecha_actualizacion = GETDATE()
WHEN NOT MATCHED THEN INSERT (
    n_lista, medicamento_lista, programa, categoria, nombre_medicamento, ema_product_number,
    medicine_status, opinion_status, inn, active_substance, therapeutic_area, atc_code,
    pharmacotherapeutic_group, therapeutic_indication,
    es_biosimilar, es_generic, es_orphan, es_advanced_therapy, es_conditional,
    additional_monitoring, patient_safety, mah, marketing_authorisation_date, ec_decision_date,
    first_published_date, last_updated_date, medicine_url, fuente_url, periodo_etiqueta,
    fecha_dato, fecha_registro, fecha_actualizacion
) VALUES (
    s.n_lista, s.medicamento_lista, s.programa, s.categoria, s.nombre_medicamento, s.ema_product_number,
    s.medicine_status, s.opinion_status, s.inn, s.active_substance, s.therapeutic_area, s.atc_code,
    s.pharmacotherapeutic_group, s.therapeutic_indication,
    s.es_biosimilar, s.es_generic, s.es_orphan, s.es_advanced_therapy, s.es_conditional,
    s.additional_monitoring, s.patient_safety, s.mah, s.marketing_authorisation_date, s.ec_decision_date,
    s.first_published_date, s.last_updated_date, s.medicine_url, s.fuente_url, s.periodo_etiqueta,
    s.fecha_dato, GETDATE(), GETDATE()
);
"""


def _ids() -> tuple[str, str, str, str]:
    schema = resumen_config()["schema"]
    return f"[{schema}]", f"[{TABLA}]", f"{schema}.{TABLA}", "mac_ema"


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
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat(timespec="seconds")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, (bytes, bytearray)):
        return bool(v)
    return v


def guardar_filas(filas: list[dict[str, Any]]) -> int:
    if not filas:
        return 0
    qschema, qtabla, _full, _df = _ids()
    sql = MERGE_SQL.replace("{qschema}", qschema).replace("{qtabla}", qtabla)
    bit_keys = (
        "es_biosimilar",
        "es_generic",
        "es_orphan",
        "es_advanced_therapy",
        "es_conditional",
        "additional_monitoring",
        "patient_safety",
    )
    n = 0
    with engine().begin() as conn:
        for fila in filas:
            payload = dict(fila)
            fd = payload.get("fecha_dato")
            if isinstance(fd, datetime):
                payload["fecha_dato"] = fd.date()
            elif isinstance(fd, str):
                payload["fecha_dato"] = date.fromisoformat(fd[:10])
            for bit in bit_keys:
                payload[bit] = 1 if payload.get(bit) else 0
            for key, val in list(payload.items()):
                if val is None:
                    continue
                if isinstance(val, str) and len(val) > 3900 and key != "therapeutic_indication":
                    payload[key] = val[:3900]
            conn.execute(text(sql), payload)
            n += 1
    return n


def purgar_obsoletos(
    fecha_dato: date | str,
    vigentes: list[tuple[int, str, str]],
) -> int:
    """Quita filas del día que ya no cruzan (p. ej. combinados EMA en principios únicos)."""
    fd = (
        fecha_dato
        if isinstance(fecha_dato, date)
        else date.fromisoformat(str(fecha_dato)[:10])
    )
    qschema, qtabla, _full, _df = _ids()
    with engine().begin() as conn:
        if not vigentes:
            res = conn.execute(
                text(f"DELETE FROM {qschema}.{qtabla} WHERE fecha_dato = :fd"),
                {"fd": fd},
            )
            return int(res.rowcount or 0)
        params: dict[str, Any] = {"fd": fd}
        claves: list[str] = []
        for i, (n_lista, ema_no, nombre) in enumerate(vigentes):
            params[f"k{i}"] = f"{int(n_lista)}|{ema_no}|{nombre}"
            claves.append(f":k{i}")
        sql = (
            f"DELETE FROM {qschema}.{qtabla} "
            f"WHERE fecha_dato = :fd "
            f"AND CONCAT(CAST(n_lista AS VARCHAR(12)), '|', ema_product_number, '|', nombre_medicamento) "
            f"NOT IN ({','.join(claves)})"
        )
        res = conn.execute(text(sql), params)
        return int(res.rowcount or 0)


def purgar_combinados_en_principios_unicos() -> int:
    """Limpieza histórica: EMA con ';' no debe quedar bajo principios sin '/' en la lista."""
    qschema, qtabla, _full, _df = _ids()
    sql = f"""
    DELETE FROM {qschema}.{qtabla}
    WHERE medicamento_lista NOT LIKE N'%/%'
      AND (
            CHARINDEX(N';', ISNULL(active_substance, N'')) > 0
         OR CHARINDEX(N';', ISNULL(inn, N'')) > 0
      )
    """
    with engine().begin() as conn:
        res = conn.execute(text(sql))
        return int(res.rowcount or 0)


def listar_por_n(
    n_lista: int,
    fecha_dato: str | date | None = None,
    solo_ultimo: bool = True,
) -> list[dict[str, Any]]:
    qschema, qtabla, _full, _df = _ids()
    params: dict[str, Any] = {"n": int(n_lista)}
    if fecha_dato:
        params["fd"] = (
            fecha_dato
            if isinstance(fecha_dato, date)
            else date.fromisoformat(str(fecha_dato)[:10])
        )
        where_fd = "fecha_dato = :fd"
    elif solo_ultimo:
        where_fd = (
            f"fecha_dato = (SELECT MAX(fecha_dato) FROM {qschema}.{qtabla} WHERE n_lista = :n)"
        )
    else:
        where_fd = "1=1"
    sql = (
        f"SELECT * FROM {qschema}.{qtabla} "
        f"WHERE n_lista = :n AND {where_fd} "
        f"ORDER BY "
        f"CASE WHEN medicine_status = N'Authorised' THEN 0 ELSE 1 END, "
        f"nombre_medicamento"
    )
    with engine().connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    out = [{k: _jsonable(v) for k, v in dict(r).items()} for r in rows]
    # Defensa: no devolver EMA combinados (';') bajo un principio único de la lista.
    filtradas: list[dict[str, Any]] = []
    for f in out:
        nombre = str(f.get("medicamento_lista") or "")
        lista_combo = "/" in nombre
        inn = str(f.get("inn") or "")
        sub = str(f.get("active_substance") or "")
        ema_combo = ";" in inn or ";" in sub
        if lista_combo == ema_combo:
            filtradas.append(f)
    return filtradas


def resumir_info(filas: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not filas:
        return None
    auth = [f for f in filas if str(f.get("medicine_status") or "").lower() == "authorised"]
    base = auth or filas
    inds = []
    seen_ind: set[str] = set()
    for f in base:
        txt = (f.get("therapeutic_indication") or "").strip()
        if not txt or txt in seen_ind:
            continue
        seen_ind.add(txt)
        inds.append(txt)
    areas: list[str] = []
    seen_a: set[str] = set()
    for f in base:
        for part in str(f.get("therapeutic_area") or "").split(";"):
            p = part.strip()
            if p and p not in seen_a:
                seen_a.add(p)
                areas.append(p)
    atcs = sorted({str(f.get("atc_code")).strip() for f in base if f.get("atc_code")})
    inns = sorted({str(f.get("inn")).strip() for f in base if f.get("inn")})
    return {
        "n_lista": filas[0].get("n_lista"),
        "medicamento_lista": filas[0].get("medicamento_lista"),
        "total_medicamentos": len(filas),
        "total_authorised": len(auth),
        "tiene_biosimilar": any(f.get("es_biosimilar") for f in filas),
        "tiene_generic": any(f.get("es_generic") for f in filas),
        "tiene_orphan": any(f.get("es_orphan") for f in filas),
        "tiene_advanced_therapy": any(f.get("es_advanced_therapy") for f in filas),
        "inns": inns,
        "atc_codes": atcs,
        "therapeutic_areas": areas[:40],
        "indicaciones": inds[:8],
        "periodo_etiqueta": filas[0].get("periodo_etiqueta"),
        "fecha_dato": filas[0].get("fecha_dato"),
        "fuente_url": "https://www.ema.europa.eu/en/medicines/download-medicine-data",
    }


def periodos_disponibles(n_lista: int | None = None) -> list[dict[str, Any]]:
    qschema, qtabla, _full, _df = _ids()
    where = "WHERE n_lista = :n" if n_lista is not None else ""
    params: dict[str, Any] = {"n": int(n_lista)} if n_lista is not None else {}
    sql = (
        f"SELECT fecha_dato, MAX(periodo_etiqueta) AS periodo_etiqueta, COUNT(*) AS filas "
        f"FROM {qschema}.{qtabla} {where} "
        f"GROUP BY fecha_dato ORDER BY fecha_dato DESC"
    )
    with engine().connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [{k: _jsonable(v) for k, v in dict(r).items()} for r in rows]


def _norm_tema_id(s: str) -> str:
    import re

    t = re.sub(r"\s+", " ", str(s or "").strip().lower())
    t = t.replace("’", "'").replace("–", "-").replace("—", "-")
    return t


# Áreas MeSH demasiado amplias para el filtro de Gráficos interactivos.
# Se mantienen temas específicos (ej. "breast neoplasms", "melanoma").
TEMAS_MESH_DEMASIADO_GENERICOS = frozenset(
    {
        "cancer",
        "neoplasm",
        "neoplasms",
        "tumor",
        "tumors",
        "tumour",
        "tumours",
        "carcinoma",  # sin sitio anatómico
        "growth",
        "disease",
        "diseases",
        "disorder",
        "disorders",
        "syndrome",
        "syndromes",
        "pain",
        "infection",
        "infections",
        "inflammation",
        "lung diseases",  # genérico vs NSCLC / SCLC concretos
    }
)


def tema_es_demasiado_generico(tema_id: str | None, label_en: str | None = None) -> bool:
    """True si el tema MeSH es demasiado genérico para comparar en gráficos."""
    for raw in (tema_id, label_en):
        tid = _norm_tema_id(raw or "")
        if tid and tid in TEMAS_MESH_DEMASIADO_GENERICOS:
            return True
    return False


def matriz_temas_ema() -> list[dict[str, Any]]:
    """Invierte therapeutic_area MeSH → principios DAMAC/FOMAC (último snapshot EMA)."""
    asegurar_tabla()
    qschema, qtabla, _full, _df = _ids()
    sql = f"""
    SELECT n_lista, MAX(medicamento_lista) AS medicamento_lista, therapeutic_area
    FROM {qschema}.{qtabla}
    WHERE fecha_dato = (SELECT MAX(fecha_dato) FROM {qschema}.{qtabla})
      AND therapeutic_area IS NOT NULL AND LTRIM(RTRIM(therapeutic_area)) <> N''
    GROUP BY n_lista, therapeutic_area
    """
    with engine().connect() as conn:
        rows = conn.execute(text(sql)).mappings().all()

    try:
        from scrapper.traducir import traducir_termino_area
    except Exception:
        traducir_termino_area = None  # type: ignore

    temas: dict[str, dict[str, Any]] = {}
    for r in rows:
        try:
            n = int(r["n_lista"])
        except (TypeError, ValueError, KeyError):
            continue
        nombre = str(r.get("medicamento_lista") or f"N{n}")
        for part in str(r.get("therapeutic_area") or "").split(";"):
            label_en = part.strip()
            if not label_en:
                continue
            tid = _norm_tema_id(label_en)
            if not tid or tema_es_demasiado_generico(tid, label_en):
                continue
            slot = temas.get(tid)
            if not slot:
                label_es = label_en
                if traducir_termino_area:
                    try:
                        label_es = traducir_termino_area(label_en, usar_motor=False) or label_en
                    except Exception:
                        label_es = label_en
                slot = {
                    "id": tid,
                    "label_en": label_en,
                    "label_es": label_es,
                    "n_listas": [],
                    "principios": [],
                    "_seen": set(),
                }
                temas[tid] = slot
            if n in slot["_seen"]:
                continue
            slot["_seen"].add(n)
            slot["n_listas"].append(n)
            slot["principios"].append({"n_lista": n, "medicamento": nombre})

    out = []
    for slot in temas.values():
        slot["n_listas"].sort()
        slot["principios"].sort(key=lambda x: str(x.get("medicamento") or "").lower())
        out.append(
            {
                "id": slot["id"],
                "label_en": slot["label_en"],
                "label_es": slot["label_es"],
                "label": slot["label_es"] or slot["label_en"],
                "principios": slot["principios"],
                "n_listas": slot["n_listas"],
                "n_principios": len(slot["n_listas"]),
            }
        )
    out.sort(key=lambda t: (-int(t["n_principios"]), str(t["label"]).lower()))
    return out


def principios_de_tema(tema_id: str) -> dict[str, Any] | None:
    """Resuelve un tema por id normalizado (o label EN/ES) y devuelve sus n_lista."""
    tid = _norm_tema_id(tema_id)
    if not tid:
        return None
    for t in matriz_temas_ema():
        if t["id"] == tid:
            return t
        if _norm_tema_id(t.get("label_en") or "") == tid:
            return t
        if _norm_tema_id(t.get("label_es") or "") == tid:
            return t
    return None

