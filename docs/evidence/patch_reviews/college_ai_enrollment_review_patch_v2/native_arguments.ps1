# Record native argument passing with Python only; never invoke Docker.
[CmdletBinding()]
param([string]$Python)
& $Python -c 'import sys,json; print(json.dumps(sys.argv[1:]))' --tmpfs /var/lib/postgresql/data:rw,size=536870912 --format '{{ index .Config.Labels "collegeai.validation.run" }}'
exit $LASTEXITCODE
