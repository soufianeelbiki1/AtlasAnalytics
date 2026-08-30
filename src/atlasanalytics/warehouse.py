from __future__ import annotations

from pathlib import Path

import duckdb

from .synthetic import SyntheticDataset, generate_synthetic_dataset


ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / "sql"


def _execute_script(connection: duckdb.DuckDBPyConnection, path: Path) -> None:
    connection.execute(path.read_text(encoding="utf-8"))


def build_warehouse(
    dataset: SyntheticDataset | None = None,
    database: str = ":memory:",
) -> duckdb.DuckDBPyConnection:
    dataset = dataset or generate_synthetic_dataset()
    connection = duckdb.connect(database)
    _execute_script(connection, SQL_DIR / "schema.sql")

    connection.executemany(
        "insert into dim_currency values (?, ?, ?)",
        dataset.currencies,
    )
    connection.executemany(
        "insert into dim_issuer values (?, ?, ?)",
        dataset.issuers,
    )
    connection.executemany(
        "insert into fact_payment values (?, ?, ?, ?, ?, ?)",
        dataset.payments,
    )
    connection.executemany(
        "insert into fact_authorization values (?, ?, ?, ?, ?, ?, ?)",
        dataset.authorizations,
    )
    if dataset.reversals:
        connection.executemany(
            "insert into fact_reversal values (?, ?, ?, ?, ?)",
            dataset.reversals,
        )
    if dataset.reconciliations:
        connection.executemany(
            "insert into fact_reconciliation values (?, ?, ?, ?, ?, ?)",
            dataset.reconciliations,
        )

    _execute_script(connection, SQL_DIR / "marts" / "payment_daily.sql")
    _execute_script(connection, SQL_DIR / "marts" / "issuer_daily.sql")
    return connection
