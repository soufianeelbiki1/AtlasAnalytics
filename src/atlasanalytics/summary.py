from __future__ import annotations

from dataclasses import dataclass

import duckdb


@dataclass(frozen=True)
class ExecutiveSummary:
    payments: int
    requested_amount_minor: int
    captured_amount_minor: int
    authorization_attempts: int
    approval_rate: float
    timeout_rate: float
    reversals: int
    reconciliation_exceptions: int
    issuer_anomalies: int
    data_scope: str = "synthetic"

    def findings(self) -> list[str]:
        prefix = "Synthetic scenario:"
        return [
            (
                f"{prefix} authorization approval rate is {self.approval_rate:.1%} across "
                f"{self.authorization_attempts:,} attempts."
            ),
            (
                f"{prefix} timeout rate is {self.timeout_rate:.1%}; "
                f"{self.reversals:,} reversals were recorded."
            ),
            (
                f"{prefix} captured amount is {self.captured_amount_minor:,} minor units from "
                f"{self.requested_amount_minor:,} requested minor units."
            ),
            (
                f"{prefix} reconciliation surfaced {self.reconciliation_exceptions:,} "
                "exception days; exceptions are not silently netted away."
            ),
            (
                f"{prefix} rolling issuer baselines flag {self.issuer_anomalies:,} "
                "issuer-day observations for investigation or critical review."
            ),
        ]


def build_executive_summary(connection: duckdb.DuckDBPyConnection) -> ExecutiveSummary:
    payment_row = connection.execute(
        """
        select
            count(*) as payments,
            coalesce(sum(amount_minor), 0) as requested_amount_minor,
            coalesce(sum(amount_minor) filter (where final_status = 'captured'), 0)
                as captured_amount_minor
        from fact_payment
        """
    ).fetchone()
    authorization_row = connection.execute(
        """
        select
            count(*) as attempts,
            coalesce(avg(case when disposition = 'approved' then 1.0 else 0.0 end), 0.0)
                as approval_rate,
            coalesce(avg(case when disposition = 'timed_out' then 1.0 else 0.0 end), 0.0)
                as timeout_rate
        from fact_authorization
        """
    ).fetchone()
    reversals = connection.execute("select count(*) from fact_reversal").fetchone()[0]
    reconciliation_exceptions = connection.execute(
        "select count(*) from fact_reconciliation where discrepancy_minor <> 0"
    ).fetchone()[0]
    issuer_anomalies = connection.execute(
        "select count(*) from mart_issuer_baseline where anomaly_state <> 'normal'"
    ).fetchone()[0]

    if payment_row is None or authorization_row is None:
        raise RuntimeError("warehouse aggregate query unexpectedly returned no row")

    return ExecutiveSummary(
        payments=int(payment_row[0]),
        requested_amount_minor=int(payment_row[1]),
        captured_amount_minor=int(payment_row[2]),
        authorization_attempts=int(authorization_row[0]),
        approval_rate=float(authorization_row[1]),
        timeout_rate=float(authorization_row[2]),
        reversals=int(reversals),
        reconciliation_exceptions=int(reconciliation_exceptions),
        issuer_anomalies=int(issuer_anomalies),
    )
