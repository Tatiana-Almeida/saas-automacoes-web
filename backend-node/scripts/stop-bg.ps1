$ErrorActionPreference = 'Stop'

# Attempts to stop the most recent background job running node server.js path
$jobs = Get-Job | Sort-Object Id -Descending
if (-not $jobs) {
  Write-Host "No background jobs found." -ForegroundColor Yellow
  exit 0
}

foreach ($j in $jobs) {
  try {
    $details = Receive-Job -Id $j.Id -Keep -ErrorAction SilentlyContinue | Out-String
    # Stop the job regardless; user asked to stop background
    Stop-Job -Id $j.Id -ErrorAction SilentlyContinue
    Remove-Job -Id $j.Id -ErrorAction SilentlyContinue
  } catch {
    # ignore
  }
}

Write-Host "Background jobs stopped/removed." -ForegroundColor Green
exit 0
