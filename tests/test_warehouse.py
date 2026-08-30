from __future__ import annotations

import duckdb
import pytest

from atlasanalytics import build_warehouse, generate_synthetic_dataset


def scalar(connection: duckdb.DuckDBPyConnection, query: str):
    return connection.execute(query).fetchone()[0]


def test_synthetic_dataset_is_deterministic_and_labeled_by_contract() -> None:
    first = generate_synthetic_dataset(seed=7, payment_count=25)
    second = generate_synthetic_dataset(seed=7, payment_count=25)

    assert first == second
    assert len(first.payments) == 25
    assert all(payment[0].startswith("pay-") for payment in first.payments)


def test_warehouse_builds_with_expected_fact_grains() -> None:
    connection = build_warehouse(generate_synthetic_dataset(payment_count=240))

    assert scalar(connection, "select count(*) from fact_payment") == 240
    assert scalar(connection, "select count(*) from fact_authorization") == 240
    assert scalar(connection, "select count(*) from dim_issuer") == 3
    assert scalar(connection, "select count(*) from dim_currency") == 2
    assert scalar(connection, "select count(*) from fact_reversal") > 0
    assert scalar(connection, "select count(*) from fact_reconciliation") > 0


def test_daily_mart_reconciles_to_atomic_facts() -> None:
    connection = build_warehouse()

    fact_payments = scalar(connection, "select count(*) from fact_payment")
    mart_payments = scalar(connection, "select sum(payments) from mart_payment_daily")
    fact_authorizations = scalar(connection, "select count(*) from fact_authorization")
    mart_authorizations = scalar(
        connection, "select sum(authorization_attempts) from mart_payment_daily"
    )

    assert mart_payments == fact_payments
    assert mart_authorizations == fact_authorizations
    assert scalar(
        connection,
        "select count(*) from mart_payment_daily "
        "where authorization_approval_rate < 0 or authorization_approval_rate > 1",
    ) == 0


def test_retry_attempt_does_not_double_count_payment_amount() -> None:
    connection = build_warehouse()
    requested_before = scalar(
        connection, "select sum(requested_amount_minor) from mart_payment_daily"
    )
    attempts_before = scalar(
        connection, "select sum(authorization_attempts) from mart_payment_daily"
    )

    connection.execute(
        """
        insert into fact_authorization
        select
            'auth-retry-00001',
            payment_id,
            2,
            created_at + interval '1 minute',
            'declined',
            '05',
            120
        from fact_payment
        where payment_id = 'pay-00001'
        """
    )

    requested_after = scalar(
        connection, "select sum(requested_amount_minor) from mart_payment_daily"
    )
    attempts_after = scalar(
        connection, "select sum(authorization_attempts) from mart_payment_daily"
    )

    assert requested_after == requested_before
    assert attempts_after == attempts_before + 1


def test_reconciliation_exceptions_are_explicit_not_hidden() -> None:
    connection = build_warehouse()

    exceptions = scalar(
        connection, "select sum(reconciliation_exceptions) from mart_payment_daily"
    )
    discrepancy = scalar(
        connection, "select sum(reconciliation_discrepancy_minor) from mart_payment_daily"
    )

    assert exceptions > 0
    assert discrepancy > 0


def test_timeout_latency_invariant_fails_closed() -> None:
    connection = build_warehouse(generate_synthetic_dataset(payment_count=5))

    with pytest.raises(duckdb.ConstraintException):
        connection.execute(
            """
            insert into fact_authorization values (
                'auth-invalid-timeout',
                'pay-00001',
                2,
                timestamp '2026-07-01 08:01:00',
                'timed_out',
                null,
                999
            )
            """
        )
