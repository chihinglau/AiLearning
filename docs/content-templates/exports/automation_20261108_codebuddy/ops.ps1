<#
  HUMAN OPS ONLY - the DB write entry, separated from run_all.ps1 on 2026-11-08
  (4th review). 5th review hardened the gate: -ConfirmToken alone is NO LONGER
  sufficient. Three gates must all pass:

    1) -ConfirmToken I_KNOW (explicit, never auto-filled)
    2) -Date <YYYYMMDD> must be passed explicitly (no Get-Date default); for
       restore, -BackupPath must also point to an existing backup file
    3) an INTERACTIVE confirmation: a fresh 6-digit code is printed at run time
       and must be typed back at the console. It cannot be copied from any
       example, script or prompt.

  Examples (the 6-digit code is printed at run time, never in this header):
    ops.cmd -Action import -Date 20261108 -ConfirmToken I_KNOW
    ops.cmd -Action import -Date 20261108 -Overwrite -ConfirmToken I_KNOW
    ops.cmd -Action import-dry -Date 20261108 -ConfirmToken I_KNOW
    ops.cmd -Action import-books -Stamp 20261109 -ConfirmToken I_KNOW
    ops.cmd -Action import-books-dry -Stamp 20261109 -ConfirmToken I_KNOW
    ops.cmd -Action import-books-dry -Stamp 20261109 -Grades 1,8 -ConfirmToken I_KNOW
    ops.cmd -Action restore -Date 20261108 -BackupPath "<backup.db>" -ConfirmToken I_KNOW
                  (backup path comes from import_report_*.json)

  import-books / import-books-dry (added 2026-11-09): the whole-book files under
  `daily_consolidated` (`*_<Stamp>_book.json`) are NOT in the `daily` tree, so
  `-Action import -Date` can never pick them up. They get their own Action
  (validate -> backup -> dry-run -> import -> per-book stem check -> report).

  -Unattended: skips the runtime 6-digit code, for "user explicitly authorized in
  this session, assistant executes" or unattended runs. The other two gates
  (explicit -ConfirmToken I_KNOW, explicit date) stay. Backup is still created.
  Teaching/generation sessions must never call this script at all.

  Teaching sessions must never call this file; see the 01 / 02 prompt docs.
#>
[CmdletBinding()]
param(
    [ValidateSet('import', 'import-dry', 'import-books', 'import-books-dry', 'restore')]
    [string]$Action = 'import',
    [string]$Date = '',
    [string]$Stamp = '',
    [string]$BackupPath = '',
    [string]$ConfirmToken = '',
    [string]$Subjects = '',
    [string]$Grades = '',
    [string]$Only = '',
    [switch]$Overwrite,
    [switch]$Unattended
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$Dir = $PSScriptRoot
$CfgPath = Join-Path $Dir 'tasks.json'
$Ops = Join-Path $Dir 'db_ops.py'
if (-not (Test-Path $CfgPath)) { throw "tasks.json not found: $CfgPath" }
if (-not (Test-Path $Ops)) { throw "db_ops.py not found: $Ops" }
if ($ConfirmToken -ne 'I_KNOW') {
    throw "Refusing DB write: pass -ConfirmToken I_KNOW explicitly (the wrapper no longer fills it in)."
}
$Cfg = Get-Content -Raw -Encoding UTF8 $CfgPath | ConvertFrom-Json
$Py = $Cfg.paths.python
if (-not (Test-Path $Py)) { throw "Python not found (check paths.python in tasks.json): $Py" }
if ($Date -notmatch '^\d{8}$' -and $Action -in @('import', 'import-dry')) {
    throw "-Date must be an explicit YYYYMMDD batch date (no default), got '$Date'"
}
if ($Stamp -and $Stamp -notmatch '^\d{8}$') {
    throw "-Stamp must be YYYYMMDD, got '$Stamp'"
}

switch ($Action) {
    'import' {
        $OpsArgs = @('import', '--date', $Date, '--confirm', $ConfirmToken)
        if ($Overwrite) { $OpsArgs += '--overwrite' }
    }
    'import-dry' {
        $OpsArgs = @('import', '--date', $Date, '--dry-run', '--confirm', $ConfirmToken)
    }
    'import-books' {
        # whole-book import: daily_consolidated/**/*_<Stamp>_book.json (no -Stamp = every book)
        # 2026-11-10 review P1-3: -Subjects/-Grades/-Only pin validation scope == import scope.
        $OpsArgs = @('import-books', '--confirm', $ConfirmToken)
        if ($Stamp) { $OpsArgs += @('--stamp', $Stamp) }
        if ($Subjects) { $OpsArgs += @('--subjects', $Subjects) }
        if ($Grades) { $OpsArgs += @('--grades', $Grades) }
        if ($Only) { $OpsArgs += @('--only', $Only) }
        if ($Overwrite) { $OpsArgs += '--overwrite' }
    }
    'import-books-dry' {
        $OpsArgs = @('import-books', '--dry-run', '--confirm', $ConfirmToken)
        if ($Stamp) { $OpsArgs += @('--stamp', $Stamp) }
        if ($Subjects) { $OpsArgs += @('--subjects', $Subjects) }
        if ($Grades) { $OpsArgs += @('--grades', $Grades) }
        if ($Only) { $OpsArgs += @('--only', $Only) }
    }
    'restore' {
        if (-not $BackupPath) { throw "-Action restore needs -BackupPath <backup.db>" }
        if (-not (Test-Path -LiteralPath $BackupPath -PathType Leaf)) {
            throw "-BackupPath does not exist, refusing to guess a backup: $BackupPath"
        }
        Write-Host "RESTORE will overwrite the current database with: $BackupPath" -ForegroundColor Yellow
        $OpsArgs = @('restore', '--backup', $BackupPath, '--force', '--confirm', $ConfirmToken)
    }
}

$Nonce = [string](Get-Random -Minimum 100000 -Maximum 1000000)
$BackupDisplay = if ($BackupPath) { $BackupPath } else { '(n/a)' }
$OpsDisplay = $OpsArgs -join ' '
Write-Host ''
Write-Host '=== HUMAN DB-WRITE CONFIRMATION (5th review) ===' -ForegroundColor Yellow
Write-Host "  Action      : $Action"
Write-Host "  -Date       : $Date"
Write-Host "  -Stamp      : $Stamp"
Write-Host "  -Subjects   : $Subjects"
Write-Host "  -Grades     : $Grades"
Write-Host "  -Only       : $Only"
Write-Host "  -BackupPath : $BackupDisplay"
Write-Host "  Command     : $OpsDisplay"
if ($Unattended) {
    # ASCII-only on purpose: this file is UTF-8 without BOM and cmd launches Windows
    # PowerShell 5.1, which decodes no-BOM scripts as ANSI (CJK would turn into mojibake).
    Write-Host '  -Unattended : skip the runtime 6-digit code (assistant / unattended path).' -ForegroundColor Red
    Write-Host '                Backup is still created first. Use only when the user has explicitly' -ForegroundColor Red
    Write-Host '                authorized this DB write in this session. Teaching sessions: forbidden.' -ForegroundColor Red
}
else {
    Write-Host "  One-time confirmation code (never stored in docs): $Nonce" -ForegroundColor Cyan
    $Answer = Read-Host 'Type the 6-digit code shown above to proceed'
    if ($Answer -ne $Nonce) {
        throw "Refusing DB write: interactive confirmation failed (copying -ConfirmToken I_KNOW from an example is no longer enough)."
    }
}

& $Py $Ops @OpsArgs
if ($LASTEXITCODE -ne 0) {
    throw "Ops command failed (exit $LASTEXITCODE): $Py $Ops $OpsDisplay"
}
