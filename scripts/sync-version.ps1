#requires -Version 5.1
<#
  Sync release version numbers from app\pubspec.yaml (single source of truth).

    versionCode = major * 10000 + minor * 100 + patch * 10 + build
    e.g. 1.0.0+1 -> 10001

  Android computes the same formula in app\android\app\build.gradle.kts.
  HarmonyOS values are written into app\ohos\AppScope\app.json5.

  Usage:
    powershell -ExecutionPolicy Bypass -File scripts\sync-version.ps1
    powershell -ExecutionPolicy Bypass -File scripts\sync-version.ps1 -Check
#>
[CmdletBinding()]
param(
  [switch]$Check
)
$ErrorActionPreference = 'Stop'
$Root = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot '..')).Path } else { (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..')).Path }

$pubspec = Join-Path $Root 'app\pubspec.yaml'
$appJson = Join-Path $Root 'app\ohos\AppScope\app.json5'
foreach ($p in @($pubspec, $appJson)) {
  if (-not (Test-Path -LiteralPath $p)) { throw "file not found: $p" }
}

$match = Select-String -LiteralPath $pubspec -Pattern '^version:\s*(\d+)\.(\d+)\.(\d+)\+(\d+)\s*$' |
  Select-Object -First 1
if (-not $match) { throw 'app\pubspec.yaml has no valid "version: x.y.z+build" line' }

$major = [int]$match.Matches[0].Groups[1].Value
$minor = [int]$match.Matches[0].Groups[2].Value
$patch = [int]$match.Matches[0].Groups[3].Value
$build = [int]$match.Matches[0].Groups[4].Value

$versionName = '{0}.{1}.{2}' -f $major, $minor, $patch
$versionCode = $major * 10000 + $minor * 100 + $patch * 10 + $build
if ($versionCode -lt 1 -or $versionCode -gt 2100000000) {
  throw "versionCode=$versionCode is outside the valid range 1..2100000000"
}

$current = [System.IO.File]::ReadAllText($appJson)
$updated = $current -replace '"versionCode"\s*:\s*\d+', "`"versionCode`": $versionCode"
$updated = $updated -replace '"versionName"\s*:\s*"[^"]*"', "`"versionName`": `"$versionName`""

Write-Host ("[sync-version] pubspec={0}+{1} -> versionName={2} versionCode={3}" -f $versionName, $build, $versionName, $versionCode) -ForegroundColor Cyan
Write-Host '[sync-version] Android versionCode is computed by build.gradle.kts with the same formula' -ForegroundColor Cyan

if ($Check) {
  if ($updated -ne $current) {
    throw 'app\ohos\AppScope\app.json5 is out of sync with app\pubspec.yaml; run scripts\sync-version.ps1'
  }
  Write-Host '[sync-version] OK: versionCode/versionName are consistent across platforms' -ForegroundColor Green
  exit 0
}

if ($updated -ne $current) {
  [System.IO.File]::WriteAllText($appJson, $updated)
  Write-Host '[sync-version] wrote app\ohos\AppScope\app.json5' -ForegroundColor Green
}
else {
  Write-Host '[sync-version] app\ohos\AppScope\app.json5 already up to date' -ForegroundColor Green
}
