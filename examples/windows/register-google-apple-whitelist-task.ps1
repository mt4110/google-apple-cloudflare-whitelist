param(
    [string]$RepoPath = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$TaskName = "google-apple-whitelist",
    [string]$MiseBin = "mise",
    [string]$OutputDir = "",
    [int]$Hour = 3,
    [int]$Minute = 17
)

$ErrorActionPreference = "Stop"

$RepoPath = (Resolve-Path $RepoPath).Path
if (-not $OutputDir) {
    $OutputDir = Join-Path $RepoPath "whitelist_output"
}

$RunScript = Join-Path $RepoPath "scripts\run_fetch.ps1"
if (-not (Test-Path $RunScript)) {
    throw "run_fetch.ps1 not found at $RunScript"
}

$PowerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$Arguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", ('"{0}"' -f $RunScript),
    "-MiseBin", ('"{0}"' -f $MiseBin),
    "--output-dir", ('"{0}"' -f $OutputDir)
) -join " "

$Action = New-ScheduledTaskAction -Execute $PowerShellExe -Argument $Arguments
$Trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours($Hour).AddMinutes($Minute))
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Refresh provider allowlist inputs" -Force | Out-Null
Write-Host "Registered task '$TaskName'."
Write-Host "RepoPath : $RepoPath"
Write-Host "MiseBin  : $MiseBin"
Write-Host "OutputDir: $OutputDir"
