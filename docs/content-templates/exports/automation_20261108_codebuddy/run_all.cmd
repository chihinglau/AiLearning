@echo off
rem One-key all-subject entry. Parameters are forwarded to run_all.ps1, e.g.:
rem   run_all.cmd
rem   run_all.cmd -Date 20261108 -Shift 02
rem   run_all.cmd -Action verify -Strict -Date 20261108
rem   run_all.cmd -Action plan -Date 20261108
rem NOTE: import/import-dry/restore are NO LONGER available from this entry.
rem       Use: ops.cmd -Action import -Date 20261108 -ConfirmToken I_KNOW
rem            ops.cmd -Action import-dry -Date 20261108 -ConfirmToken I_KNOW
rem            ops.cmd -Action restore -Date 20261108 -BackupPath "<backup.db>" -ConfirmToken I_KNOW
rem       (separate HUMAN OPS entry backed by db_ops.py; nothing is auto-filled.
rem        It also requires -Date, an existing backup for restore, and an interactive
rem        6-digit confirmation printed at run time.)
rem       _run_daily.py and run_all.ps1 have no DB capability at all.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_all.ps1" %*
