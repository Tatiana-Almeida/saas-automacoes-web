$ErrorActionPreference = 'Stop'
param(
  [string]$BaseUrl = 'http://localhost:8000'
)

function Invoke-Json($Method, $Url, $Body = $null, $Headers = @{}) {
  if ($Body -ne $null -and -not ($Body -is [string])) {
    $Body = ($Body | ConvertTo-Json -Depth 6)
  }
  return Invoke-RestMethod -Method $Method -Uri $Url -Headers $Headers -ContentType 'application/json' -Body $Body
}

Write-Host "[1/4] Health check..." -ForegroundColor Cyan
$health = Invoke-Json GET "$BaseUrl/api/v1/health"
if ($health.status -ne 'ok') { throw "Health not ok: $($health | ConvertTo-Json -Depth 6)" }
Write-Host " Health: ok" -ForegroundColor Green

$suffix = Get-Random -Minimum 10000 -Maximum 99999
$username = "smoke_$suffix"
$password = "T3st!$suffix"
$email = "$username@example.test"

Write-Host "[2/4] Register user $username ..." -ForegroundColor Cyan
try {
  $reg = Invoke-Json POST "$BaseUrl/api/v1/auth/register" @{ username = $username; email = $email; password = $password }
  Write-Host " Registered: $($reg.id)" -ForegroundColor Green
} catch {
  Write-Warning " Register failed (may exist): $($_.Exception.Message)"
}

Write-Host "[3/4] Login to obtain access token..." -ForegroundColor Cyan
$login = Invoke-Json POST "$BaseUrl/api/v1/auth/token" @{ username = $username; password = $password }
$access = $login.access
if (-not $access) { throw "Missing access token in response: $($login | ConvertTo-Json -Depth 6)" }
Write-Host " Token acquired" -ForegroundColor Green

Write-Host "[4/4] Call /users/me ..." -ForegroundColor Cyan
$me = Invoke-Json GET "$BaseUrl/api/v1/users/me" $null @{ Authorization = "Bearer $access" }
Write-Host (" User: {0} (id={1})" -f $me.username,$me.id) -ForegroundColor Green

Write-Host "Smoke test passed." -ForegroundColor Green
exit 0
