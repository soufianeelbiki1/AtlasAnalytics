create or replace view mart_issuer_baseline as
with historical as (
    select
        metric_date,
        currency_code,
        issuer_id,
        issuer_name,
        country_code,
        authorization_attempts,
        authorization_approval_rate,
        timeout_rate,
        p95_latency_ms,
        count(*) over baseline_window as baseline_observations,
        avg(authorization_approval_rate) over baseline_window as baseline_approval_rate,
        stddev_pop(authorization_approval_rate) over baseline_window as baseline_approval_stddev,
        avg(timeout_rate) over baseline_window as baseline_timeout_rate,
        stddev_pop(timeout_rate) over baseline_window as baseline_timeout_stddev,
        avg(p95_latency_ms) over baseline_window as baseline_p95_latency_ms
    from mart_issuer_daily
    window baseline_window as (
        partition by currency_code, issuer_id
        order by metric_date
        rows between 7 preceding and 1 preceding
    )
),
scored as (
    select
        *,
        case
            when baseline_observations < 5 or coalesce(baseline_approval_stddev, 0) = 0 then null
            else
                (authorization_approval_rate - baseline_approval_rate)
                / baseline_approval_stddev
        end as approval_rate_zscore,
        case
            when baseline_observations < 5 or coalesce(baseline_timeout_stddev, 0) = 0 then null
            else (timeout_rate - baseline_timeout_rate) / baseline_timeout_stddev
        end as timeout_rate_zscore
    from historical
)
select
    *,
    case
        when abs(coalesce(approval_rate_zscore, 0)) >= 3
          or abs(coalesce(timeout_rate_zscore, 0)) >= 3 then 'critical'
        when abs(coalesce(approval_rate_zscore, 0)) >= 2
          or abs(coalesce(timeout_rate_zscore, 0)) >= 2 then 'investigate'
        else 'normal'
    end as anomaly_state
from scored;
