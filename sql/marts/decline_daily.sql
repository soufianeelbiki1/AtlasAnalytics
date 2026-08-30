create or replace view mart_decline_daily as
select
    cast(a.requested_at as date) as metric_date,
    p.currency_code,
    p.issuer_id,
    i.issuer_name,
    coalesce(a.response_code, 'NO_RESPONSE') as response_code,
    case
        when a.disposition = 'timed_out' then 'network_timeout'
        when a.response_code = '51' then 'insufficient_funds'
        when a.response_code = '05' then 'do_not_honor'
        else 'other_decline'
    end as decline_reason,
    count(*) as decline_attempts,
    sum(p.amount_minor) as affected_payment_amount_minor
from fact_authorization a
join fact_payment p using (payment_id)
join dim_issuer i using (issuer_id)
where a.disposition in ('declined', 'timed_out')
group by 1, 2, 3, 4, 5, 6;
