from __future__ import annotations

from datetime import datetime, timedelta
from random import Random

from atlasanalytics.risk import RiskObservation


def generate_synthetic_risk_observations(
    seed: int = 20260831,
    observation_count: int = 420,
) -> list[RiskObservation]:
    """Generate deterministic scored observations for risk-evaluation demos.

    The generator intentionally creates a mild score-distribution shift in the final
    portion of the chronology so PSI and temporal-holdout diagnostics have something
    measurable to report. Labels, scores and amounts are synthetic.
    """

    if observation_count < 20:
        raise ValueError("observation_count must be at least 20")

    rng = Random(seed)
    start = datetime(2026, 6, 1, 8, 0, 0)
    issuers = ("iss-atlas-ma", "iss-rif-ma", "iss-euro-eu")
    observations: list[RiskObservation] = []

    shift_start = int(observation_count * 0.72)
    for index in range(observation_count):
        issuer_id = issuers[index % len(issuers)]
        amount_minor = rng.randint(2_500, 220_000)
        amount_signal = min(amount_minor / 220_000, 1.0)
        issuer_signal = 0.035 if issuer_id == "iss-rif-ma" else 0.0
        late_period = index >= shift_start
        late_period_signal = 0.025 if late_period else 0.0

        fraud_probability = min(
            0.42,
            0.025 + 0.09 * amount_signal + issuer_signal + late_period_signal,
        )
        is_fraud = rng.random() < fraud_probability

        if is_fraud:
            score = 0.55 + 0.34 * rng.random() + 0.06 * amount_signal
        else:
            score = 0.04 + 0.34 * rng.random() + 0.08 * amount_signal

        # The holdout period is deliberately a little higher-scoring. This models a
        # monitoring scenario, not evidence that a real fraud model drifted.
        if late_period:
            score += 0.07
        score = max(0.0, min(score, 0.99))

        observations.append(
            RiskObservation(
                occurred_at=start + timedelta(hours=index * 2),
                score=score,
                is_fraud=is_fraud,
                amount_minor=amount_minor,
                issuer_id=issuer_id,
            )
        )

    return observations
