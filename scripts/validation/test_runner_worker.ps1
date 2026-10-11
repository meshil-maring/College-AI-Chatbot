# Test worker: shadow every external Docker/Python entry point before invoking a runner.
# Only the guard proxy uses real Python, with all its subprocesses mocked.
$ErrorActionPreference = 'Stop'
$mode = $env:REVIEW_MODE
if ($mode -eq 'remote_host') { $env:DOCKER_HOST = 'tcp://example.invalid:2375' }
if ($mode -eq 'remote_env_context') { $env:DOCKER_CONTEXT = 'remote' }
function Record-Call([object[]]$values) {
    $sanitized = @($values | ForEach-Object { if (([string]$_) -like 'POSTGRES_PASSWORD=*') { 'POSTGRES_PASSWORD=<redacted>' } else { [string]$_ } })
    ConvertTo-Json -InputObject $sanitized -Compress | Add-Content -LiteralPath $env:REVIEW_LOG -Encoding UTF8
}
function docker {
    Record-Call (@('docker') + @($args))
    if ($args[0] -ne '--context' -or $args[1] -ne 'desktop-linux') { throw 'MOCK: unpinned Docker command' }
    $operation = $args[2]
    $global:LASTEXITCODE = 0
    switch ($operation) {
        'run' {
            $token = (@($args | Where-Object { ([string]$_) -like 'collegeai.validation.run=*' })[0] -split '=', 2)[1]
            $purpose = (@($args | Where-Object { ([string]$_) -like 'collegeai.validation.purpose=*' })[0] -split '=', 2)[1]
            @{ token=$token; purpose=$purpose } | ConvertTo-Json | Set-Content -LiteralPath $env:REVIEW_METADATA -Encoding UTF8
            if ($mode -eq 'creation_failed') { $global:LASTEXITCODE = 1; 'a' * 64; return }
            if ($mode -eq 'persistent_name') { 'supabase_db_CollegeAIChatbot' } else { 'a' * 64 }
            return
        }
        'exec' {
            if ($args[3] -ne ('a' * 64)) { throw 'MOCK: unexpected target' }
            if ($args[4] -eq 'pg_isready') { return }
            if ($args[4] -eq 'cat') { '.postgres'; return }
            if ($args[4] -ne 'psql') { throw 'MOCK: unexpected exec operation' }
            # Record only. No SQL binary is invoked and no migration is read/executed.
            return
        }
        'cp' { if ($mode -eq 'migration_copy_failure') { $global:LASTEXITCODE = 1 }; return }
        'stop' { if ($mode -eq 'stop_failed') { $global:LASTEXITCODE = 1 }; return }
        default { throw 'MOCK: unexpected Docker operation' }
    }
}
function python {
    Record-Call (@('python') + @($args))
    if ((Split-Path -Leaf $args[0]) -ne 'disposable_container.py') {
        if ($args[1] -ne ('a' * 64)) { throw 'MOCK: helper target changed' }
        $global:LASTEXITCODE = 0
        return
    }
    if ($args[1] -eq 'validate') {
        switch ($mode) {
            'validator_failure' { $global:LASTEXITCODE = 1; return }
            'validator_empty' { $global:LASTEXITCODE = 0; return }
            'validator_missing' { & '__collegeai_missing_python_command__'; return }
            'validator_mismatch' { $global:LASTEXITCODE = 0; 'c' * 64; return }
        }
    }
    if ($args[1] -eq 'cleanup') {
        if ($mode -eq 'cleanup_empty') { $global:LASTEXITCODE = 0; return }
        if ($mode -eq 'cleanup_mismatch') { $global:LASTEXITCODE = 0; 'c' * 64; return }
    }
    & $env:REVIEW_PYTHON $env:REVIEW_PROXY '--guard-proxy' @args
}
& $env:REVIEW_RUNNER -PythonExecutable python
exit $LASTEXITCODE
