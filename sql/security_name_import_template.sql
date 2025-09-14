-- Template: Import current name snapshot CSV into security_name_history
-- Usage options:
--   A) psql on your machine (recommended for large CSV)
--      1) Ensure the history table and view exist (run security_name_history_setup.sql once)
--      2) Set snapshot date below (replace YYYY-MM-DD)
--      3) Create/empty staging table and \copy CSV into it
--      4) Run the upsert & range-closing logic
--   B) Supabase Table Editor: create a table security_name_snapshot_tmp with the same columns
--      then import the CSV with UI, set snapshot_date via UPDATE, and run the upsert section.

begin;

-- 1) Staging table for the CSV (code,name) + snapshot_date
create table if not exists security_name_snapshot_tmp (
  code varchar(16) not null,
  name varchar(64) not null,
  snapshot_date date
);

-- optional: start fresh before each import
truncate table security_name_snapshot_tmp;

-- 2) (psql) Import CSV
-- From psql, run something like (replace path):
--   \copy security_name_snapshot_tmp(code,name) from 'D:/path/current_names_2025-09-01.csv' with (format csv, header true, encoding 'UTF8');

-- 3) Set the snapshot date for this batch (edit the date below)
update security_name_snapshot_tmp
set snapshot_date = date '2025-09-01'
where snapshot_date is null;

-- 4) Normalize whitespace
update security_name_snapshot_tmp
set code = trim(code),
    name = trim(name);

-- 5) Close open-ended records that changed name at snapshot_date
update security_name_history h
set valid_to = s.snapshot_date
from security_name_snapshot_tmp s
where h.code = s.code
  and h.valid_to = date '9999-12-31'
  and (trim(h.name) is distinct from trim(s.name));

-- 6) Insert new open-ended rows (new codes or renamed ones)
insert into security_name_history(code, name, valid_from, valid_to, source)
select s.code, s.name, s.snapshot_date, date '9999-12-31', 'snapshot'
from security_name_snapshot_tmp s
left join security_name_history h
  on h.code = s.code
 and h.valid_to = date '9999-12-31'
where h.code is null                       -- new code
   or (trim(h.name) is distinct from s.name); -- renamed

commit;

-- Verification helpers
-- Current (open-ended) names after import:
--   select code, name from security_name_history where valid_to = '9999-12-31' order by code limit 50;
-- Effective name on a given date D:
--   select h.code, h.name from security_name_history h where date '2025-09-01' >= h.valid_from and date '2025-09-01' < h.valid_to;

