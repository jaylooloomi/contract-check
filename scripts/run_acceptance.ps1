# Full acceptance run: check_env -> unit tests -> e2e tests -> eval.
# Usage (repo root):  powershell -ExecutionPolicy Bypass -File scripts\run_acceptance.ps1 [-Python <python.exe>]
# Python resolution: -Python, else active venv ($env:VIRTUAL_ENV), else .venv\, else `py -3.12`.
param([string]$Python = "")
$ErrorActionPreference = "Continue"
Set-Location (Split-Path -Parent $PSScriptRoot)
$pre = @()
if (-not $Python) {
    if ($env:VIRTUAL_ENV) { $Python = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe" }
    elseif (Test-Path ".venv\Scripts\python.exe") { $Python = ".venv\Scripts\python.exe" }
    else { $Python = "py"; $pre = @("-3.12") }
}
$env:PYTHONIOENCODING = "utf-8"
New-Item -ItemType Directory -Force acceptance_logs | Out-Null
$log = "acceptance_logs\acceptance_$(Get-Date -Format yyyyMMdd_HHmmss).log"
$summary = @()
function Invoke-Step($name, [string[]]$a) {
    $t = Get-Date
    "==== $name :: $Python $(($pre + $a) -join ' ')" | Tee-Object -FilePath $log -Append
    & $Python @pre @a 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
    $code = $LASTEXITCODE
    $sec = [int]((Get-Date) - $t).TotalSeconds
    "==== $name exit=$code ${sec}s`n" | Tee-Object -FilePath $log -Append
    $script:summary += ("{0,-10} exit={1}  {2}s" -f $name, $code, $sec)
}
Invoke-Step "check_env" @("scripts/check_env.py")
Invoke-Step "unit" @("-m", "pytest", "tests", "-m", "not e2e", "-q")
Invoke-Step "e2e" @("-m", "pytest", "tests/e2e", "-m", "e2e", "-q")
Invoke-Step "eval" @("eval/run_eval.py")
"==== SUMMARY" | Tee-Object -FilePath $log -Append
$summary | Tee-Object -FilePath $log -Append
"log: $log"
