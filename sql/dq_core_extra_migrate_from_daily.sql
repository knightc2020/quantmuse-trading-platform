-- Migrate data from existing daily_quotes table into the new core/extra tables.
-- Safe to run multiple times (upsert semantics).

begin;

-- Core fields
insert into daily_quotes_core (
  trade_date, code, open, high, low, close, volume, amount, pe_ttm, pb
)
select
  trade_date, code, open, high, low, close, volume, amount, pe_ttm, pb
from daily_quotes
on conflict (trade_date, code) do update set
  open   = excluded.open,
  high   = excluded.high,
  low    = excluded.low,
  close  = excluded.close,
  volume = excluded.volume,
  amount = excluded.amount,
  pe_ttm = excluded.pe_ttm,
  pb     = excluded.pb;

-- Extra/enrichment fields
insert into daily_quotes_extra (
  trade_date, code, pre_close, change, pct_chg, change_ratio,
  upper_limit, lower_limit, turnover_ratio, avg_price,
  volume_btin, amount_btin, trans_num,
  post_volume, post_trans_num, post_amount,
  valid_turnover_ratio, swing,
  rel_issue_chg, rel_issue_chg_ratio, rel_market_chg_ratio,
  trade_status, suspension_days, suspension_reason,
  adj_factor, adj_factor2, limit_status,
  last_trade_date, nearest_trade_date, ah_premium_rate,
  total_mv, mv
)
select
  trade_date, code, pre_close, change, pct_chg, change_ratio,
  upper_limit, lower_limit, turnover_ratio, avg_price,
  volume_btin, amount_btin, trans_num,
  post_volume, post_trans_num, post_amount,
  valid_turnover_ratio, swing,
  rel_issue_chg, rel_issue_chg_ratio, rel_market_chg_ratio,
  trade_status, suspension_days, suspension_reason,
  adj_factor, adj_factor2, limit_status,
  last_trade_date, nearest_trade_date, ah_premium_rate,
  total_mv, mv
from daily_quotes
on conflict (trade_date, code) do update set
  pre_close = excluded.pre_close,
  change = excluded.change,
  pct_chg = excluded.pct_chg,
  change_ratio = excluded.change_ratio,
  upper_limit = excluded.upper_limit,
  lower_limit = excluded.lower_limit,
  turnover_ratio = excluded.turnover_ratio,
  avg_price = excluded.avg_price,
  volume_btin = excluded.volume_btin,
  amount_btin = excluded.amount_btin,
  trans_num = excluded.trans_num,
  post_volume = excluded.post_volume,
  post_trans_num = excluded.post_trans_num,
  post_amount = excluded.post_amount,
  valid_turnover_ratio = excluded.valid_turnover_ratio,
  swing = excluded.swing,
  rel_issue_chg = excluded.rel_issue_chg,
  rel_issue_chg_ratio = excluded.rel_issue_chg_ratio,
  rel_market_chg_ratio = excluded.rel_market_chg_ratio,
  trade_status = excluded.trade_status,
  suspension_days = excluded.suspension_days,
  suspension_reason = excluded.suspension_reason,
  adj_factor = excluded.adj_factor,
  adj_factor2 = excluded.adj_factor2,
  limit_status = excluded.limit_status,
  last_trade_date = excluded.last_trade_date,
  nearest_trade_date = excluded.nearest_trade_date,
  ah_premium_rate = excluded.ah_premium_rate,
  total_mv = excluded.total_mv,
  mv = excluded.mv;

commit;

