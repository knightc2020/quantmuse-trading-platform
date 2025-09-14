param(
  [Parameter(Mandatory=$true)][string]$SnapshotCsv,
  [Parameter(Mandatory=$true)][string]$SnapshotDate,  # e.g. 2025-09-01
  [Parameter(Mandatory=$false)][string]$PgUri = $env:PGURI
)

$ErrorActionPreference = 'Stop'
if (-not $PgUri) {
  Write-Error "Please set -PgUri or PGURI env with your Supabase Postgres connection URI."
}

function Invoke-PsqlFile($file, $vars=@{}) {
  $args = @()
  foreach ($k in $vars.Keys) { $args += '-v'; $args += "$k=$($vars[$k])" }
  $args += @('-v','ON_ERROR_STOP=1','-f', $file)
  & psql $PgUri @args
  if ($LASTEXITCODE -ne 0) { throw "psql failed: $file" }
}

function Invoke-PsqlCmd($sql) {
  & psql $PgUri -v ON_ERROR_STOP=1 -c $sql
  if ($LASTEXITCODE -ne 0) { throw "psql failed: $sql" }
}

# 1) Ensure tables/views exist
Invoke-PsqlFile "sql/security_name_history_setup.sql"

# 2) Prepare staging table and import CSV
Invoke-PsqlFile "sql/security_name_import_template.sql"

# Overwrite snapshot_date for this batch
Invoke-PsqlCmd "update security_name_snapshot_tmp set snapshot_date = date '$SnapshotDate' where snapshot_date is null;"

# Import CSV (code,name). Requires psql client access to the CSV path.
& psql $PgUri -v ON_ERROR_STOP=1 -c "\\copy security_name_snapshot_tmp(code,name) from '$SnapshotCsv' with (format csv, header true, encoding 'UTF8')"
if ($LASTEXITCODE -ne 0) { throw "psql copy failed: $SnapshotCsv" }

# 3) Run the upsert logic (steps 5 & 6 in the template)
Invoke-PsqlCmd "update security_name_history h set valid_to = (select snapshot_date from security_name_snapshot_tmp s where s.code=h.code limit 1) where h.valid_to = date '9999-12-31' and exists (select 1 from security_name_snapshot_tmp s where s.code=h.code and trim(h.name) is distinct from trim(s.name));"

Invoke-PsqlCmd "insert into security_name_history(code,name,valid_from,valid_to,source) select s.code, trim(s.name), s.snapshot_date, date '9999-12-31', 'snapshot' from security_name_snapshot_tmp s left join security_name_history h on h.code=s.code and h.valid_to=date '9999-12-31' where h.code is null or trim(h.name) is distinct from trim(s.name);"

Write-Host "Name snapshot imported for $SnapshotDate from $SnapshotCsv."

