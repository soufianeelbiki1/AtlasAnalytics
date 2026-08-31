from __future__ import annotations

from dataclasses import dataclass
from math import log
from statistics import mean


@dataclass(frozen=True)
class RiskObservation:
    occurred_at: object
    score: float
    is_fraud: bool
    amount_minor: int
    issuer_id: str


@dataclass(frozen=True)
class ThresholdMetrics:
    threshold: float
    precision: float
    recall: float
    false_positive_rate: float
    expected_cost_minor: float
    alert_rate: float


@dataclass(frozen=True)
class CalibrationBin:
    lower_bound: float
    upper_bound: float
    count: int
    mean_score: float
    observed_fraud_rate: float


def temporal_split(
    observations: list[RiskObservation],
    train_fraction: float = 0.7,
) -> tuple[list[RiskObservation], list[RiskObservation]]:
    """Split observations chronologically to avoid future-to-past leakage."""

    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1")
    ordered = sorted(observations, key=lambda observation: observation.occurred_at)
    split_at = max(1, min(len(ordered) - 1, int(len(ordered) * train_fraction)))
    return ordered[:split_at], ordered[split_at:]


def evaluate_threshold(
    observations: list[RiskObservation],
    threshold: float,
    *,
    false_positive_cost_minor: int = 75,
    false_negative_cost_multiplier: float = 1.0,
) -> ThresholdMetrics:
    """Evaluate an alert threshold with amount-sensitive missed-fraud cost.

    This is a decision-cost model for portfolio analysis, not a production fraud loss model.
    """

    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    if false_positive_cost_minor < 0 or false_negative_cost_multiplier < 0:
        raise ValueError("cost parameters must be non-negative")

    tp = fp = fn = tn = 0
    missed_fraud_cost = 0.0
    alerts = 0
    for observation in observations:
        predicted = observation.score >= threshold
        alerts += int(predicted)
        if predicted and observation.is_fraud:
            tp += 1
        elif predicted:
            fp += 1
        elif observation.is_fraud:
            fn += 1
            missed_fraud_cost += observation.amount_minor * false_negative_cost_multiplier
        else:
            tn += 1

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    false_positive_rate = fp / (fp + tn) if fp + tn else 0.0
    expected_cost = missed_fraud_cost + fp * false_positive_cost_minor
    alert_rate = alerts / len(observations) if observations else 0.0
    return ThresholdMetrics(
        threshold=threshold,
        precision=precision,
        recall=recall,
        false_positive_rate=false_positive_rate,
        expected_cost_minor=expected_cost,
        alert_rate=alert_rate,
    )


def select_cost_optimal_threshold(
    observations: list[RiskObservation],
    thresholds: list[float] | None = None,
    *,
    false_positive_cost_minor: int = 75,
    false_negative_cost_multiplier: float = 1.0,
) -> ThresholdMetrics:
    candidates = thresholds or [index / 100 for index in range(5, 100, 5)]
    if not candidates:
        raise ValueError("thresholds must not be empty")
    evaluated = [
        evaluate_threshold(
            observations,
            threshold,
            false_positive_cost_minor=false_positive_cost_minor,
            false_negative_cost_multiplier=false_negative_cost_multiplier,
        )
        for threshold in candidates
    ]
    return min(evaluated, key=lambda metric: (metric.expected_cost_minor, -metric.recall))


def calibration_bins(
    observations: list[RiskObservation],
    bin_count: int = 10,
) -> list[CalibrationBin]:
    if bin_count <= 0:
        raise ValueError("bin_count must be positive")

    bins: list[CalibrationBin] = []
    for index in range(bin_count):
        lower = index / bin_count
        upper = (index + 1) / bin_count
        members = [
            observation
            for observation in observations
            if lower <= observation.score < upper
            or (index == bin_count - 1 and observation.score == 1)
        ]
        if not members:
            continue
        bins.append(
            CalibrationBin(
                lower_bound=lower,
                upper_bound=upper,
                count=len(members),
                mean_score=mean(observation.score for observation in members),
                observed_fraud_rate=mean(float(observation.is_fraud) for observation in members),
            )
        )
    return bins


def _bin_share(
    values: list[float],
    lower: float,
    upper: float,
    *,
    include_upper: bool,
    epsilon: float,
) -> float:
    count = sum(
        1
        for value in values
        if lower <= value < upper or (include_upper and value == upper)
    )
    return max(count / len(values), epsilon)


def population_stability_index(
    reference_scores: list[float],
    current_scores: list[float],
    bin_count: int = 10,
    epsilon: float = 1e-6,
) -> float:
    """Compute PSI over fixed probability-score bins.

    PSI is presented as a monitoring signal, not proof of harmful model drift.
    """

    if not reference_scores or not current_scores:
        raise ValueError("both score samples must be non-empty")
    if bin_count <= 0:
        raise ValueError("bin_count must be positive")

    psi = 0.0
    for index in range(bin_count):
        lower = index / bin_count
        upper = (index + 1) / bin_count
        include_upper = index == bin_count - 1
        reference_share = _bin_share(
            reference_scores,
            lower,
            upper,
            include_upper=include_upper,
            epsilon=epsilon,
        )
        current_share = _bin_share(
            current_scores,
            lower,
            upper,
            include_upper=include_upper,
            epsilon=epsilon,
        )
        psi += (current_share - reference_share) * log(current_share / reference_share)
    return psi
