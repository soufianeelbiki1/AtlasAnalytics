# AtlasAnalytics

AtlasAnalytics is a DuckDB-based payments analytics project built around explicit fact grains, reproducible synthetic data and decision-focused SQL/Python analysis.

The warehouse separates payments from authorization attempts, reversals and reconciliation events so retries do not inflate monetary totals.

## Data model

- `fact_payment` for payment-level amounts and final captured value.
- `fact_authorization` for individual authorization attempts and response outcomes.
- separate reversal and reconciliation facts.
- issuer and currency dimensions.

Current marts cover daily payment activity, issuer performance, decline categories, rolling issuer baselines and reconciliation exceptions.

## Risk evaluation

The risk module provides a leakage-safe evaluation path for scored transactions:

- chronological train/test splitting;
- precision, recall, false-positive rate and alert rate;
- amount-sensitive expected-cost evaluation;
- threshold selection using the declared cost function;
- calibration bins;
- Population Stability Index (PSI) for score-distribution monitoring.

This is evaluation tooling, not a deployed fraud model. Cost values are assumptions and PSI is treated as a monitoring signal rather than proof of model failure.

## Synthetic data

The repository generates its own payment data for repeatable tests and analysis. It contains no real PANs, cardholders, merchants or production AtlasPay transactions.

## Example

```python
from atlasanalytics import build_warehouse

connection = build_warehouse()
rows = connection.execute(
    "select * from mart_issuer_daily order by metric_date, issuer_id"
).fetchall()
```

Risk thresholds can be evaluated independently:

```python
from atlasanalytics import evaluate_threshold

metrics = evaluate_threshold(observations, threshold=0.65)
print(metrics.precision, metrics.recall, metrics.expected_cost_minor)
```

## Run and test

```bash
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
pytest -q
```

CI runs on Python 3.11 and 3.12.

## Documentation

`docs/data_dictionary.md` defines the warehouse grains and metric semantics.

## Roadmap

- add date, merchant and channel dimensions;
- add lifecycle/cohort analysis and traffic-weighted rolling baselines;
- generate a temporal holdout risk report with precision-recall and expected-cost curves;
- add an operations/risk dashboard backed directly by the DuckDB warehouse;
- add an analyst investigation queue and segment-level monitoring.
