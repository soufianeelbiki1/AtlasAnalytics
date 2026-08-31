from datetime import datetime, timedelta

import pytest

from atlasanalytics.risk import (
    RiskObservation,
    calibration_bins,
    evaluate_threshold,
    population_stability_index,
    select_cost_optimal_threshold,
    temporal_split,
)


def _observations() -> list[RiskObservation]:
    start = datetime(2026, 7, 1)
    rows: list[RiskObservation] = []
    for index in range(20):
        is_fraud = index in {3, 8, 14, 18}
        score = {
            3: 0.82,
            8: 0.73,
            14: 0.91,
            18: 0.64,
        }.get(index, 0.08 + (index % 5) * 0.08)
        rows.append(
            RiskObservation(
                occurred_at=start + timedelta(hours=index),
                score=score,
                is_fraud=is_fraud,
                amount_minor=50_000 if is_fraud else 8_000,
                issuer_id="iss-atlas-ma" if index % 2 == 0 else "iss-rif-ma",
            )
        )
    return rows


def test_temporal_split_preserves_chronology() -> None:
    observations = list(reversed(_observations()))

    train, test = temporal_split(observations, train_fraction=0.7)

    assert len(train) == 14
    assert len(test) == 6
    assert max(row.occurred_at for row in train) < min(row.occurred_at for row in test)


def test_cost_sensitive_threshold_penalizes_missed_fraud() -> None:
    observations = _observations()

    strict = evaluate_threshold(observations, 0.90, false_positive_cost_minor=100)
    balanced = evaluate_threshold(observations, 0.60, false_positive_cost_minor=100)

    assert balanced.recall > strict.recall
    assert balanced.expected_cost_minor < strict.expected_cost_minor


def test_threshold_selection_minimizes_declared_cost_model() -> None:
    observations = _observations()
    thresholds = [0.40, 0.60, 0.75, 0.90]

    selected = select_cost_optimal_threshold(
        observations,
        thresholds,
        false_positive_cost_minor=100,
    )
    costs = [
        evaluate_threshold(observations, threshold, false_positive_cost_minor=100).expected_cost_minor
        for threshold in thresholds
    ]

    assert selected.expected_cost_minor == min(costs)
    assert selected.threshold in thresholds


def test_calibration_bins_report_score_and_observed_rate() -> None:
    bins = calibration_bins(_observations(), bin_count=5)

    assert sum(bucket.count for bucket in bins) == 20
    assert all(0 <= bucket.mean_score <= 1 for bucket in bins)
    assert all(0 <= bucket.observed_fraud_rate <= 1 for bucket in bins)


def test_population_stability_index_detects_distribution_shift() -> None:
    reference = [0.05, 0.08, 0.12, 0.15, 0.18, 0.22, 0.25, 0.28]
    stable = [0.06, 0.09, 0.11, 0.16, 0.19, 0.21, 0.24, 0.27]
    shifted = [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]

    assert population_stability_index(reference, stable) < population_stability_index(
        reference, shifted
    )


def test_invalid_temporal_fraction_is_rejected() -> None:
    with pytest.raises(ValueError):
        temporal_split(_observations(), train_fraction=1.0)
