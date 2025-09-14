-- Security name dimension (history) without changing core ingestion
-- Execute in Supabase SQL editor

begin;

-- 1) History table (SCD Type-2 by effective date range)
create table if not exists security_name_history (
  code varchar(16) not null,
  name varchar(64) not null,
  valid_from date not null,
  valid_to date not null default '9999-12-31',
  source varchar(64),
  primary key (code, valid_from)
);

create index if not exists idx_sec_name_hist_code_from_to
  on security_name_history(code, valid_from, valid_to);

-- Optional safety (commented for portability on hosted Postgres)
-- ensure valid_to >= valid_from
-- Postgres (incl. Supabase) does not support IF NOT EXISTS on ADD CONSTRAINT prior to v16.
-- Use a safe DO block to add the constraint only if missing.
do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'chk_name_range'
      and conrelid = 'security_name_history'::regclass
  ) then
    alter table security_name_history
      add constraint chk_name_range
      check (valid_to >= valid_from);
  end if;
end $$;

-- If your instance allows extensions, you can prevent overlapping ranges per code
-- create extension if not exists btree_gist;
-- alter table security_name_history
--   add constraint if not exists ex_name_no_overlap
--   exclude using gist (
--     code with =,
--     daterange(valid_from, valid_to, '[]') with &&
--   );

-- 2) Convenience view: join core quotes with the name effective on trade_date
create or replace view daily_quotes_core_with_name as
select c.*, n.name
from daily_quotes_core c
left join lateral (
  select s.name
  from security_name_history s
  where s.code = c.code
    and c.trade_date >= s.valid_from
    and c.trade_date <  s.valid_to
  order by s.valid_from desc
  limit 1
) n on true;

commit;

-- Usage notes:
-- - Seed the table with a current snapshot (code,name) using a very early valid_from, e.g. 1990-01-01
--   insert into security_name_history(code,name,valid_from)
--   values ('000001.SZ','平安银行','1990-01-01')
--   on conflict do nothing;
-- - When a rename happens at date D:
--   update security_name_history set valid_to = 'D'
--     where code='000001.SZ' and valid_to='9999-12-31';
--   insert into security_name_history(code,name,valid_from)
--     values ('000001.SZ','新名称','D');
-- - Query with name:
--   select * from daily_quotes_core_with_name
--     where trade_date between '2025-09-01' and '2025-09-05' and code='000001.SZ';
