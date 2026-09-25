"""Conexión a la base de precios.

Por defecto usa PostgreSQL (este servidor). Si DB_DIALECT=mssql conserva
el camino original hacia SQL Server / REDATAM.
"""

from __future__ import annotations

import os
import re
import urllib.parse
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

load_dotenv()

_ENGINE: Engine | None = None


def _first(*keys: str, default: str = "") -> str:
    for key in keys:
        valor = os.getenv(key)
        if valor is not None and str(valor).strip() != "":
            return str(valor).strip()
    return default


def _cfg() -> dict[str, str]:
    timeout = _first("REDATAM_DB_TIMEOUT", "DW_DB_TIMEOUT", "DB_CONNECTION_TIMEOUT", default="15")
    if timeout in ("", "0"):
        timeout = "15"
    dialect = _first("DB_DIALECT", default="postgres").lower()
    if dialect in ("postgresql", "pg"):
        dialect = "postgres"
    return {
        "dialect": dialect,
        "host": _first("REDATAM_DB_HOST", "DW_DB_HOST", "DB_SERVER", default="127.0.0.1"),
        "port": _first("REDATAM_DB_PORT", "DW_DB_PORT", "DB_PORT", default="5432" if dialect == "postgres" else "1433"),
        "database": _first("REDATAM_DB_DATABASE", "DW_DB_DATABASE", "DB_NAME", default="altocosto"),
        "schema": _first("REDATAM_DB_SCHEMA", "DB_SCHEMA", default="public" if dialect == "postgres" else "dbo"),
        "user": _first("REDATAM_DB_USERNAME", "DW_DB_USERNAME", "DB_USER"),
        "password": _first("REDATAM_DB_PASSWORD", "DW_DB_PASSWORD", "DB_PASSWORD"),
        "driver": _first("DB_DRIVER", default="ODBC Driver 17 for SQL Server"),
        "encrypt": _first("DB_ENCRYPT", default="no"),
        "trust": _first("DB_TRUST_SERVER_CERTIFICATE", default="yes"),
        "timeout": timeout,
    }


def es_postgres() -> bool:
    return _cfg()["dialect"] == "postgres"


def resumen_config() -> dict[str, str]:
    c = _cfg()
    return {
        "dialect": c["dialect"],
        "host": c["host"],
        "port": c["port"],
        "database": c["database"],
        "schema": c["schema"],
        "user": c["user"],
        "driver": "psycopg" if c["dialect"] == "postgres" else c["driver"],
    }


def _incompatible_mssql(sql: str) -> bool:
    up = sql.upper()
    marcas = (
        "SYS.TABLES",
        "SYS.SCHEMAS",
        "SYS.COLUMNS",
        "SYS.DEFAULT_CONSTRAINTS",
        "SYS.INDEXES",
        "SYS.INDEX_COLUMNS",
        "SYS.KEY_CONSTRAINTS",
        "COL_LENGTH(",
        "OBJECT_ID(",
        "OBJECT_ID (",
        "SP_EXECUTESQL",
    )
    return any(m in up for m in marcas)


def traducir_sql(sql: str) -> str:
    """Adapta el T-SQL que ya traen los scrapers para PostgreSQL."""
    if not es_postgres() or not sql:
        return sql
    if _incompatible_mssql(sql):
        return "SELECT NULL"
    s = sql
    s = re.sub(r"\[([^\]]+)\]", r'"\1"', s)
    s = re.sub(
        r"CAST\s*\(\s*GETDATE\s*\(\s*\)\s*AS\s+DATE\s*\)",
        "CURRENT_DATE",
        s,
        flags=re.I,
    )
    s = re.sub(
        r"CONVERT\s*\(\s*date\s*,\s*GETDATE\s*\(\s*\)\s*\)",
        "CURRENT_DATE",
        s,
        flags=re.I,
    )
    s = re.sub(r"GETDATE\s*\(\s*\)", "CURRENT_TIMESTAMP", s, flags=re.I)
    param = r"(?:%\([^)]+\)s|:\w+|\$\d+)"
    s = re.sub(
        rf"DATEADD\s*\(\s*day\s*,\s*-1\s*,\s*({param})\s*\)",
        r"(CAST(\1 AS date) - INTERVAL '1 day')",
        s,
        flags=re.I,
    )
    s = re.sub(
        rf"DATEADD\s*\(\s*minute\s*,\s*-({param})\s*,\s*CURRENT_TIMESTAMP\s*\)",
        r"(CURRENT_TIMESTAMP - (\1 * INTERVAL '1 minute'))",
        s,
        flags=re.I,
    )
    s = re.sub(r"(?i)(?<![A-Za-z0-9_])N'", "'", s)
    s = re.sub(r"(?i)\bMERGE\s+(?!INTO\b)", "MERGE INTO ", s)
    if re.search(r"OUTPUT\s+INSERTED\.\*", s, re.I):
        s = re.sub(r"OUTPUT\s+INSERTED\.\*\s*", "", s, flags=re.I)
        s = s.rstrip().rstrip(";") + " RETURNING *"
    elif re.search(r"OUTPUT\s+INSERTED\.id", s, re.I):
        s = re.sub(r"OUTPUT\s+INSERTED\.id\s*", "", s, flags=re.I)
        s = s.rstrip().rstrip(";") + " RETURNING id"
    m = re.search(
        r"SELECT\s+TOP\s+(\(%\([^)]+\)s\)|\(:\w+\)|\$\d+|\d+)\s+",
        s,
        flags=re.I,
    )
    if m and " LIMIT " not in s.upper():
        token = m.group(1)
        lim = token[1:-1] if token.startswith("(") else token
        s = re.sub(
            r"SELECT\s+TOP\s+(?:\(%\([^)]+\)s\)|\(:\w+\)|\$\d+|\d+)\s+",
            "SELECT ",
            s,
            count=1,
            flags=re.I,
        )
        s = s.rstrip().rstrip(";") + f" LIMIT {lim}"
    if "MERGE INTO" in s.upper():
        casts = {
            "fecha_publicacion": "timestamp",
            "fecha_dato": "date",
            "fecha_vista": "date",
            "precio": "numeric",
            "precio_lista": "numeric",
            "precio_oferta": "numeric",
            "precio_usd": "numeric",
            "n_lista": "integer",
        }
        for col, tipo in casts.items():
            s = re.sub(
                rf"((?:%\({col}\)s|:{col}))\s+AS\s+{col}\b",
                rf"\1::{tipo} AS {col}",
                s,
                flags=re.I,
            )
    return s


def _rewrite(conn, cursor, statement, parameters, context, executemany):
    return traducir_sql(statement), parameters


def cadena_odbc() -> str:
    c = _cfg()
    return (
        f"DRIVER={{{c['driver']}}};"
        f"SERVER={c['host']},{c['port']};"
        f"DATABASE={c['database']};"
        f"UID={c['user']};"
        f"PWD={c['password']};"
        f"Encrypt={c['encrypt']};"
        f"TrustServerCertificate={c['trust']};"
        f"Connection Timeout={c['timeout']};"
    )


def engine() -> Engine:
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE
    c = _cfg()
    if c["dialect"] == "postgres":
        user = urllib.parse.quote_plus(c["user"])
        password = urllib.parse.quote_plus(c["password"])
        url = (
            f"postgresql+psycopg://{user}:{password}"
            f"@{c['host']}:{c['port']}/{c['database']}"
        )
        _ENGINE = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)
        event.listen(_ENGINE, "before_cursor_execute", _rewrite, retval=True)
        return _ENGINE
    params = urllib.parse.quote_plus(cadena_odbc())
    _ENGINE = create_engine(f"mssql+pyodbc:///?odbc_connect={params}", pool_pre_ping=True)
    return _ENGINE


def ping() -> dict[str, Any]:
    info = resumen_config()
    try:
        with engine().connect() as conn:
            if es_postgres():
                row = conn.execute(
                    text(
                        "SELECT current_database() AS db, current_user AS usuario, "
                        "COALESCE(inet_server_addr()::text, 'local') AS servidor, "
                        "(SELECT oid FROM pg_namespace WHERE nspname = :esquema) AS schema_id"
                    ),
                    {"esquema": info["schema"]},
                ).mappings().first()
            else:
                row = conn.execute(
                    text(
                        "SELECT DB_NAME() AS db, SUSER_SNAME() AS usuario, @@SERVERNAME AS servidor, "
                        "SCHEMA_ID(:esquema) AS schema_id"
                    ),
                    {"esquema": info["schema"]},
                ).mappings().first()
        schema_ok = bool(row and row["schema_id"])
        motor = "PostgreSQL" if es_postgres() else "SQL Server"
        return {
            "ok": True,
            "mensaje": f"Conectado a {motor}" + ("" if schema_ok else f" (esquema {info['schema']} no encontrado)"),
            **info,
            "db": row["db"] if row else info["database"],
            "usuario": row["usuario"] if row else info["user"],
            "servidor": row["servidor"] if row else info["host"],
            "schema_ok": schema_ok,
        }
    except Exception as exc:
        return {
            "ok": False,
            "mensaje": str(exc).split("\n")[0],
            **info,
        }
