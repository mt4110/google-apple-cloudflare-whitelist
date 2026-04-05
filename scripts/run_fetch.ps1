param(
    [string]$MiseBin = $env:MISE_BIN,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"

if (-not $MiseBin) {
    $MiseBin = "mise"
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoDir = Split-Path -Parent $ScriptDir

Push-Location $RepoDir
try {
    & $MiseBin run fetch @RemainingArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
