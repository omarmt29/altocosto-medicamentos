"""Conexión a SQL Server (REDATAM)."""

from __future__ import annotations

import os
import urllib.parse
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()


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
    return {
        "host": _first("REDATAM_DB_HOST", "DW_DB_HOST", "DB_SERVER"),
        "port": _first("REDATAM_DB_PORT", "DW_DB_PORT", "DB_PORT", default="1433"),
        "database": _first("REDATAM_DB_DATABASE", "DW_DB_DATABASE", "DB_NAME"),
        "schema": _first("REDATAM_DB_SCHEMA", "DB_SCHEMA", default="dbo"),
        "user": _first("REDATAM_DB_USERNAME", "DW_DB_USERNAME", "DB_USER"),
        "password": _first("REDATAM_DB_PASSWORD", "DW_DB_PASSWORD", "DB_PASSWORD"),
        "driver": _first("DB_DRIVER", default="ODBC Driver 17 for SQL Server"),
        "encrypt": _first("DB_ENCRYPT", default="no"),
        "trust": _first("DB_TRUST_SERVER_CERTIFICATE", default="yes"),
        "timeout": timeout,
    }


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
    params = urllib.parse.quote_plus(cadena_odbc())
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}", pool_pre_ping=True)


def resumen_config() -> dict[str, str]:
    c = _cfg()
    return {
        "host": c["host"],
        "port": c["port"],
        "database": c["database"],
        "schema": c["schema"],
        "user": c["user"],
        "driver": c["driver"],
    }


def ping() -> dict[str, Any]:
    info = resumen_config()
    try:
        with engine().connect() as conn:
            row = conn.execute(
                text(
                    "SELECT DB_NAME() AS db, SUSER_SNAME() AS usuario, @@SERVERNAME AS servidor, "
                    "SCHEMA_ID(:esquema) AS schema_id"
                ),
                {"esquema": info["schema"]},
            ).mappings().first()
        schema_ok = bool(row and row["schema_id"])
        return {
            "ok": True,
            "mensaje": "Conectado a SQL Server" + ("" if schema_ok else f" (esquema {info['schema']} no encontrado)"),
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
