from __future__ import annotations

from atlasanalytics import build_executive_summary, build_warehouse


def test_decline_taxonomy_covers_every_failed_authorization_attempt() -> None:
    connection = build_warehouse()

    failed_attempts = connection.execute(
        "select count(*) from fact_authorization where disposition in ('declined', 'timed_out')"
    ).fetchone()[0]
    classified_attempts = connection.execute(
        "select coalesce(sum(decline_attempts), 0) from mart_decline_daily"
    ).fetchone()[0]
    reasons = {
        row[0]
        for row in connection.execute(
            "select distinct decline_reason from mart_decline_daily"
        ).fetchall()
    }

    assert classified_attempts == failed_attempts
    assert reasons <= {
        "insufficient_funds",
        "do_not_honor",
        "network_timeout",
        "other_decline",
    }
    assert "network_timeout" in reasons


def test_issuer_baseline_never_uses_current_observation_as_history() -> None:
    connection = build_warehouse()

    first_rows_with_history = connection.execute(
        """
        select count(*)
        from (
            select
                *,
                row_number() over (
                    partition by currency_code, issuer_id order by metric_date
                ) as sequence_no
            from mart_issuer_baseline
        ) ranked
        where sequence_no = 1 and baseline_observations <> 0
        """
    ).fetchone()[0]
    premature_scores = connection.execute(
        """
        select count(*)
        from mart_issuer_baseline
        where baseline_observations < 5
          and (approval_rate_zscore is not null or timeout_rate_zscore is not null)
        """
    ).fetchone()[0]

    assert first_rows_with_history == 0
    assert premature_scores == 0


def test_issuer_anomaly_states_and_rates_are_defensible() -> None:
    connection = build_warehouse()

    invalid_states = connection.execute(
        """
        select count(*)
        from mart_issuer_baseline
        where anomaly_state not in ('normal', 'investigate', 'critical')
        """
    ).fetchone()[0]
    invalid_rates = connection.execute(
        """
        select count(*)
        from mart_issuer_baseline
        where authorization_approval_rate < 0
           or authorization_approval_rate > 1
           or timeout_rate < 0
           or timeout_rate > 1
        """
    ).fetchone()[0]

    assert invalid_states == 0
    assert invalid_rates == 0


def test_executive_summary_is_measured_from_atomic_facts() -> None:
    connection = build_warehouse()
    summary = build_executive_summary(connection)

    payment_count = connection.execute("select count(*) from fact_payment").fetchone()[0]
    authorization_count = connection.execute("select count(*) from fact_authorization").fetchone()[
        0
    ]
    reversal_count = connection.execute("select count(*) from fact_reversal").fetchone()[0]

    assert summary.payments == payment_count
    assert summary.authorization_attempts == authorization_count
    assert summary.reversals == reversal_count
    assert summary.data_scope == "synthetic"
    assert 0 <= summary.approval_rate <= 1
    assert 0 <= summary.timeout_rate <= 1
    assert len(summary.findings()) == 5
    assert all("synthetic scenario" in finding.lower() for finding in summary.findings())
