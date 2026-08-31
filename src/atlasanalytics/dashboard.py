from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

import duckdb

from atlasanalytics.warehouse import build_warehouse


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _bar(label: str, value: int, maximum: int) -> str:
    width = 0 if maximum <= 0 else max(2, round(value / maximum * 100))
    return (
        '<div class="bar-row">'
        f'<span>{escape(label)}</span><div class="bar-track"><div class="bar" style="width:{width}%"></div></div>'
        f'<strong>{value:,}</strong></div>'
    )


def build_dashboard_html(connection: duckdb.DuckDBPyConnection) -> str:
    attempts, approved, timed_out, p95_latency = connection.execute(
        """
        select
            count(*),
            count(*) filter (where disposition = 'approved'),
            count(*) filter (where disposition = 'timed_out'),
            coalesce(quantile_cont(latency_ms, 0.95) filter (where latency_ms is not null), 0)
        from fact_authorization
        """
    ).fetchone()
    attempts = int(attempts)
    approved = int(approved)
    timed_out = int(timed_out)
    approval_rate = approved / attempts if attempts else 0.0
    timeout_rate = timed_out / attempts if attempts else 0.0

    issuer_rows = connection.execute(
        """
        select
            issuer_name,
            currency_code,
            sum(authorization_attempts)::bigint as attempts,
            sum(approved_attempts)::bigint as approved,
            sum(timeout_attempts)::bigint as timeouts,
            sum(approved_attempts)::double / nullif(sum(authorization_attempts), 0) as approval_rate,
            max(p95_latency_ms) as peak_daily_p95_latency_ms
        from mart_issuer_daily
        group by issuer_name, currency_code
        order by attempts desc, issuer_name
        """
    ).fetchall()

    decline_rows = connection.execute(
        """
        select decline_reason, sum(decline_attempts)::bigint as attempts
        from mart_decline_daily
        group by decline_reason
        order by attempts desc, decline_reason
        """
    ).fetchall()
    max_declines = max((int(row[1]) for row in decline_rows), default=0)

    anomaly_rows = connection.execute(
        """
        select metric_date, issuer_name, currency_code, anomaly_state,
               approval_rate_zscore, timeout_rate_zscore
        from mart_issuer_baseline
        where anomaly_state <> 'normal'
        order by metric_date desc, issuer_name
        limit 12
        """
    ).fetchall()

    issuer_html = "".join(
        "<tr>"
        f"<td>{escape(str(name))}</td><td>{escape(str(currency))}</td>"
        f"<td>{int(row_attempts):,}</td><td>{_percent(float(rate or 0))}</td>"
        f"<td>{int(timeouts):,}</td><td>{float(latency or 0):.0f} ms</td>"
        "</tr>"
        for name, currency, row_attempts, _approved, timeouts, rate, latency in issuer_rows
    )
    decline_html = "".join(
        _bar(str(reason).replace("_", " ").title(), int(value), max_declines)
        for reason, value in decline_rows
    )
    anomaly_html = "".join(
        "<tr>"
        f"<td>{escape(str(day))}</td><td>{escape(str(name))}</td><td>{escape(str(currency))}</td>"
        f"<td><span class=""badge badge-{escape(str(state))}"">{escape(str(state))}</span></td>"
        f"<td>{'—' if approval_z is None else f'{float(approval_z):.2f}'}</td>"
        f"<td>{'—' if timeout_z is None else f'{float(timeout_z):.2f}'}</td>"
        "</tr>"
        for day, name, currency, state, approval_z, timeout_z in anomaly_rows
    ) or '<tr><td colspan="6">No investigate/critical issuer-day signals in this generated dataset.</td></tr>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AtlasAnalytics — Payments Operations</title>
<style>
:root {{ font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: #172033; background: #f4f6f8; }}
* {{ box-sizing: border-box; }} body {{ margin: 0; }}
main {{ max-width: 1180px; margin: 0 auto; padding: 40px 24px 64px; }}
header {{ margin-bottom: 28px; }} h1 {{ margin: 5px 0 8px; font-size: clamp(2rem, 6vw, 4rem); }}
.sub {{ color: #5b6576; max-width: 760px; line-height: 1.6; }} .note {{ font-size: .82rem; color: #687386; }}
.cards {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin: 24px 0; }}
.card, .panel {{ background: white; border: 1px solid #dfe4ea; border-radius: 14px; box-shadow: 0 8px 24px rgba(20,30,50,.05); }}
.card {{ padding: 18px; }} .card span {{ color: #687386; font-size: .82rem; text-transform: uppercase; letter-spacing: .06em; }}
.card strong {{ display: block; margin-top: 7px; font-size: 1.7rem; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 18px; }} .panel {{ padding: 20px; overflow: auto; }}
h2 {{ margin: 0 0 16px; font-size: 1.15rem; }} table {{ width: 100%; border-collapse: collapse; font-size: .9rem; }}
th, td {{ padding: 10px 8px; text-align: left; border-bottom: 1px solid #edf0f3; white-space: nowrap; }} th {{ color: #687386; font-weight: 600; }}
.bar-row {{ display: grid; grid-template-columns: 150px 1fr 55px; gap: 10px; align-items: center; margin: 13px 0; font-size: .9rem; }}
.bar-track {{ height: 10px; border-radius: 20px; background: #edf0f3; overflow: hidden; }} .bar {{ height: 100%; background: #334155; border-radius: 20px; }}
.badge {{ padding: 3px 8px; border-radius: 999px; font-size: .78rem; background: #eef2f6; }} .badge-critical {{ background: #fee2e2; }} .badge-investigate {{ background: #fef3c7; }}
.full {{ margin-top: 18px; }}
@media (max-width: 850px) {{ .cards {{ grid-template-columns: 1fr 1fr; }} .grid {{ grid-template-columns: 1fr; }} }}
@media (max-width: 520px) {{ .cards {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<main>
<header><div class="note">SYNTHETIC DATA · REPRODUCIBLE DUCKDB WAREHOUSE</div><h1>Payments operations</h1><p class="sub">Authorization health, issuer behavior and decline diagnostics generated directly from AtlasAnalytics marts. Values are from the repository's deterministic synthetic dataset.</p></header>
<section class="cards">
<div class="card"><span>Authorization attempts</span><strong>{attempts:,}</strong></div>
<div class="card"><span>Approval rate</span><strong>{_percent(approval_rate)}</strong></div>
<div class="card"><span>Timeout rate</span><strong>{_percent(timeout_rate)}</strong></div>
<div class="card"><span>Overall p95 latency</span><strong>{float(p95_latency or 0):.0f} ms</strong></div>
</section>
<section class="grid">
<div class="panel"><h2>Issuer performance</h2><table><thead><tr><th>Issuer</th><th>Currency</th><th>Attempts</th><th>Approval</th><th>Timeouts</th><th>Peak daily p95</th></tr></thead><tbody>{issuer_html}</tbody></table></div>
<div class="panel"><h2>Decline mix</h2>{decline_html}</div>
</section>
<section class="panel full"><h2>Issuer anomaly signals</h2><table><thead><tr><th>Date</th><th>Issuer</th><th>Currency</th><th>State</th><th>Approval z</th><th>Timeout z</th></tr></thead><tbody>{anomaly_html}</tbody></table><p class="note">Rolling baselines use prior issuer observations only. A signal is a diagnostic flag, not proof of an outage or model failure.</p></section>
</main>
</body>
</html>"""


def write_dashboard(path: str | Path, connection: duckdb.DuckDBPyConnection | None = None) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    owns_connection = connection is None
    conn = connection or build_warehouse()
    try:
        output.write_text(build_dashboard_html(conn), encoding="utf-8")
    finally:
        if owns_connection:
            conn.close()
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the AtlasAnalytics HTML dashboard")
    parser.add_argument("--output", default="build/atlasanalytics-dashboard.html")
    args = parser.parse_args()
    print(write_dashboard(args.output))


if __name__ == "__main__":
    main()
