param(
  [Parameter()][string]$StartDate = '2005-01-01',
  [Parameter()][string]$EndDate = '2025-09-05',
  [Parameter()][string]$CodesFile = 'codes_all.csv',
  [Parameter()][int]$LimitPerShard = 1500,
  [Parameter()][int]$ShardCount = 4,
  [Parameter()][string]$StartTime = '20:00'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo\..

for ($i=0; $i -lt $ShardCount; $i++) {
  $offset = $i * $LimitPerShard
  $taskName = "DQ-Core-Shard-$i"
  $cmd = "cmd /c set THS_CALL_INTERVAL=1.2 && set THS_BATCH_INTERVAL=1.0 && cd `"$pwd`" && python daily_data_sync.py historical-range --start-date $StartDate --end-date $EndDate --codes-file $CodesFile --limit-codes $LimitPerShard --code-offset $offset >> logs\core_$i.log 2>>&1"
  schtasks /create /tn $taskName /sc ONCE /st $StartTime /RL HIGHEST /TR $cmd /F | Out-Null
  Write-Host "Created task: $taskName (offset=$offset)"
}

Write-Host "Tasks created. You can adjust schedule in Task Scheduler UI or re-run with different -StartTime."

