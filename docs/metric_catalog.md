# Metric catalog

All current metric examples are computed from reproducible synthetic data.

| Metric | Grain | Definition | Decision use | Caveat |
| --- | --- | --- | --- | --- |
| Authorization approval rate | day × currency × issuer | approved authorization attempts / all authorization attempts | route and issuer health | attempt-grain; retrying one payment adds another attempt |
| Timeout rate | day × currency × issuer | timed-out attempts / all authorization attempts | network/issuer reliability | timeout means no response in the synthetic scenario, not proven non-delivery |
| Requested amount | day × currency | sum of `fact_payment.amount_minor` | demand / attempted payment volume | payment-grain; not revenue |
| Captured amount | day × currency | payment amount where final status is captured | successfully completed payment value | synthetic status model; no settlement claim |
| Decline attempts | day × currency × issuer × reason | failed authorization attempts mapped to a reason family | investigate avoidable and issuer-specific failure mix | amount attached to this mart is attempt-grain and can repeat when a payment is retried |
| P95 issuer latency | day × currency × issuer | 95th percentile of non-timeout response latency | identify slow routes and compare issuer service | excludes timed-out attempts because no response latency exists |
| Reconciliation exceptions | day × currency | controls where observed amount differs from expected amount | accounting investigation | synthetic control discrepancy, not a production ledger break |
| Approval z-score | day × currency × issuer | current approval rate relative to previous 5–7 issuer observations | anomaly triage | baseline excludes the current observation and is descriptive, not causal |
| Timeout z-score | day × currency × issuer | current timeout rate relative to previous 5–7 issuer observations | reliability anomaly triage | sparse history or zero variance produces no score rather than a fabricated zero |

## Anomaly policy

Rolling issuer baselines use the previous seven available issuer-day observations and explicitly exclude the current row. A score is withheld until at least five historical observations exist. `investigate` begins at an absolute z-score of 2 and `critical` at 3 for approval or timeout rate.

These thresholds are transparent portfolio defaults, not validated production alert thresholds. A production system would calibrate them using historical false-positive cost, incident labels, seasonality, traffic volume, and operational response capacity.
