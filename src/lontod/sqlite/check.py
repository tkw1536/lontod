"""test utilities for sqlite"""

from sqlite3 import Connection, connect
from typing import Any, TypedDict


def make_test_database(sql_script: str) -> Connection:
    """creates a new database with contents initialized by the given script"""
    c = connect(":memory:")
    c.executescript(sql_script)
    return c


def _table_names(conn: Connection) -> set[str]:
    cursor = conn.cursor().execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {table[0] for table in cursor.fetchall()}


def _table_schema(conn: Connection, table: str) -> list[Any]:
    cursor = conn.cursor().execute(f"PRAGMA table_info({table})")
    return cursor.fetchall()


def _table_data(conn: Connection, table: str) -> list[Any]:
    cursor = conn.cursor().execute(f"SELECT * FROM {table}")
    return cursor.fetchall()


class TableDiff(TypedDict):
    """diff of two tables"""

    table: str
    schema_left: list[Any]
    schema_right: list[Any]
    left: list[Any]
    right: list[Any]


class DatabaseDiff(TypedDict):
    """diff of two databases"""

    left: set[str]
    right: set[str]
    diff: list[TableDiff]


def diff_database(left: Connection, right: Connection) -> DatabaseDiff:
    """performs a diff on two databases"""

    tables_left = _table_names(left)
    tables_right = _table_names(right)

    left_only_tables = tables_left - tables_right
    right_only_tables = tables_right - tables_left
    common_tables = tables_left.intersection(tables_right)

    diff: list[TableDiff] = []

    for table in common_tables:
        schema_left = _table_schema(left, table)
        schema_right = _table_schema(right, table)

        data_left = _table_data(left, table)
        data_right = _table_data(right, table)

        if schema_left != schema_right or data_left != data_right:
            diff.append(
                {
                    "table": table,
                    "schema_left": schema_left,
                    "schema_right": schema_right,
                    "left": data_left,
                    "right": data_right,
                }
            )

    return {
        "left": left_only_tables,
        "right": right_only_tables,
        "diff": diff,
    }
