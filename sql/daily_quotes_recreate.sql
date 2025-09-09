-- Recreate daily_quotes table with extended fields aligned to iFinD official schema
-- WARNING: This will drop the existing table. Backup before running if needed.

begin;

drop table if exists daily_quotes cascade;

create table daily_quotes (
  trade_date date not null,
  code varchar(16) not null,

  -- Official style fields
  pre_close numeric(14,4),
  open numeric(14,4),
  high numeric(14,4),
  low numeric(14,4),
  close numeric(14,4),
  change numeric(14,4),
  change_ratio numeric(10,6),
  upper_limit numeric(14,4),
  lower_limit numeric(14,4),
  amount numeric(20,2),
  volume bigint,
  turnover_ratio numeric(10,6),
  rise_day_count integer,
  suspension_flag boolean,
  trade_status varchar(32),

  -- Extra indicators commonly available in history quotes
  avg_price numeric(14,4),
  pe_ttm numeric(14,4),
  pb numeric(14,4),
  total_mv numeric(20,2),
  mv numeric(20,2),

  primary key (trade_date, code)
);

create index if not exists idx_daily_quotes_code_date on daily_quotes (code, trade_date);

commit;

