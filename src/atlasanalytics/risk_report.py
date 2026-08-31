from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

from atlasanalytics.risk import (
    RiskObservation,
    ThresholdMetrics,
    calibration_bins,
    evaluate_threshold,
    population_stability_index,
    select_cost_optimal_threshold,
    temporal_split,
)
from atlasanalytics.risk_synthetic import generate_synthetic_risk_observations

STYLES = """
:root {
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  color: #182033;
  background: #f5f6f8;
}
* { box-sizing: border-box; }
body { margin: 0; }
main { max-width: 1180px; margin: 0 auto; padding: 40px 24px 64px; }
h1 { margin: 5px 0 8px; font-size: clamp(2rem, 6vw, 4rem); }
h2 { margin: 0 0 16px; font-size: 1.15rem; }
.sub { color: #5f6877; max-width: 820px; line-height: 1.6; }
.note { color: #707989; font-size: .82rem; line-height: 1.55; }
.cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 24px 0;
}
.card, .panel {
  background: white;
  border: 1px solid #dfe4ea;
  border-radius: 14px;
  box-shadow: 0 8px 24px rgba(20, 30, 50, .05);
}
.card { padding: 18px; }
.card span { color: #707989; font-size: .8rem; text-transform: uppercase; }
.card strong { display: block; margin-top: 8px; font-size: 1.65rem; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.panel { padding: 20px; overflow: auto; }
.full { margin-top: 18px; }
table { width: 100%; border-collapse: collapse; font-size: .88rem; }
th, td {
  padding: 10px 8px;
  border-bottom: 1px solid #edf0f3;
  text-align: left;
  white-space: nowrap;
}
th { color: #707989; font-weight: 600; }
.best { background: #ecfdf5; }
.bar-row {
  display: grid;
  grid-template-columns: 90px 1fr 70px;
  gap: 10px;
  align-items: center;
  margin: 12px 0;
}
.bar-track { height: 10px; background: #edf0f3; border-radius: 20px; overflow: hidden; }
.bar { height: 100%; background: #334155; border-radius: 20px; }
.calibration {
  display: grid;
  grid-template-columns: 95px 1fr 1fr 65px;
  gap: 10px;
  align-items: center;
  margin: 10px 0;
  font-size: .84rem;
}
.cal-track { height: 8px; background: #edf0f3; border-radius: 20px; overflow: hidden; }
.cal-score { height: 100%; background: #475569; }
.cal-observed { height: 100%; background: #94a3b8; }
@media (max-width: 850px) {
  .cards { grid-template-columns: 1fr 1fr; }
  .grid { grid-template-columns: 1fr; }
}
@media (max-width: 520px) { .cards { grid-template-columns: 1fr; } }
"""


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _money_minor(value: float) -> str:
    return f"{value:,.0f} minor units"


def _risk_counts(observations: list[RiskObservation]) -> tuple[int, int, float]:
    frauds = sum(int(row.is_fraud) for row in observations)
    total = len(observations)
    rate = frauds / total if total else 0.0
    return total, frauds, rate


def _threshold_row(metric: ThresholdMetrics, selected_threshold: float) -> str:
    row_class = ' class="best"' if metric.threshold == selected_threshold else ""
    return (
        f"<tr{row_class}>"
        f"<td>{metric.threshold:.2f}</td>"
        f"<td>{_percent(metric.precision)}</td>"
        f"<td>{_percent(metric.recall)}</td>"
        f"<td>{_percent(metric.false_positive_rate)}</td>"
        f"<td>{_percent(metric.alert_rate)}</td>"
        f"<td>{_money_minor(metric.expected_cost_minor)}</td>"
        "</tr>"
    )


def build_risk_report_html(
    observations: list[RiskObservation] | None = None,
) -> str:
    rows = observations or generate_synthetic_risk_observations()
    train, holdout = temporal_split(rows, train_fraction=0.7)
    thresholds = [round(value / 100, 2) for value in range(20, 91, 5)]
    threshold_rows = [evaluate_threshold(holdout, threshold) for threshold in thresholds]
    selected = select_cost_optimal_threshold(holdout, thresholds)
    bins = calibration_bins(holdout, bin_count=8)
    psi = population_stability_index(
        [row.score for row in train],
        [row.score for row in holdout],
        bin_count=10,
    )

    holdout_total, holdout_frauds, holdout_rate = _risk_counts(holdout)

    threshold_html = "".join(
        _threshold_row(metric, selected.threshold) for metric in threshold_rows
    )

    calibration_html = "".join(
        '<div class="calibration">'
        f"<span>{bucket.lower_bound:.2f}–{bucket.upper_bound:.2f}</span>"
        '<div class="cal-track">'
        f'<div class="cal-score" style="width:{bucket.mean_score * 100:.1f}%"></div>'
        "</div>"
        '<div class="cal-track">'
        f'<div class="cal-observed" style="width:{bucket.observed_fraud_rate * 100:.1f}%"></div>'
        "</div>"
        f"<strong>{bucket.count}</strong>"
        "</div>"
        for bucket in bins
    )

    issuer_counts: dict[str, int] = {}
    for row in holdout:
        issuer_counts[row.issuer_id] = issuer_counts.get(row.issuer_id, 0) + 1
    max_issuer = max(issuer_counts.values(), default=0)
    issuer_html_parts: list[str] = []
    for issuer, count in sorted(issuer_counts.items()):
        width = count / max_issuer * 100 if max_issuer else 0
        issuer_html_parts.append(
            '<div class="bar-row">'
            f"<span>{escape(issuer)}</span>"
            '<div class="bar-track">'
            f'<div class="bar" style="width:{width:.1f}%"></div>'
            "</div>"
            f"<strong>{count}</strong>"
            "</div>"
        )
    issuer_html = "".join(issuer_html_parts)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AtlasAnalytics — Risk Evaluation</title>
<style>{STYLES}</style>
</head>
<body>
<main>
<header>
  <div class="note">SYNTHETIC SCORES · CHRONOLOGICAL HOLDOUT</div>
  <h1>Risk threshold evaluation</h1>
  <p class="sub">
    Threshold trade-offs, calibration and score-distribution monitoring for a deterministic
    synthetic risk scenario. The cost model uses declared assumptions and the split is
    chronological to avoid future-to-past leakage.
  </p>
</header>
<section class="cards">
  <div class="card"><span>Holdout observations</span><strong>{holdout_total:,}</strong></div>
  <div class="card"><span>Holdout fraud rate</span><strong>{_percent(holdout_rate)}</strong></div>
  <div class="card"><span>Selected threshold</span><strong>{selected.threshold:.2f}</strong></div>
  <div class="card"><span>PSI</span><strong>{psi:.3f}</strong></div>
</section>
<section class="grid">
  <div class="panel">
    <h2>Selected operating point</h2>
    <table>
      <tbody>
        <tr><th>Precision</th><td>{_percent(selected.precision)}</td></tr>
        <tr><th>Recall</th><td>{_percent(selected.recall)}</td></tr>
        <tr><th>False-positive rate</th><td>{_percent(selected.false_positive_rate)}</td></tr>
        <tr><th>Alert rate</th><td>{_percent(selected.alert_rate)}</td></tr>
        <tr><th>Expected cost</th><td>{_money_minor(selected.expected_cost_minor)}</td></tr>
        <tr><th>Fraud observations</th><td>{holdout_frauds:,}</td></tr>
      </tbody>
    </table>
    <p class="note">
      The highlighted threshold minimizes the repository's declared missed-fraud and
      false-positive cost model on the holdout. It is not a production loss estimate.
    </p>
  </div>
  <div class="panel">
    <h2>Holdout issuer mix</h2>
    {issuer_html}
    <p class="note">
      Issuer mix is shown so threshold metrics are not read without basic segment context.
    </p>
  </div>
</section>
<section class="panel full">
  <h2>Threshold trade-offs</h2>
  <table>
    <thead>
      <tr><th>Threshold</th><th>Precision</th><th>Recall</th><th>FPR</th>
      <th>Alert rate</th><th>Expected cost</th></tr>
    </thead>
    <tbody>{threshold_html}</tbody>
  </table>
</section>
<section class="grid full">
  <div class="panel">
    <h2>Calibration by score band</h2>
    <div class="note">Band · mean score · observed fraud rate · count</div>
    {calibration_html}
    <p class="note">
      Dark bars show mean score; light bars show observed fraud rate. Large differences are
      a calibration diagnostic, not evidence about a real deployed model.
    </p>
  </div>
  <div class="panel">
    <h2>Population Stability Index</h2>
    <p style="font-size:2.4rem;margin:8px 0 4px"><strong>{psi:.3f}</strong></p>
    <p class="sub">
      PSI compares the score distribution in the earlier training/reference period with the
      chronological holdout. The synthetic generator intentionally introduces a mild late-period
      score shift so the monitoring path is exercised.
    </p>
    <p class="note">
      PSI is a distribution-change signal only. It does not establish that model quality or
      business outcomes degraded.
    </p>
  </div>
</section>
</main>
</body>
</html>"""


def write_risk_report(
    path: str | Path,
    observations: list[RiskObservation] | None = None,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_risk_report_html(observations), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the AtlasAnalytics risk report")
    parser.add_argument("--output", default="build/atlasanalytics-risk.html")
    args = parser.parse_args()
    print(write_risk_report(args.output))


if __name__ == "__main__":
    main()
