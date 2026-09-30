[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("start", "status", "reset")]
    [string]$Action,

    [switch]$ConfirmLocalReset
)

$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$configPath = Join-Path $repositoryRoot "supabase\config.toml"

if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw "Local Supabase config not found at the expected repository path."
}

if ($env:DOCKER_HOST) {
    throw "DOCKER_HOST is set; refusing an ambiguous Docker target."
}

$dockerContext = (& docker context show 2>$null).Trim()
if ($LASTEXITCODE -ne 0 -or $dockerContext -ne "desktop-linux") {
    throw "Docker context must be the local desktop-linux context."
}

$dockerName = (& docker info --format "{{.Name}}" 2>$null).Trim()
$dockerOs = (& docker info --format "{{.OSType}}" 2>$null).Trim()
if ($LASTEXITCODE -ne 0 -or $dockerName -ne "docker-desktop" -or $dockerOs -ne "linux") {
    throw "The local Docker Desktop Linux engine is not reachable."
}

$config = Get-Content -Raw -LiteralPath $configPath
$dbPortMatch = [regex]::Match($config, '(?ms)^\[db\]\s.*?^port\s*=\s*(\d+)\s*$')
if (-not $dbPortMatch.Success) {
    throw "The local database port is missing or ambiguous in supabase/config.toml."
}

$dbPort = $dbPortMatch.Groups[1].Value
Write-Output "TARGET=LOCAL"
Write-Output "DOCKER_CONTEXT=$dockerContext"
Write-Output "DATABASE_ENDPOINT=127.0.0.1:$dbPort"

if (Test-Path -LiteralPath (Join-Path $repositoryRoot "supabase\.temp\project-ref")) {
    Write-Output "LINK_METADATA_PRESENT=YES (ignored; this wrapper only invokes local commands)"
}

if ($Action -eq "reset" -and -not $ConfirmLocalReset) {
    throw "Reset requires -ConfirmLocalReset and always uses --local."
}

$supabaseArguments = @(switch ($Action) {
    "start" { @("start") }
    "status" { @("status") }
    "reset" { @("db", "reset", "--local") }
})

Push-Location $repositoryRoot
try {
    & supabase @supabaseArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Supabase local command failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
