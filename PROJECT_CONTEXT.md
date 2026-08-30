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

## Current slice

- DuckDB-backed local analytical warehouse.
- Deterministic synthetic payment generator with no PII or production records.
- Currency and issuer dimensions.
- Payment, authorization-attempt, reversal, and reconciliation facts.
- Daily payment mart with requested/captured volume, authorization outcomes, response-code taxonomy, latency percentiles, reversals, and reconciliation exceptions.
- Daily issuer mart with approval/timeout rates, decline taxonomy, reversals, and latency.
- Regression tests prove mart totals reconcile to atomic facts and authorization retries do not duplicate payment amount.

## Next highest-value slice

Add a versioned `dim_date`, merchant/channel dimensions, an authorization funnel/decline taxonomy model, rolling 7/30-day issuer baselines with anomaly flags, and a CLI that materializes a local `.duckdb` artifact plus an executive summary generated from measured synthetic results. Then add a lightweight dashboard only after metric contracts are stable.
