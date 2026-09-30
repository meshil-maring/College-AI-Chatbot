[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$password = $env:COLLEGEAI_LOCAL_DEMO_PASSWORD
if ([string]::IsNullOrWhiteSpace($password) -or $password.Length -lt 8) {
    throw "Set COLLEGEAI_LOCAL_DEMO_PASSWORD to an ephemeral local-only password of at least 8 characters."
}

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

$adminHeaders = @{
    apikey = $serviceRoleKey
    Authorization = "Bearer $serviceRoleKey"
    "Content-Type" = "application/json"
}

$restHeaders = @{
    apikey = $serviceRoleKey
    Authorization = "Bearer $serviceRoleKey"
    "Content-Type" = "application/json"
    Prefer = "resolution=merge-duplicates,return=representation"
}

$demoUsers = @(
    @{
        id = "30000000-0000-0000-0000-000000000102"
        email = "admin.demo@collegeai.local"
        first_name = "Demo"
        last_name = "Admin"
    },
    @{
        id = "30000000-0000-0000-0000-000000000103"
        email = "student2.demo@collegeai.local"
        first_name = "Jane"
        last_name = "Doe"
    },
    @{
        id = "30000000-0000-0000-0000-000000000104"
        email = "student3.demo@collegeai.local"
        first_name = "Alice"
        last_name = "Smith"
    }
)

$existingResponse = Invoke-RestMethod `
    -Method Get `
    -Uri "$apiUrl/auth/v1/admin/users?page=1&per_page=1000" `
    -Headers $adminHeaders
$existingUsers = @($existingResponse.users)
$created = 0
$reused = 0

foreach ($demo in $demoUsers) {
    $authUser = $existingUsers | Where-Object { $_.email -eq $demo.email } | Select-Object -First 1
    if ($null -eq $authUser) {
        $createBody = @{
            email = $demo.email
            password = $password
            email_confirm = $true
            user_metadata = @{
                first_name = $demo.first_name
                last_name = $demo.last_name
                local_demo = $true
            }
        } | ConvertTo-Json -Depth 4
        $authUser = Invoke-RestMethod `
            -Method Post `
            -Uri "$apiUrl/auth/v1/admin/users" `
            -Headers $adminHeaders `
            -Body $createBody
        $created++
    }
    else {
        $reused++
    }

    if ([string]::IsNullOrWhiteSpace([string]$authUser.id)) {
        throw "GoTrue did not return an id for $($demo.email)."
    }

    $publicBody = @(@{
        id = $demo.id
        auth_user_id = [string]$authUser.id
        email = $demo.email
        first_name = $demo.first_name
        last_name = $demo.last_name
        display_name = "$($demo.first_name) $($demo.last_name)"
        status = "active"
    }) | ConvertTo-Json -Depth 3
    $publicRows = @(Invoke-RestMethod `
        -Method Post `
        -Uri "$apiUrl/rest/v1/users?on_conflict=id" `
        -Headers $restHeaders `
        -Body $publicBody)

    if ($publicRows.Count -ne 1 -or [string]$publicRows[0].auth_user_id -ne [string]$authUser.id) {
        throw "public.users mapping verification failed for $($demo.email)."
    }

    $loginBody = @{
        email = $demo.email
        password = $password
    } | ConvertTo-Json
    $session = Invoke-RestMethod `
        -Method Post `
        -Uri "$apiUrl/auth/v1/token?grant_type=password" `
        -Headers @{ apikey = $serviceRoleKey; "Content-Type" = "application/json" } `
        -Body $loginBody
    if ([string]::IsNullOrWhiteSpace([string]$session.access_token)) {
        throw "Local password login validation failed for $($demo.email)."
    }
}

Write-Output "TARGET=LOCAL"
Write-Output "AUTH_USERS_CREATED=$created"
Write-Output "AUTH_USERS_REUSED=$reused"
Write-Output "PUBLIC_USER_MAPPINGS_VERIFIED=$($demoUsers.Count)"
Write-Output "PASSWORD_LOGGED=NO"
