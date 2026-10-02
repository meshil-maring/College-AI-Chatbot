[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Assign", "Revoke")]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[^\s@]+@[^\s@]+\.[^\s@]+$')]
    [string]$TargetEmail,

    [Parameter(Mandatory = $true)]
    [ValidateLength(1, 200)]
    [string]$ActorIdentifier,

    [Parameter(Mandatory = $true)]
    [ValidateSet("local", "test")]
    [string]$Environment
)

$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$configPath = Join-Path $repositoryRoot "supabase\config.toml"
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw "Local Supabase config not found."
}
if ($env:DOCKER_HOST) {
    throw "DOCKER_HOST is set; refusing an ambiguous Docker target."
}

$dockerContext = (& docker context show 2>$null).Trim()
$dockerName = (& docker info --format "{{.Name}}" 2>$null).Trim()
$dockerOs = (& docker info --format "{{.OSType}}" 2>$null).Trim()
if (
    $LASTEXITCODE -ne 0 -or
    $dockerContext -ne "desktop-linux" -or
    $dockerName -ne "docker-desktop" -or
    $dockerOs -ne "linux"
) {
    throw "The local Docker Desktop Linux engine is not the active target."
}

Push-Location $repositoryRoot
try {
    $status = (& supabase status -o json | ConvertFrom-Json)
}
finally {
    Pop-Location
}

$apiUrl = [string]$status.API_URL
$serviceRoleKey = [string]$status.SERVICE_ROLE_KEY
if ($apiUrl -ne "http://127.0.0.1:54321") {
    throw "Refusing non-local Supabase API target: $apiUrl"
}
if ([string]::IsNullOrWhiteSpace($serviceRoleKey)) {
    throw "The local service-role key is unavailable."
}

$headers = @{
    apikey = $serviceRoleKey
    Authorization = "Bearer $serviceRoleKey"
    "Content-Type" = "application/json"
}
$functionName = if ($Action -eq "Assign") {
    "phase712_assign_super_admin"
}
else {
    "phase712_revoke_super_admin"
}
$body = @{
    p_target_email = $TargetEmail.Trim().ToLowerInvariant()
    p_actor_identifier = $ActorIdentifier.Trim()
} | ConvertTo-Json

$response = @(Invoke-RestMethod `
    -Method Post `
    -Uri "$apiUrl/rest/v1/rpc/$functionName" `
    -Headers $headers `
    -Body $body)

if ($response.Count -ne 1 -or [string]::IsNullOrWhiteSpace([string]$response[0].result)) {
    throw "The controlled role operation did not return a verifiable result."
}

Write-Output "TARGET=LOCAL"
Write-Output "ENVIRONMENT=$($Environment.ToUpperInvariant())"
Write-Output "ACTION=$($Action.ToUpperInvariant())"
Write-Output "RESULT=$([string]$response[0].result)"
Write-Output "AUDIT_RECORDED=YES"
Write-Output "AUTH_IDENTITY_MODIFIED=NO"
Write-Output "SECRET_LOGGED=NO"

