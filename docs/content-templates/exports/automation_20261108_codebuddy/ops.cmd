@echo off
rem HUMAN OPS ONLY. DB write entry separated from run_all on 2026-11-08 (4th review).
rem 5th review: -ConfirmToken I_KNOW is necessary but NOT sufficient. Also required:
rem   * explicit -Date <YYYYMMDD> (no default); restore also needs an existing -BackupPath
rem   * interactive confirmation: a one-time 6-digit code printed at run time must be typed back
rem The wrapper does NOT auto-fill any confirmation.
rem   ops.cmd -Action import -Date 20261108 -ConfirmToken I_KNOW
rem   ops.cmd -Action import -Date 20261108 -Overwrite -ConfirmToken I_KNOW
rem   ops.cmd -Action import-dry -Date 20261108 -ConfirmToken I_KNOW
rem   ops.cmd -Action import-books -Stamp 20261109 -ConfirmToken I_KNOW        (整册文件)
rem   ops.cmd -Action import-books-dry -Stamp 20261109 -ConfirmToken I_KNOW
rem 2026-11-10 review P1-3: -Subjects / -Grades / -Only pin the batch scope:
rem   ops.cmd -Action import-books-dry -Stamp 20261109 -Grades 1,8 -ConfirmToken I_KNOW
rem   ops.cmd -Action import-books -Stamp 20261109 -Subjects math,chinese -Grades 7,9 -ConfirmToken I_KNOW
rem   ops.cmd -Action restore -Date 20261108 -BackupPath "<backup.db>" -ConfirmToken I_KNOW
rem 2026-11-09 added: import-books / import-books-dry (daily_consolidated 整册入库) and
rem   -Unattended (skip the runtime 6-digit code; still needs -ConfirmToken I_KNOW and
rem   an explicit date; only for user-authorized / unattended runs).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ops.ps1" %*
