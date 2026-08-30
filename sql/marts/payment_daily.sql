create or replace view mart_payment_daily as
with payment_rollup as (
    select
        cast(created_at as date) as metric_date,
        currency_code,
        count(*) as payments,
        count(*) filter (where final_status = 'captured') as captured_payments,
        count(*) filter (where final_status = 'declined') as declined_payments,
        count(*) filter (where final_status = 'timed_out') as timed_out_payments,
        count(*) filter (where final_status = 'reversed') as reversed_payments,
        sum(amount_minor) as requested_amount_minor,
        sum(amount_minor) filter (where final_status = 'captured') as captured_amount_minor,
        avg(amount_minor) as average_ticket_minor
    from fact_payment
    group by 1, 2
),
authorization_rollup as (
    select
        cast(a.requested_at as date) as metric_date,
        p.currency_code,
        count(*) as authorization_attempts,
        count(*) filter (where a.disposition = 'approved') as approved_attempts,
        count(*) filter (where a.disposition = 'declined') as declined_attempts,
        count(*) filter (where a.disposition = 'timed_out') as timeout_attempts,
        count(*) filter (where a.response_code = '51') as insufficient_funds_declines,
        count(*) filter (where a.response_code = '05') as generic_do_not_honor_declines,
        quantile_cont(a.latency_ms, 0.50) filter (where a.latency_ms is not null) as p50_latency_ms,
        quantile_cont(a.latency_ms, 0.95) filter (where a.latency_ms is not null) as p95_latency_ms
    from fact_authorization a
    join fact_payment p using (payment_id)
    group by 1, 2
),
reversal_rollup as (
    select
        cast(r.created_at as date) as metric_date,
        p.currency_code,
        count(*) as reversals,
        count(*) filter (where r.reason = 'timeout') as timeout_reversals,
        count(*) filter (where r.reason = 'late_response') as late_response_reversals,
        count(*) filter (where r.reason = 'operator') as operator_reversals
    from fact_reversal r
    join fact_payment p using (payment_id)
    group by 1, 2
),
reconciliation_rollup as (
    select
        control_date as metric_date,
        currency_code,
        sum(discrepancy_minor) as reconciliation_discrepancy_minor,
        count(*) filter (where discrepancy_minor <> 0) as reconciliation_exceptions
    from fact_reconciliation
    group by 1, 2
)
select
    p.metric_date,
    p.currency_code,
    p.payments,
    p.captured_payments,
    p.declined_payments,
    p.timed_out_payments,
    p.reversed_payments,
    p.requested_amount_minor,
    coalesce(p.captured_amount_minor, 0) as captured_amount_minor,
    p.average_ticket_minor,
    coalesce(a.authorization_attempts, 0) as authorization_attempts,
    coalesce(a.approved_attempts, 0) as approved_attempts,
    coalesce(a.declined_attempts, 0) as declined_attempts,
    coalesce(a.timeout_attempts, 0) as timeout_attempts,
    case
        when coalesce(a.authorization_attempts, 0) = 0 then null
        else a.approved_attempts::double / a.authorization_attempts
    end as authorization_approval_rate,
    coalesce(a.insufficient_funds_declines, 0) as insufficient_funds_declines,
    coalesce(a.generic_do_not_honor_declines, 0) as generic_do_not_honor_declines,
    a.p50_latency_ms,
    a.p95_latency_ms,
    coalesce(r.reversals, 0) as reversals,
    coalesce(r.timeout_reversals, 0) as timeout_reversals,
    coalesce(r.late_response_reversals, 0) as late_response_reversals,
    coalesce(r.operator_reversals, 0) as operator_reversals,
    coalesce(rec.reconciliation_discrepancy_minor, 0) as reconciliation_discrepancy_minor,
    coalesce(rec.reconciliation_exceptions, 0) as reconciliation_exceptions
from payment_rollup p
left join authorization_rollup a using (metric_date, currency_code)
left join reversal_rollup r using (metric_date, currency_code)
left join reconciliation_rollup rec using (metric_date, currency_code);
