create or replace view mart_issuer_daily as
select
    cast(a.requested_at as date) as metric_date,
    p.currency_code,
    p.issuer_id,
    i.issuer_name,
    i.country_code,
    count(*) as authorization_attempts,
    count(*) filter (where a.disposition = 'approved') as approved_attempts,
    count(*) filter (where a.disposition = 'declined') as declined_attempts,
    count(*) filter (where a.disposition = 'timed_out') as timeout_attempts,
    count(*) filter (where a.response_code = '51') as insufficient_funds_declines,
    count(*) filter (where a.response_code = '05') as generic_do_not_honor_declines,
    count(*) filter (where r.reversal_id is not null) as reversed_payments,
    count(*) filter (where r.reason = 'timeout') as timeout_reversals,
    count(*) filter (where r.reason = 'late_response') as late_response_reversals,
    count(*) filter (where r.reason = 'operator') as operator_reversals,
    count(*) filter (where a.disposition = 'approved')::double / count(*) as authorization_approval_rate,
    count(*) filter (where a.disposition = 'timed_out')::double / count(*) as timeout_rate,
    quantile_cont(a.latency_ms, 0.50) filter (where a.latency_ms is not null) as p50_latency_ms,
    quantile_cont(a.latency_ms, 0.95) filter (where a.latency_ms is not null) as p95_latency_ms
from fact_authorization a
join fact_payment p using (payment_id)
join dim_issuer i using (issuer_id)
left join fact_reversal r on r.authorization_id = a.authorization_id
group by 1, 2, 3, 4, 5;
