param(
  [Parameter(Mandatory=$false)][string]$Date = (Get-Date).ToString('yyyy-MM-dd'),
  [Parameter(Mandatory=$false)][string]$CodesFile = "codes_50.txt",
  [Parameter(Mandatory=$false)][int]$Limit = 50
)

$ErrorActionPreference = 'Stop'

# Resolve repo root from script location
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir '..')
Set-Location $repoRoot

# Prepare logs
$logDir = Join-Path $repoRoot 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$logPath = Join-Path $logDir "perf_50-$ts.log"
$errPath = Join-Path $logDir "perf_50-$ts.err.log"

# Optional tuning (can be overridden by existing env)
if (-not $env:THS_CALL_INTERVAL) { $env:THS_CALL_INTERVAL = '1.2' }
if (-not $env:THS_BATCH_INTERVAL) { $env:THS_BATCH_INTERVAL = '1.0' }

# Build arguments
$args = @('daily_data_sync.py', 'daily', '--date', $Date, '--codes-file', $CodesFile, '--limit-codes', $Limit)

# Start detached python process with output redirected to logs
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = 'python'
$psi.Arguments = [string]::Join(' ', $args)
$psi.WorkingDirectory = $repoRoot
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $psi
$null = $proc.Start()

# Async log piping
$outStream = New-Object System.IO.StreamWriter($logPath, $true)
$errStream = New-Object System.IO.StreamWriter($errPath, $true)
$proc.BeginOutputReadLine()
$proc.BeginErrorReadLine()
$proc.add_OutputDataReceived({ param($s,$e) if ($e.Data) { $outStream.WriteLine($e.Data) } })
$proc.add_ErrorDataReceived({ param($s,$e) if ($e.Data) { $errStream.WriteLine($e.Data) } })

# Write PID file
$pidFile = Join-Path $logDir 'perf_50.pid'
Set-Content -Path $pidFile -Value $proc.Id
"Started perf test. PID=$($proc.Id). Logs: $logPath / $errPath" | Tee-Object -FilePath (Join-Path $logDir 'perf_50.last')

# Detach: do not WaitForExit; flush and close after short delay
Start-Sleep -Seconds 1
$outStream.Flush(); $errStream.Flush();
$outStream.Close(); $errStream.Close();

