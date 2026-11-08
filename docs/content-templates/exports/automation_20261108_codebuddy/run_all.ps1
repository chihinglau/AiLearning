<#
  ONE-KEY entry for ALL 9 subjects on a given BATCH_DATE (manual, resumable).

  Action=run (default):
    1) print a READ-ONLY all-subject plan (done / missing / repair / next_section per grade)
    2) print ONE paste-ready prompt for a fresh CodeBuddy session; the session runs all
       subjects, then calls all-verify itself. Re-running this command resumes pending
       grades only; finished files are never rewritten.

  Action=verify : read-only check of all daily JSON files (0 = passed). Add -Strict to
                  require no missing files and no warnings.
  Action=plan   : read-only plan only.
  Action=prompt : print the paste-ready prompt only.
  NOTE (4th review, 2026-11-08): DB write Actions import / import-dry / restore
        were REMOVED from this entry. They now live ONLY in ops.ps1 / ops.cmd,
        which requires an explicit -ConfirmToken I_KNOW (no wrapper auto-fill) and
        is never invoked by a teaching session. _run_daily.py has no DB capability.

  Examples:
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\run_all.ps1"
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\run_all.ps1" -Date 20261108 -Shift 02
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\run_all.ps1" -Action verify -Strict
    ops.cmd -Action import -Date 20261108 -ConfirmToken I_KNOW
    ops.cmd -Action import-dry -Date 20261108 -ConfirmToken I_KNOW
    ops.cmd -Action restore -Date 20261108 -BackupPath "<backup.db>" -ConfirmToken I_KNOW
    (5th review: ops.cmd additionally requires -Date, an existing -BackupPath for
     restore, and an interactive 6-digit confirmation printed at run time)
#>
[CmdletBinding()]
param(
    [ValidateSet('run', 'verify', 'plan', 'prompt')]
    [string]$Action = 'run',
    [string]$Date = (Get-Date -Format 'yyyyMMdd'),
    [ValidateSet('02', '12', '22')]
    [string]$Shift = '02',
    [switch]$Strict,
    [switch]$Json,
    [string]$OutFile = ''
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$Dir = $PSScriptRoot
$CfgPath = Join-Path $Dir 'tasks.json'
$Run = Join-Path $Dir '_run_daily.py'
if (-not (Test-Path $CfgPath)) { throw "tasks.json not found: $CfgPath" }
if (-not (Test-Path $Run)) { throw "_run_daily.py not found: $Run" }
$Cfg = Get-Content -Raw -Encoding UTF8 $CfgPath | ConvertFrom-Json
$Py = $Cfg.paths.python
if (-not (Test-Path $Py)) { throw "Python not found (check paths.python in tasks.json): $Py" }
if ($Date -notmatch '^\d{8}$') { throw "-Date must be YYYYMMDD, got '$Date'" }

$Base = @('--date', $Date)
if ($Json) { $Base += '--json' }

function Invoke-Daily {
    param([string[]]$Arguments)
    & $Py $Run @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed (exit $LASTEXITCODE): $Py $Run $($Arguments -join ' ')"
    }
}

function Save-Prompt {
    param([string]$Text)
    if (-not $OutFile) { return }
    $Target = if ([IO.Path]::IsPathRooted($OutFile)) { $OutFile } else { Join-Path $Dir $OutFile }
    [IO.File]::WriteAllText($Target, $Text + "`n", (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "Prompt saved (UTF-8 no BOM): $Target" -ForegroundColor Green
}

switch ($Action) {
    'plan' {
        Invoke-Daily (@('all-plan') + $Base + @('--shift', $Shift))
    }
    'prompt' {
        $Lines = & $Py $Run all-prompt --date $Date --shift $Shift
        if ($LASTEXITCODE -ne 0) { throw "all-prompt failed (exit $LASTEXITCODE)" }
        $Text = $Lines -join "`n"
        Write-Output $Text
        Save-Prompt $Text
    }
    'verify' {
        $Args2 = @('all-verify') + $Base
        if ($Strict) { $Args2 += '--strict' }
        & $Py $Run @Args2
        $Rc = $LASTEXITCODE
        if ($Rc -eq 0) {
            Write-Host "ALL-VERIFY PASSED (batch $Date)" -ForegroundColor Green
        }
        else {
            Write-Host "ALL-VERIFY NOT PASSED (batch $Date, exit $Rc): see missing/fail/warn above" -ForegroundColor Yellow
        }
        exit $Rc
    }
    'run' {
        Write-Host '=== [1/2] READ-ONLY all-subject plan (safe to re-run) ===' -ForegroundColor Cyan
        Invoke-Daily (@('all-plan') + @('--date', $Date, '--shift', $Shift))
        Write-Host ''
        Write-Host '=== [2/2] PASTE THE PROMPT BELOW INTO A FRESH CodeBuddy SESSION ===' -ForegroundColor Cyan
        Write-Host '=== It runs all 9 subjects, verifies results, and resumes pending grades on re-run. ===' -ForegroundColor Cyan
        $Lines = & $Py $Run all-prompt --date $Date --shift $Shift
        if ($LASTEXITCODE -ne 0) { throw "all-prompt failed (exit $LASTEXITCODE)" }
        $Text = $Lines -join "`n"
        Write-Output $Text
        Write-Host ''
        Write-Host "After the session finishes, confirm with: run_all.cmd -Action verify -Strict -Date $Date" -ForegroundColor Green
        Save-Prompt $Text
    }
}
