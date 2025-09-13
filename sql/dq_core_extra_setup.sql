-- Set up dual-table storage for daily quotes: core (stable fields) + extra (enrichment fields)
-- Execute this in Supabase SQL editor.

begin;

create table if not exists daily_quotes_core (
  trade_date date not null,
  code varchar(16) not null,
  open numeric(14,4),
  high numeric(14,4),
  low numeric(14,4),
  close numeric(14,4),
  volume bigint,
  amount numeric(20,2),
  pe_ttm numeric(14,4),
  pb numeric(14,4),
  primary key (trade_date, code)
);

create index if not exists idx_dq_core_code_date on daily_quotes_core(code, trade_date);

create table if not exists daily_quotes_extra (
  trade_date date not null,
  code varchar(16) not null,
  pre_close numeric(14,4),
  change numeric(14,4),
  pct_chg numeric(10,6),
  change_ratio numeric(10,6),
  upper_limit numeric(14,4),
  lower_limit numeric(14,4),
  turnover_ratio numeric(10,6),
  avg_price numeric(14,4),
  volume_btin bigint,
  amount_btin numeric(20,2),
  trans_num bigint,
  post_volume bigint,
  post_trans_num bigint,
  post_amount numeric(20,2),
  valid_turnover_ratio numeric(10,6),
  swing numeric(10,6),
  rel_issue_chg numeric(14,4),
  rel_issue_chg_ratio numeric(10,6),
  rel_market_chg_ratio numeric(10,6),
  trade_status varchar(32),
  suspension_days integer,
  suspension_reason varchar(128),
  adj_factor numeric(18,8),
  adj_factor2 numeric(18,8),
  limit_status varchar(32),
  last_trade_date date,
  nearest_trade_date date,
  ah_premium_rate numeric(12,6),
  total_mv numeric(20,2),
  mv numeric(20,2),
  primary key (trade_date, code)
);

create index if not exists idx_dq_extra_code_date on daily_quotes_extra(code, trade_date);

-- Optional: if TimescaleDB is enabled, convert core table to hypertable
-- select create_hypertable('daily_quotes_core','trade_date', if_not_exists => true);

create or replace view daily_quotes_full as
select
  c.trade_date, c.code,
  c.open, c.high, c.low, c.close, c.volume, c.amount, c.pe_ttm, c.pb,
  e.pre_close, e.change, e.pct_chg, e.change_ratio,
  e.upper_limit, e.lower_limit, e.turnover_ratio, e.avg_price,
  e.volume_btin, e.amount_btin, e.trans_num,
  e.post_volume, e.post_trans_num, e.post_amount,
  e.valid_turnover_ratio, e.swing,
  e.rel_issue_chg, e.rel_issue_chg_ratio, e.rel_market_chg_ratio,
  e.trade_status, e.suspension_days, e.suspension_reason,
  e.adj_factor, e.adj_factor2, e.limit_status,
  e.last_trade_date, e.nearest_trade_date, e.ah_premium_rate,
  e.total_mv, e.mv
from daily_quotes_core c
left join daily_quotes_extra e
  on c.trade_date = e.trade_date and c.code = e.code;

commit;

