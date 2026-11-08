@echo off
rem HUMAN OPS ONLY. DB write entry separated from run_all on 2026-11-08 (4th review).
rem 5th review: -ConfirmToken I_KNOW is necessary but NOT sufficient. Also required:
rem   * explicit -Date <YYYYMMDD> (no default); restore also needs an existing -BackupPath
rem   * interactive confirmation: a one-time 6-digit code printed at run time must be typed back
rem The wrapper does NOT auto-fill any confirmation.
rem   ops.cmd -Action import -Date 20261108 -ConfirmToken I_KNOW
rem   ops.cmd -Action import -Date 20261108 -Overwrite -ConfirmToken I_KNOW
rem   ops.cmd -Action import-dry -Date 20261108 -ConfirmToken I_KNOW
rem   ops.cmd -Action restore -Date 20261108 -BackupPath "<backup.db>" -ConfirmToken I_KNOW
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ops.ps1" %*
