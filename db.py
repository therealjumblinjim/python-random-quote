"""Database helpers for MSSQL ODBC access.

This module is intentionally beginner-friendly and focused on read-only querying.
"""

from __future__ import annotations

import os
from typing import Any

import pyodbc


class DatabaseError(RuntimeError):
    """Raised when database configuration or execution fails."""


def _build_conn_str_from_parts() -> str | None:
    """Build a connection string from individual env vars when provided.

    This is a beginner-friendly alternative to setting one long
    `MSSQL_ODBC_CONN_STR` value.
    """
    driver = os.getenv("proto")
    server = os.getenv("TheMachine")
    database = os.getenv("proto")

    if not (driver and server and database):
        return None

    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
        f"DATABASE={database}",
        f"Encrypt={os.getenv('MSSQL_ENCRYPT', 'yes')}",
        f"TrustServerCertificate={os.getenv('MSSQL_TRUST_SERVER_CERT', 'yes')}",
    ]

    if os.getenv("MSSQL_TRUSTED_CONNECTION", "no").lower() in {"yes", "true", "1"}:
        parts.append("Trusted_Connection=yes")
    else:
        uid = os.getenv("emsdba")
        pwd = os.getenv("emsdba")
        if not (uid and pwd):
            raise DatabaseError(
                "Using split MSSQL settings requires MSSQL_UID and MSSQL_PWD, "
                "unless MSSQL_TRUSTED_CONNECTION=yes."
            )
        parts.append(f"UID={uid}")
        parts.append(f"PWD={pwd}")

    return ";".join(parts) + ";"


def get_connection() -> pyodbc.Connection:
    """Create and return a pyodbc connection using env configuration.

    Supported config styles:
      1) MSSQL_ODBC_CONN_STR (single full connection string)
      2) Split env vars (driver/server/database/etc.)

    Optional:
      - DB_QUERY_TIMEOUT_SECONDS (default: 30)
    """
    conn_str = os.getenv("MSSQL_ODBC_CONN_STR") or _build_conn_str_from_parts()
    if not conn_str:
        raise DatabaseError(
            "Set either MSSQL_ODBC_CONN_STR, or split vars: "
            "MSSQL_ODBC_DRIVER, MSSQL_SERVER, MSSQL_DATABASE, "
            "plus MSSQL_UID/MSSQL_PWD (or MSSQL_TRUSTED_CONNECTION=yes)."
        )

    timeout_seconds = int(os.getenv("DB_QUERY_TIMEOUT_SECONDS", "30"))
    try:
        conn = pyodbc.connect(conn_str, timeout=timeout_seconds)
    except pyodbc.Error as exc:
        raise DatabaseError(f"Could not connect to SQL Server: {exc}") from exc

    return conn


def fetch_schema_context(limit_tables: int = 25, limit_columns: int = 400) -> str:
    """Return a compact schema summary to send to the LLM."""
    table_sql = """
        SELECT TOP (?) TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME;
    """

    column_sql = """
        SELECT TOP (?) TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION;
    """

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(table_sql, limit_tables)
        tables = cur.fetchall()

        cur.execute(column_sql, limit_columns)
        columns = cur.fetchall()

    table_lines = [f"- {row.TABLE_SCHEMA}.{row.TABLE_NAME}" for row in tables]
    column_lines = [
        f"- {row.TABLE_SCHEMA}.{row.TABLE_NAME}.{row.COLUMN_NAME} ({row.DATA_TYPE})"
        for row in columns
    ]

    return "\n".join(
        [
            "TABLES:",
            *(table_lines or ["- (none found)"]),
            "",
            "COLUMNS:",
            *(column_lines or ["- (none found)"]),
        ]
    )


def run_select_query(sql: str, max_rows: int = 100) -> dict[str, Any]:
    """Execute a validated SELECT query and return rows as dictionaries."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql)

        columns = [col[0] for col in cur.description] if cur.description else []
        rows = cur.fetchmany(max_rows)

    data = [dict(zip(columns, row)) for row in rows]
    return {"columns": columns, "rows": data, "row_count": len(data)}
