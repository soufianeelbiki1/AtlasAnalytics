# AtlasAnalytics

AtlasAnalytics is a DuckDB-based payments analytics project built around explicit fact grains, reproducible synthetic data and decision-focused SQL/Python analysis.

The warehouse separates payments from authorization attempts, reversals and reconciliation events so retries do not inflate monetary totals.

## Data model

- `fact_payment` for payment-level amounts and final captured value.
- `fact_authorization` for individual authorization attempts and response outcomes.
- separate reversal and reconciliation facts.
- issuer and currency dimensions.

Current marts cover daily payment activity, issuer performance, decline categories, rolling issuer baselines and reconciliation exceptions.

## Operations dashboard

Generate a standalone HTML dashboard directly from the DuckDB warehouse:

```bash
python -m atlasanalytics.dashboard --output build/atlasanalytics-dashboard.html
```

It includes:

- authorization attempts, approval rate, timeout rate and overall p95 latency;
- issuer performance by currency;
- decline-reason distribution;
- rolling issuer anomaly signals with approval/timeout z-scores.

The HTML contains its CSS and does not require a dashboard server. Values are regenerated from the deterministic synthetic warehouse rather than copied into a static mockup.

## Risk evaluation report

Generate the visual risk report with:

```bash
python -m atlasanalytics.risk_report --output build/atlasanalytics-risk.html
```

The report uses a deterministic scored scenario and a chronological holdout. It shows:

- precision, recall, false-positive rate and alert rate across thresholds;
- the operating point selected by the declared amount-sensitive cost function;
- score-band calibration against observed synthetic fraud rate;
- Population Stability Index (PSI) between the reference period and holdout;
- issuer mix for basic segment context.

The synthetic scenario intentionally contains a mild late-period score shift so the PSI monitoring path is exercised. Cost values are assumptions, and PSI is a distribution-change signal rather than proof that a real model degraded.

## Risk evaluation API

The underlying risk module can also be used independently:

- chronological train/test splitting;
- precision, recall, false-positive rate and alert rate;
- amount-sensitive expected-cost evaluation;
- threshold selection using the declared cost function;
- calibration bins;
- Population Stability Index (PSI) for score-distribution monitoring.

This is evaluation tooling, not a deployed fraud model.

## Synthetic data

The repository generates its own payment and scored-risk data for repeatable tests and analysis. It contains no real PANs, cardholders, merchants or production AtlasPay transactions.

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
python -m atlasanalytics.dashboard --output build/atlasanalytics-dashboard.html
python -m atlasanalytics.risk_report --output build/atlasanalytics-risk.html
```

CI runs on Python 3.11 and 3.12.

## Documentation

`docs/data_dictionary.md` defines the warehouse grains and metric semantics.

## Roadmap

- add date, merchant and channel dimensions;
- add lifecycle/cohort analysis and traffic-weighted rolling baselines;
- add an analyst investigation queue and segment-level monitoring;
- add threshold and calibration breakdowns by issuer/channel after those dimensions are modeled.
