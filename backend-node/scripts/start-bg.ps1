$ErrorActionPreference = 'Stop'

param(
  [string]$Script = "${PSScriptRoot}\..\src\server.js",
  [string]$Url = 'http://127.0.0.1:3001/api/v1/health',
  [int]$TimeoutSec = 20
)

Write-Host "Starting Node server in background..." -ForegroundColor Cyan
$job = Start-Job -ScriptBlock { param($p) node $p | Out-String } -ArgumentList $Script

$deadline = (Get-Date).AddSeconds($TimeoutSec)
do {
  Start-Sleep -Seconds 2
  try {
    $resp = Invoke-RestMethod -Method GET $Url -TimeoutSec 3
    if ($resp.status -eq 'ok') {
      Write-Host "Server ready at $Url" -ForegroundColor Green
      Write-Host ("Job Id: {0}" -f $job.Id) -ForegroundColor DarkGray
      exit 0
    }
  } catch {
    # keep waiting
  }
} while ((Get-Date) -lt $deadline)

Write-Warning "Server did not become ready within $TimeoutSec seconds. Job Id: $($job.Id)"
exit 1
