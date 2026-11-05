#requires -Version 5.1
<#
  AiLearning (深爱学) dev environment setup.
  Reuses the shared zero-pollution toolchain from the sibling MyLangLean project
  via junctions, and JDK21 from the sibling RetroEmuPouch project (same layout
  as that repo). Nothing is installed system-wide.

  Usage:
    powershell -ExecutionPolicy Bypass -File scripts\setup-env.ps1
  Idempotent: safe to re-run.
#>
[CmdletBinding()]
param(
  [string]$Root = '',
  [string]$SharedTools = ''
)
$ErrorActionPreference = 'Stop'

if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
$Root = (Resolve-Path $Root).Path
$Tools = Join-Path $Root '.tools'
New-Item -ItemType Directory -Force $Tools | Out-Null

if (-not $SharedTools) {
  $SharedTools = Join-Path (Split-Path $Root -Parent) 'MyLangLean\.tools'
}
if (-not (Test-Path $SharedTools)) {
  throw "SharedTools not found: $SharedTools (pass -SharedTools explicitly)"
}

function Write-Step($m) { Write-Host "`n========== $m ==========" -ForegroundColor Cyan }

function Link-Or-Reuse($name, $target) {
  $dst = Join-Path $Tools $name
  if (Test-Path $dst) { Write-Host "exists: .tools\$name"; return }
  $src = Join-Path $target $name
  if (Test-Path $src) {
    New-Item -ItemType Junction -Path $dst -Target $src | Out-Null
    Write-Host "junction: .tools\$name -> $src" -ForegroundColor Green
  }
  else { Write-Warning "missing in shared toolchain: $src" }
}

Write-Step "Reuse shared toolchain: $SharedTools"
foreach ($n in 'jdk17', 'android-sdk', 'flutter', 'flutter_ohos', 'caches') {
  Link-Or-Reuse $n $SharedTools
}

# JDK21: RetroEmuPouch keeps a real copy (Gradle 9.x Kotlin-DSL cold-cache issue).
$jdk21 = Join-Path $Tools 'jdk21'
if (-not (Test-Path (Join-Path $jdk21 'bin\java.exe'))) {
  $retroJdk = Join-Path (Split-Path $Root -Parent) 'RetroEmuPouch\.tools\jdk21'
  if (Test-Path (Join-Path $retroJdk 'bin\java.exe')) {
    New-Item -ItemType Junction -Path $jdk21 -Target $retroJdk | Out-Null
    Write-Host "junction: .tools\jdk21 -> $retroJdk" -ForegroundColor Green
  }
  else {
    Write-Warning 'JDK21 not found; falling back to JDK17 (fine for Gradle 8.x).'
  }
}

# Flutter OHOS project metadata: point at this repo's toolchain.
$localProps = Join-Path $Root 'app\ohos\local.properties'
if (Test-Path $localProps) {
  $flutterSdk = (Join-Path $Tools 'flutter_ohos').Replace('\', '\\')
  $lines = @(
    'sdk.dir=D:/HuaWei/Sdk',
    "flutter.sdk=$flutterSdk",
    'hwsdk.dir=D:\\HuaWei\\DevEco-Studio\\sdk'
  )
  Set-Content -Path $localProps -Value $lines -Encoding ASCII
  Write-Host "updated: app\ohos\local.properties" -ForegroundColor Green
}

Write-Step 'Verify'
$oldEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
foreach ($p in @('jdk21', 'jdk17')) {
  $java = Join-Path (Join-Path $Tools $p) 'bin\java.exe'
  if (Test-Path $java) { cmd /c "`"$java`" -version 2>&1" | Select-Object -First 1 }
}
$adb = Join-Path $Tools 'android-sdk\platform-tools\adb.exe'
if (Test-Path $adb) { cmd /c "`"$adb`" version 2>&1" | Select-Object -First 1 }
$fbat = Join-Path $Tools 'flutter\bin\flutter.bat'
if (Test-Path $fbat) {
  $env:JAVA_HOME = if (Test-Path (Join-Path $Tools 'jdk21\bin\java.exe')) {
    Join-Path $Tools 'jdk21'
  } else { Join-Path $Tools 'jdk17' }
  cmd /c "`"$fbat`" --version 2>&1" | Select-Object -First 1
}
$ErrorActionPreference = $oldEap
Write-Host "`n[DONE] In every new terminal run first: . .\scripts\use-env.ps1   (add -Ohos for HarmonyOS)" -ForegroundColor Green
