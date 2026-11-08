<#
  One-key entry for the CodeBuddy daily-content workflow (manual, no scheduled task).

  Default (Action=prompt):
    1) run a READ-ONLY plan so you can see today's todos
    2) print a FULL, paste-ready prompt with fixed BATCH_DATE for a fresh CodeBuddy session

  Other actions:
    check   : read-only plan (+ progress for one grade if -Grade is given)
    commit  : after the JSON was written, run validate -> commit -> finish
              (-Grade 1 or -Grades "1,2,3"; add -DryRun to preview)

  Examples:
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\run.ps1" -Subject math -Shift 02
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\run.ps1" -Action check -Subject biology -Shift 12 -Date 20261108
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\run.ps1" -Action commit -Subject math -Grade 1 -Date 20261108 -Minutes 5 -DryRun
#>
[CmdletBinding()]
param(
    [ValidateSet('prompt', 'check', 'commit')]
    [string]$Action = 'prompt',
    [string]$Subject = 'math',
    [ValidateSet('02', '12', '22')]
    [string]$Shift = '02',
    [string]$Date = (Get-Date -Format 'yyyyMMdd'),
    [int]$Grade = 0,
    [string]$Grades = '',
    [int]$Minutes = 5,
    [switch]$DryRun,
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
$Subjects = @($Cfg.tasks | ForEach-Object { $_.subject })
if ($Subjects -notcontains $Subject) { throw "Unknown subject '$Subject'. Valid: $($Subjects -join ', ')" }
if ($Date -notmatch '^\d{8}$') { throw "-Date must be YYYYMMDD, got '$Date'" }

function Invoke-Daily {
    param([string[]]$Arguments)
    & $Py $Run @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed (exit $LASTEXITCODE): $Py $Run $($Arguments -join ' ')"
    }
}

$Base = @('--subject', $Subject, '--date', $Date)
$Extra = @()
if ($DryRun) { $Extra += '--dry-run' }

switch ($Action) {
    'prompt' {
        Write-Host '=== [1/2] READ-ONLY plan (no files written) ===' -ForegroundColor Cyan
        Invoke-Daily (@('plan') + $Base + @('--shift', $Shift))
        if ($Grade -gt 0) {
            Invoke-Daily (@('progress') + @('--subject', $Subject, '--grade', "$Grade"))
        }
        Write-Host ''
        Write-Host '=== [2/2] PASTE THE PROMPT BELOW INTO A FRESH CodeBuddy SESSION ===' -ForegroundColor Cyan
        Write-Host '=== (BATCH_DATE is fixed; this is a single manual run, no scheduled task) ===' -ForegroundColor Cyan
        $Lines = & $Py $Run prompt --subject $Subject --shift $Shift --date $Date
        if ($LASTEXITCODE -ne 0) { throw "prompt generation failed (exit $LASTEXITCODE)" }
        $Text = $Lines -join "`n"
        Write-Output $Text
        if ($OutFile) {
            $Target = if ([IO.Path]::IsPathRooted($OutFile)) { $OutFile } else { Join-Path $Dir $OutFile }
            [IO.File]::WriteAllText($Target, $Text + "`n", (New-Object System.Text.UTF8Encoding($false)))
            Write-Host ''
            Write-Host "Prompt saved (UTF-8 no BOM): $Target" -ForegroundColor Green
        }
    }
    'check' {
        Invoke-Daily (@('plan') + $Base + @('--shift', $Shift))
        if ($Grade -gt 0) {
            Invoke-Daily (@('progress') + @('--subject', $Subject, '--grade', "$Grade"))
        }
    }
    'commit' {
        $List = @()
        if ($Grades) {
            $List = @($Grades -split ',' | ForEach-Object { [int]$_.Trim() })
        }
        elseif ($Grade -gt 0) {
            $List = @($Grade)
        }
        else {
            throw "-Action commit needs -Grade N or -Grades `"1,2,3`""
        }
        foreach ($G in $List) {
            Write-Host "=== validate / commit g$G ===" -ForegroundColor Cyan
            Invoke-Daily (@('validate') + $Base + @('--grade', "$G"))
            Invoke-Daily (@('commit') + $Base + @('--grade', "$G", '--minutes', "$Minutes") + $Extra)
        }
        Write-Host '=== finish (release lock + log summary) ===' -ForegroundColor Cyan
        Invoke-Daily (@('finish') + $Base + @('--done', "$($List.Count)", '--minutes', "$Minutes") + $Extra)
    }
}
