from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from random import Random


@dataclass(frozen=True)
class SyntheticDataset:
    currencies: list[tuple[str, str, int]]
    issuers: list[tuple[str, str, str]]
    payments: list[tuple[str, datetime, str, str, int, str]]
    authorizations: list[tuple[str, str, int, datetime, str, str | None, int | None]]
    reversals: list[tuple[str, str, str, str, datetime]]
    reconciliations: list[tuple[str, object, str, int, int, int]]


def generate_synthetic_dataset(seed: int = 20260831, payment_count: int = 240) -> SyntheticDataset:
    """Generate deterministic synthetic payment operations for warehouse regression tests.

    The dataset is intentionally synthetic. It contains no real cardholder, merchant, PAN,
    account, or production transaction data.
    """

    if payment_count <= 0:
        raise ValueError("payment_count must be positive")

    rng = Random(seed)
    currencies = [("MAD", "Moroccan dirham", 2), ("EUR", "Euro", 2)]
    issuers = [
        ("iss-atlas-ma", "Atlas Bank MA", "MA"),
        ("iss-rif-ma", "Rif Credit MA", "MA"),
        ("iss-euro-eu", "Euro Issuer EU", "FR"),
    ]

    payments: list[tuple[str, datetime, str, str, int, str]] = []
    authorizations: list[tuple[str, str, int, datetime, str, str | None, int | None]] = []
    reversals: list[tuple[str, str, str, str, datetime]] = []
    captured_by_day_currency: defaultdict[tuple[object, str], int] = defaultdict(int)

    start = datetime(2026, 7, 1, 8, 0, 0)
    for index in range(payment_count):
        payment_id = f"pay-{index + 1:05d}"
        authorization_id = f"auth-{index + 1:05d}"
        created_at = start + timedelta(hours=index * 3)
        currency_code = "MAD" if rng.random() < 0.72 else "EUR"
        issuer_id = rng.choice([issuer[0] for issuer in issuers])
        amount_minor = rng.randint(2_500, 180_000)

        outcome = rng.random()
        reversal_reason: str | None = None
        if outcome < 0.76:
            disposition = "approved"
            response_code = "00"
            latency_ms = rng.randint(45, 850)
            if rng.random() < 0.07:
                final_status = "reversed"
                reversal_reason = "operator" if rng.random() < 0.5 else "late_response"
            else:
                final_status = "captured"
        elif outcome < 0.90:
            disposition = "declined"
            response_code = "51" if rng.random() < 0.65 else "05"
            latency_ms = rng.randint(35, 600)
            final_status = "declined"
        else:
            disposition = "timed_out"
            response_code = None
            latency_ms = None
            if rng.random() < 0.60:
                final_status = "reversed"
                reversal_reason = "timeout"
            else:
                final_status = "timed_out"

        payments.append(
            (payment_id, created_at, currency_code, issuer_id, amount_minor, final_status)
        )
        authorizations.append(
            (
                authorization_id,
                payment_id,
                1,
                created_at,
                disposition,
                response_code,
                latency_ms,
            )
        )

        if final_status == "captured":
            captured_by_day_currency[(created_at.date(), currency_code)] += amount_minor

        if reversal_reason is not None:
            reversals.append(
                (
                    f"rev-{index + 1:05d}",
                    payment_id,
                    authorization_id,
                    reversal_reason,
                    created_at + timedelta(minutes=5),
                )
            )

    reconciliations: list[tuple[str, object, str, int, int, int]] = []
    for sequence, ((control_date, currency_code), expected_minor) in enumerate(
        sorted(captured_by_day_currency.items()), start=1
    ):
        discrepancy_minor = 250 if sequence % 11 == 0 else 0
        observed_minor = expected_minor + discrepancy_minor
        reconciliations.append(
            (
                f"rec-{sequence:05d}",
                control_date,
                currency_code,
                expected_minor,
                observed_minor,
                discrepancy_minor,
            )
        )

    return SyntheticDataset(
        currencies=currencies,
        issuers=issuers,
        payments=payments,
        authorizations=authorizations,
        reversals=reversals,
        reconciliations=reconciliations,
    )
