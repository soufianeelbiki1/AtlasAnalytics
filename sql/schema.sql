create table dim_currency (
    currency_code varchar primary key,
    currency_name varchar not null,
    minor_units integer not null check (minor_units between 0 and 3)
);

create table dim_issuer (
    issuer_id varchar primary key,
    issuer_name varchar not null,
    country_code varchar not null
);

create table fact_payment (
    payment_id varchar primary key,
    created_at timestamp not null,
    currency_code varchar not null references dim_currency(currency_code),
    issuer_id varchar not null references dim_issuer(issuer_id),
    amount_minor bigint not null check (amount_minor > 0),
    final_status varchar not null check (final_status in ('captured', 'declined', 'reversed', 'timed_out'))
);

create table fact_authorization (
    authorization_id varchar primary key,
    payment_id varchar not null references fact_payment(payment_id),
    attempt_no integer not null check (attempt_no > 0),
    requested_at timestamp not null,
    disposition varchar not null check (disposition in ('approved', 'declined', 'timed_out')),
    response_code varchar,
    latency_ms integer check (latency_ms is null or latency_ms >= 0),
    unique (payment_id, attempt_no),
    check ((disposition = 'timed_out' and latency_ms is null) or disposition <> 'timed_out')
);

create table fact_reversal (
    reversal_id varchar primary key,
    payment_id varchar not null unique references fact_payment(payment_id),
    authorization_id varchar not null unique references fact_authorization(authorization_id),
    reason varchar not null check (reason in ('timeout', 'late_response', 'operator')),
    created_at timestamp not null
);

create table fact_reconciliation (
    reconciliation_id varchar primary key,
    control_date date not null,
    currency_code varchar not null references dim_currency(currency_code),
    expected_minor bigint not null,
    observed_minor bigint not null,
    discrepancy_minor bigint not null,
    check (discrepancy_minor = observed_minor - expected_minor),
    unique (control_date, currency_code)
);
