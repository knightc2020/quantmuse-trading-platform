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
  pct_chg numeric(10,6),
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

  -- Extended fields from THS_BD basic indicators
  amount_btin numeric(20,2),            -- 成交额(含大宗交易)
  volume_btin bigint,                   -- 成交量(含大宗交易)
  trans_num bigint,                     -- 成交笔数
  post_volume bigint,                   -- 盘后成交量
  post_trans_num bigint,                -- 盘后成交笔数
  post_amount numeric(20,2),            -- 盘后成交额
  valid_turnover_ratio numeric(10,6),   -- 有效换手率
  swing numeric(10,6),                  -- 振幅
  rel_issue_chg numeric(14,4),          -- 相对发行价涨跌
  rel_issue_chg_ratio numeric(10,6),    -- 相对发行价涨跌幅
  rel_market_chg_ratio numeric(10,6),   -- 相对大盘涨跌幅
  suspension_days integer,              -- 连续停牌天数
  suspension_reason varchar(128),       -- 停牌原因
  adj_factor numeric(18,8),             -- 复权因子
  adj_factor2 numeric(18,8),            -- 复权因子2
  limit_status varchar(32),             -- 涨跌停状态
  last_trade_date date,                 -- 最近交易日
  nearest_trade_date date,              -- 指定日相近交易日
  ah_premium_rate numeric(12,6),        -- AH股溢价率

  primary key (trade_date, code)
);

create index if not exists idx_daily_quotes_code_date on daily_quotes (code, trade_date);

commit;
