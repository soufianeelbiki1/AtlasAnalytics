# AtlasAnalytics operating brief

AtlasAnalytics is the Data Analyst / Analytics Engineer flagship in the portfolio. It should demonstrate trustworthy metric engineering and decision support, not notebook volume.

## Guardrails

- Synthetic data must always be labeled synthetic and generated reproducibly.
- Never imply access to real AtlasPay production data or real cardholder data.
- Keep payment, authorization-attempt, reversal, reconciliation, and future settlement/event grains explicit.
- Money is stored in integer minor units; do not introduce floating-point monetary accounting.
- Tests must catch grain multiplication, broken reconciliation identities, impossible state combinations, and misleading null-to-zero conversions.
- Prefer executable SQL, database constraints, and reproducible Python pipelines over screenshots.
- Every hiring-facing metric needs a business definition, denominator, caveat, and decision use.
- Rolling anomaly baselines must exclude the current observation and must withhold scores when history is insufficient or variance is zero.

## Current state

- DuckDB-backed local analytical warehouse.
- Deterministic synthetic payment generator with no PII or production records.
- Currency and issuer dimensions.
- Payment, authorization-attempt, reversal, and reconciliation facts.
- Daily payment mart with requested/captured volume, authorization outcomes, response-code taxonomy, latency percentiles, reversals, and reconciliation exceptions.
- Daily issuer mart with approval/timeout rates, decline taxonomy, reversals, and latency.
- Decline mart maps failed attempts into explicit insufficient-funds, do-not-honor, network-timeout, and other families while keeping affected amount explicitly at attempt grain.
- Rolling issuer baseline mart uses prior observations only, requires minimum history, computes approval/timeout z-scores, and surfaces normal/investigate/critical states.
- Measured executive-summary API derives five hiring-facing findings directly from warehouse facts and labels every finding as a synthetic scenario.
- Metric catalog documents grain, denominator, decision use, and caveat for each core KPI.
- Regression tests prove mart totals reconcile to atomic facts, authorization retries do not duplicate payment amount, decline taxonomy covers failed attempts, baselines do not leak the current row, and executive findings come from measured facts.

## Next highest-value slice

Add a versioned date dimension plus synthetic merchant/channel dimensions, cohort/lifecycle marts, rolling 7/30-day business baselines weighted by traffic, and a reproducible CLI that materializes a local `.duckdb` artifact and Markdown executive report. After those contracts stabilize, add the first lightweight operations/executive dashboard and then a leakage-safe fraud/risk evaluation layer.
