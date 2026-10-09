[CmdletBinding()]
param()
$ErrorActionPreference = 'Continue'
$repository = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$containerName = 'codex-academic-setup-' + [guid]::NewGuid().ToString('N').Substring(0, 10)
$containerId = $null
$verificationExit = 1
if ($env:DOCKER_HOST -or (& docker context show).Trim() -ne 'desktop-linux') { throw 'Only local Docker Desktop is permitted' }
if ((& docker info --format '{{.Name}}').Trim() -ne 'docker-desktop') { throw 'Expected local Docker Desktop engine' }
try {
    $fixturePassword = [guid]::NewGuid().ToString('N')
    $containerId = (& docker run --rm -d --name $containerName --label 'collegeai.academic-setup-verification=true' -e "POSTGRES_PASSWORD=$fixturePassword" public.ecr.aws/supabase/postgres:17.6.1.166).Trim()
    if ($LASTEXITCODE -ne 0 -or $containerId -notmatch '^[a-f0-9]{64}$') { throw 'Could not create disposable database' }
    $ready = $false
    for ($attempt = 0; $attempt -lt 100; $attempt++) {
        & docker exec $containerName pg_isready -U postgres *> $null
        if ($LASTEXITCODE -eq 0 -and ([string](& docker exec $containerName cat /proc/1/comm 2>$null)).Trim() -match '^[.]?postgres') { $ready = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw 'Disposable database did not become ready' }
    & docker cp (Join-Path $repository 'supabase\migrations') "${containerName}:/tmp/migrations"
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy migrations' }
    $migrations = Get-ChildItem -LiteralPath (Join-Path $repository 'supabase\migrations') -Filter '*.sql' | Sort-Object Name
    foreach ($migration in $migrations) {
        Write-Output "REPLAY $($migration.Name)"
        & docker exec $containerName psql -U postgres -d postgres -v ON_ERROR_STOP=1 -q -f "/tmp/migrations/$($migration.Name)"
        if ($LASTEXITCODE -ne 0) { throw "Migration failed: $($migration.Name)" }
    }
    foreach ($fixture in @('academic_setup_sql_lint.sql', 'academic_setup_database.sql', 'faculty_responsibilities_database.sql', 'faculty_attendance_database.sql', 'faculty_tests_database.sql')) {
        & docker cp (Join-Path $PSScriptRoot $fixture) "${containerName}:/tmp/$fixture"
        if ($LASTEXITCODE -ne 0) { throw 'Could not copy contract fixture' }
        & docker exec $containerName psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f "/tmp/$fixture"
        if ($LASTEXITCODE -ne 0) { throw "Database contract failed: $fixture" }
    }
    & (Join-Path $repository 'backend\.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'academic_setup_concurrency.py') $containerName
    if ($LASTEXITCODE -ne 0) { throw 'Academic concurrency contracts failed' }
    Write-Output "DATABASE PASS: $($migrations.Count) migrations; academic, responsibility, attendance and assessment contracts; academic races"
    $verificationExit = 0
} catch { Write-Error $_ }
finally {
    if ($containerId -match '^[a-f0-9]{64}$') {
        & docker stop $containerId | Out-Null
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Disposable verification container cleanup failed' }
    }
}
exit $verificationExit
