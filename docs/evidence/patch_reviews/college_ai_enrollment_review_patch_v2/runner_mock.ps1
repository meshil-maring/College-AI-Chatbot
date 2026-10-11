# All external commands are shadowed. This worker never invokes real Docker.
$ErrorActionPreference = 'Stop'
$mode = $env:REVIEW_MODE
if ($mode -eq 'remote_host') { $env:DOCKER_HOST = 'tcp://example.invalid:2375' }
function Record-Call([object[]]$values) {
    ConvertTo-Json -InputObject @($values) -Compress | Add-Content -LiteralPath $env:REVIEW_LOG
}
function docker {
    Record-Call (@('docker') + @($args))
    $global:LASTEXITCODE = 0
    switch ($args[0]) {
        'context' { if ($mode -eq 'remote_context') { 'remote' } else { 'desktop-linux' }; return }
        'info' { if ($mode -eq 'wrong_engine') { 'remote-engine' } else { 'docker-desktop' }; return }
        'run' { if ($mode -eq 'persistent_name') { 'supabase_db_CollegeAIChatbot' } else { 'a' * 64 }; return }
        'exec' {
            if ($args[2] -eq 'pg_isready') { return }
            if ($args[2] -eq 'cat') { 'postgres'; return }
            throw 'MOCK: SQL execution reached'
        }
        'inspect' { 'unowned-persistent-container'; return }
        'cp' { throw 'MOCK: copy reached' }
        'stop' { throw 'MOCK: stopping unowned persistent container reached' }
        default { throw 'MOCK: unexpected Docker command' }
    }
}
function python {
    Record-Call (@('python') + @($args))
    switch ($mode) {
        'validator_failure' { $global:LASTEXITCODE = 1; return }
        'validator_empty' { $global:LASTEXITCODE = 0; return }
        'validator_missing' { & '__collegeai_missing_python_command__'; return }
        default { & $env:REVIEW_PYTHON $env:REVIEW_PROXY '--guard-proxy' @args; return }
    }
}
& $env:REVIEW_RUNNER
exit $LASTEXITCODE
