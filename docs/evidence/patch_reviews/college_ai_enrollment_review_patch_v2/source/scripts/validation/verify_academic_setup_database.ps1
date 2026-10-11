[CmdletBinding()]
param()
$ErrorActionPreference = 'Continue' # PostgreSQL NOTICE output is native stderr, not a failure.
$repository = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$purpose = 'academic-setup'
$runToken = [guid]::NewGuid().ToString('N')
$containerName = 'codex-academic-setup-' + $runToken.Substring(0, 12)
$containerId = $null
$verificationExit = 1
$image = 'public.ecr.aws/supabase/postgres:17.6.1.166'

# Refuse remote/overridden Docker targets before creating anything.
if ($env:DOCKER_HOST -or (& docker context show).Trim() -ne 'desktop-linux') { throw 'Only local Docker Desktop desktop-linux is permitted' }
if ((& docker info --format '{{.Name}}').Trim() -ne 'docker-desktop') { throw 'Expected local Docker Desktop engine' }
try {
    $fixturePassword = [guid]::NewGuid().ToString('N')
    $containerId = (& docker run --rm -d --network none --tmpfs /var/lib/postgresql/data:rw,size=536870912 --name $containerName `
        --label 'collegeai.validation.disposable=true' `
        --label "collegeai.validation.run=$runToken" `
        --label "collegeai.validation.purpose=$purpose" `
        -e "POSTGRES_PASSWORD=$fixturePassword" $image).Trim()
    if ($LASTEXITCODE -ne 0 -or $containerId -notmatch '^[a-f0-9]{64}$') { throw 'Could not create isolated disposable database' }

    $ready = $false
    for ($attempt = 0; $attempt -lt 100; $attempt++) {
        & docker exec $containerId pg_isready -U postgres *> $null
        if ($LASTEXITCODE -eq 0 -and ([string](& docker exec $containerId cat /proc/1/comm 2>$null)).Trim() -match '^[.]?postgres') { $ready = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw 'Disposable database did not become ready' }

    # Verify the exact run-owned container has only bounded tmpfs storage, no published ports, and no network.
    $verifiedId = & python -c "import sys; sys.path.insert(0, r'$PSScriptRoot'); from disposable_container import validate_disposable_target; print(validate_disposable_target(sys.argv[1], sys.argv[2], sys.argv[3]))" $containerId $runToken $purpose
    if ($LASTEXITCODE -ne 0 -or $verifiedId.Trim() -ne $containerId) { throw 'Disposable container safety validation failed' }

    & docker cp (Join-Path $repository 'supabase\migrations') "${containerId}:/tmp/migrations"
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy migrations' }
    $migrations = Get-ChildItem -LiteralPath (Join-Path $repository 'supabase\migrations') -Filter '*.sql' | Sort-Object Name
    foreach ($migration in $migrations) {
        Write-Output "REPLAY $($migration.Name)"
        & docker exec $containerId psql -U postgres -d postgres -v ON_ERROR_STOP=1 -q -f "/tmp/migrations/$($migration.Name)"
        if ($LASTEXITCODE -ne 0) { throw "Migration failed: $($migration.Name)" }
    }
    foreach ($fixture in @('academic_setup_sql_lint.sql', 'academic_setup_database.sql', 'faculty_responsibilities_database.sql', 'faculty_attendance_database.sql', 'faculty_tests_database.sql')) {
        & docker cp (Join-Path $PSScriptRoot $fixture) "${containerId}:/tmp/$fixture"
        if ($LASTEXITCODE -ne 0) { throw "Could not copy contract fixture: $fixture" }
        & docker exec $containerId psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f "/tmp/$fixture"
        if ($LASTEXITCODE -ne 0) { throw "Database contract failed: $fixture" }
    }
    & python (Join-Path $PSScriptRoot 'academic_setup_concurrency.py') $containerId $runToken $purpose
    if ($LASTEXITCODE -ne 0) { throw 'Academic concurrency contracts failed' }
    Write-Output "DATABASE PASS: $($migrations.Count) migrations; academic, responsibility, attendance, assessment, and academic-race contracts passed"
    $verificationExit = 0
} catch {
    Write-Error $_
} finally {
    if ($containerId -match '^[a-f0-9]{64}$') {
        $ownedToken = (& docker inspect --format '{{ index .Config.Labels "collegeai.validation.run" }}' $containerId 2>$null).Trim()
        if ($ownedToken -eq $runToken) {
            & docker stop $containerId | Out-Null
            if ($LASTEXITCODE -ne 0) { Write-Warning 'Disposable verification container cleanup failed' }
        } else { Write-Warning 'Cleanup refused because container ownership label did not match this run' }
    }
}
exit $verificationExit
