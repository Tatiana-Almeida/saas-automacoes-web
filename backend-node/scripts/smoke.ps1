$ErrorActionPreference = 'Stop'
param(
  [string]$BaseUrl = 'http://127.0.0.1:3001',
  [string]$Plan = 'pro'
)

function Invoke-Json($Method, $Url, $Body = $null, $Headers = @{}) {
  if ($Body -ne $null -and -not ($Body -is [string])) {
    $Body = ($Body | ConvertTo-Json -Depth 6)
  }
  return Invoke-RestMethod -Method $Method -Uri $Url -Headers $Headers -ContentType 'application/json' -Body $Body
}

$commonHeaders = @{ 'x-plan' = $Plan }

Write-Host "[1/5] Health check..." -ForegroundColor Cyan
$health = Invoke-Json GET "$BaseUrl/api/v1/health" $null $commonHeaders
if ($health.status -ne 'ok') { throw "Health not ok: $($health | ConvertTo-Json -Depth 6)" }
Write-Host " Health: ok" -ForegroundColor Green

$suffix = Get-Random -Minimum 10000 -Maximum 99999
$email = "smoke_$suffix@example.test"
$password = "T3st!$suffix"

Write-Host "[2/5] Register admin user $email ..." -ForegroundColor Cyan
try {
  $reg = Invoke-Json POST "$BaseUrl/api/v1/auth/register" @{ email = $email; password = $password; role = 'admin' } $commonHeaders
  Write-Host " Registered: $($reg.id)" -ForegroundColor Green
} catch {
  Write-Warning " Register failed (may exist): $($_.Exception.Message)"
}

Write-Host "[3/5] Login to obtain token..." -ForegroundColor Cyan
$login = Invoke-Json POST "$BaseUrl/api/v1/auth/login" @{ email = $email; password = $password } $commonHeaders
$token = $login.token
if (-not $token) { throw "Missing token in response: $($login | ConvertTo-Json -Depth 6)" }
$authHeaders = $commonHeaders.Clone()
$authHeaders['Authorization'] = "Bearer $token"
Write-Host " Token acquired" -ForegroundColor Green

Write-Host "[4/5] Call /users/me ..." -ForegroundColor Cyan
$me = Invoke-Json GET "$BaseUrl/api/v1/users/me" $null $authHeaders
Write-Host (" User: {0} (id={1})" -f $me.email,$me.id) -ForegroundColor Green

Write-Host "[5/5] Call admin ping ..." -ForegroundColor Cyan
$admin = Invoke-Json GET "$BaseUrl/api/v1/auth/admin/ping" $null $authHeaders
if (-not $admin.ok) { throw "Admin ping failed: $($admin | ConvertTo-Json -Depth 6)" }
Write-Host " Admin ping: ok" -ForegroundColor Green

Write-Host "Node backend smoke test passed." -ForegroundColor Green
exit 0
