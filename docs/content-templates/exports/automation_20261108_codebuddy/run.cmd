@echo off
rem Shortcut for run.ps1. All parameters are forwarded, e.g.:
rem   run.cmd -Subject math -Shift 02 -Date 20261108
rem   run.cmd -Action check -Subject biology -Shift 12
rem   run.cmd -Action commit -Subject math -Grade 1 -Date 20261108 -DryRun
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
