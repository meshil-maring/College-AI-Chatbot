[CmdletBinding()]
param([string]$PythonExecutable = 'python')
$ErrorActionPreference = 'Continue' # PostgreSQL NOTICEs use native stderr; check native exit codes explicitly.
$repository = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$validator = Join-Path $PSScriptRoot 'disposable_container.py'
$purpose = 'faculty-assignment'
$runToken = [guid]::NewGuid().ToString('N')
$containerName = 'codex-' + $purpose + '-' + $runToken.Substring(0, 12)
$containerId = $null
$created = $false
$verificationExit = 1
$image = 'public.ecr.aws/supabase/postgres:17.6.1.166'
try {
    $null = Get-Command $PythonExecutable -ErrorAction Stop
    $localResult = & $PythonExecutable $validator local
    $localExit = $LASTEXITCODE
    if ($localExit -ne 0 -or ([string]$localResult).Trim() -cne 'LOCAL PASS') { throw 'Local Docker safety preflight failed' }

    $fixturePassword = [guid]::NewGuid().ToString('N')
    $createdOutput = & docker --context desktop-linux run --pull=never --rm -d --network none `
        --tmpfs '/var/lib/postgresql/data:rw,size=536870912' --name $containerName `
        --label 'collegeai.validation.disposable=true' `
        --label "collegeai.validation.run=$runToken" --label "collegeai.validation.purpose=$purpose" `
        -e 'PGDATA=/var/lib/postgresql/data' -e "POSTGRES_PASSWORD=$fixturePassword" $image
    $creationExit = $LASTEXITCODE
    $containerId = ([string]$createdOutput).Trim()
    if ($creationExit -ne 0 -or $containerId -cnotmatch '^[a-f0-9]{64}$') { throw 'Could not create isolated disposable database' }
    $created = $true

    # Validate ownership/storage before even probing database readiness. Never use a name or fallback.
    $verifiedId = & $PythonExecutable $validator validate $containerId $runToken $purpose
    $validationExit = $LASTEXITCODE
    if ($validationExit -ne 0 -or ([string]$verifiedId).Trim() -cne $containerId) { throw 'Disposable container safety validation failed' }

    $ready = $false
    for ($attempt = 0; $attempt -lt 100; $attempt++) {
        & docker --context desktop-linux exec $containerId pg_isready -U postgres *> $null
        if ($LASTEXITCODE -eq 0) {
            $serverProcess = & docker --context desktop-linux exec $containerId cat /proc/1/comm 2>$null
            if ($LASTEXITCODE -eq 0 -and ([string]$serverProcess).Trim() -match '^[.]?postgres') { $ready = $true; break }
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw 'Disposable database did not become ready' }

    $migrationPath = Join-Path $repository 'supabase\migrations'
    $migrations = @(Get-ChildItem -LiteralPath $migrationPath -Filter '*.sql' -ErrorAction Stop | Sort-Object Name)
    if (-not $migrations.Count) { throw 'No migrations found; refusing an empty verification' }
    & docker --context desktop-linux cp $migrationPath "${containerId}:/tmp/migrations"
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy migrations' }
    foreach ($migration in $migrations) {
        Write-Output "REPLAY $($migration.Name)"
        & docker --context desktop-linux exec $containerId psql -U postgres -d postgres -v ON_ERROR_STOP=1 -q -f "/tmp/migrations/$($migration.Name)"
        if ($LASTEXITCODE -ne 0) { throw "Migration failed: $($migration.Name)" }
    }
    foreach ($fixture in @('faculty_responsibilities_database.sql', 'faculty_attendance_database.sql')) {
        $fixturePath = Join-Path $PSScriptRoot $fixture
        if (-not (Test-Path -LiteralPath $fixturePath -PathType Leaf)) { throw "Missing fixture: $fixture" }
        & docker --context desktop-linux cp $fixturePath "${containerId}:/tmp/$fixture"
        if ($LASTEXITCODE -ne 0) { throw "Could not copy contract fixture: $fixture" }
        & docker --context desktop-linux exec $containerId psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f "/tmp/$fixture"
        if ($LASTEXITCODE -ne 0) { throw "Database contract failed: $fixture" }
    }
    & $PythonExecutable (Join-Path $PSScriptRoot 'faculty_assignment_concurrency.py') $containerId $runToken $purpose
    if ($LASTEXITCODE -ne 0) { throw 'Concurrency contracts failed: faculty_assignment_concurrency.py' }
    Write-Output "DATABASE PASS: $($migrations.Count) migrations; $purpose contracts passed"
    $verificationExit = 0
} catch {
    Write-Error $_
} finally {
    if ($created -and $containerId -cmatch '^[a-f0-9]{64}$') {
        try {
            # Plain JSON inspection in Python avoids PowerShell's native Go-template quoting bug.
            $ownedId = & $PythonExecutable $validator cleanup $containerId $runToken $purpose
            $ownershipExit = $LASTEXITCODE
            if ($ownershipExit -ne 0 -or ([string]$ownedId).Trim() -cne $containerId) { throw 'Cleanup ownership check failed; refusing to stop this target' }
            & docker --context desktop-linux stop --timeout 10 $containerId | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'Disposable verification container cleanup failed' }
        } catch {
            $verificationExit = 1
            Write-Warning ([string]$_)
        }
    }
}
exit $verificationExit
