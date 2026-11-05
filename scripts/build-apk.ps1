#requires -Version 5.1
<#
  Build the AiLearning (深爱学) Android APK with the shared (zero-pollution) toolchain.

  Usage:
    powershell -ExecutionPolicy Bypass -File scripts\build-apk.ps1
    powershell -ExecutionPolicy Bypass -File scripts\build-apk.ps1 -DebugBuild -SplitPerAbi
    powershell -ExecutionPolicy Bypass -File scripts\build-apk.ps1 -BuildAab        # Google Play / 华为 AAB

  -DebugBuild     Build a debug APK instead of release.
  -SplitPerAbi    Emit one APK per ABI instead of a fat APK.
  -BuildAab       Build an Android App Bundle (.aab) instead of APK.
  -NoPubGet       Skip `flutter pub get` (use when deps already resolved).
  -ApiBaseUrl     Override the backend base URL baked into the app (default http://10.0.2.2:18080).
#>
[CmdletBinding()]
param(
  [switch]$DebugBuild,
  [switch]$SplitPerAbi,
  [switch]$BuildAab,
  [switch]$NoPubGet,
  [string]$ApiBaseUrl = 'http://10.0.2.2:18080'
)
$ErrorActionPreference = 'Stop'
$Root  = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot '..')).Path } else { (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..')).Path }
$Tools = Join-Path $Root '.tools'

$jdk = Join-Path $Tools 'jdk21'
if (-not (Test-Path (Join-Path $jdk 'bin\java.exe'))) { $jdk = Join-Path $Tools 'jdk17' }

$env:AIL_ROOT         = $Root
$env:JAVA_HOME        = $jdk
$env:ANDROID_HOME     = Join-Path $Tools 'android-sdk'
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:PUB_CACHE        = Join-Path $Tools 'caches\pub-cache'
$env:GRADLE_USER_HOME = Join-Path $Tools 'caches\gradle'
$env:FLUTTER_STORAGE_BASE_URL = 'https://storage.flutter-io.cn'
$env:PUB_HOSTED_URL   = 'https://pub.flutter-io.cn'
$env:Path = ((@(
    (Join-Path $env:JAVA_HOME 'bin'),
    (Join-Path $Tools 'flutter\bin'),
    (Join-Path $Tools 'android-sdk\platform-tools'),
    (Join-Path $Tools 'android-sdk\cmdline-tools\latest\bin')
  ) | Where-Object { Test-Path $_ } | Select-Object -Unique) -join ';') + ';' + $env:Path

$flutter = Join-Path $Tools 'flutter\bin\flutter.bat'
$app     = Join-Path $Root 'app'

Write-Host "[env] JAVA_HOME=$env:JAVA_HOME" -ForegroundColor Cyan
Write-Host "[env] ANDROID_HOME=$env:ANDROID_HOME" -ForegroundColor Cyan

Push-Location $app
$oldEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
  if (-not $NoPubGet) {
    Write-Host "`n========== flutter pub get ==========" -ForegroundColor Cyan
    & $flutter pub get 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) { throw "flutter pub get failed ($LASTEXITCODE)" }
  }

  if ($BuildAab) {
    $args = @('build', 'appbundle')
    $outDir = Join-Path $app 'build\app\outputs\bundle\release'
    $artifactFilter = '*.aab'
  } else {
    $args = @('build', 'apk', '--target-platform', 'android-arm64')
    $outDir = Join-Path $app 'build\app\outputs\flutter-apk'
    $artifactFilter = '*.apk'
  }
  if ($DebugBuild) { $args += '--debug' } else { $args += '--release' }
  $args += '--dart-define', "API_BASE_URL=$ApiBaseUrl"
  if (-not $BuildAab -and $SplitPerAbi) { $args += '--split-per-abi' }

  $artifactPattern = if ($BuildAab) { 'Built build\\.*\.aab' } else { 'Built build\\.*\.apk' }

  Write-Host "`n========== flutter $($args -join ' ') ==========" -ForegroundColor Cyan
  $log    = Join-Path $Root 'build-apk.log'
  $errLog = Join-Path $Root 'build-apk.err'
  $sw     = [System.Diagnostics.Stopwatch]::StartNew()
  $buildProc = Start-Process -FilePath $flutter -ArgumentList $args `
    -NoNewWindow -PassThru -RedirectStandardOutput $log -RedirectStandardError $errLog
  $timeoutMin = 40
  while (-not $buildProc.HasExited -and $sw.Elapsed.TotalMinutes -lt $timeoutMin) {
    Start-Sleep -Seconds 3
  }
  if (-not $buildProc.HasExited) {
    Write-Host "build exceeded ${timeoutMin}min — killing build process" -ForegroundColor Yellow
    $buildProc.Kill()
  }
  Start-Sleep -Seconds 2
  $gradlew = Join-Path $app 'android\gradlew.bat'
  if (Test-Path -LiteralPath $gradlew) { & $gradlew --stop 2>&1 | Out-Null }
  if (Test-Path -LiteralPath $errLog) {
    Get-Content -LiteralPath $errLog -ErrorAction SilentlyContinue | ForEach-Object { Add-Content -LiteralPath $log -Value $_ }
  }
  $exitCode = if ($buildProc.HasExited) { $buildProc.ExitCode } else { -1 }
  $built = Select-String -LiteralPath $log -Pattern $artifactPattern -ErrorAction SilentlyContinue
  if ($exitCode -ne 0 -and -not $built) {
    Write-Host "`n========== build failed (exit=$exitCode) — last 40 log lines ==========" -ForegroundColor Red
    Get-Content -LiteralPath $log -Tail 40 -ErrorAction SilentlyContinue | Write-Host
    throw "flutter build failed (exit=$exitCode); see $log"
  }

  Write-Host ("`n========== build OK in {0:N0}s ==========" -f $sw.Elapsed.TotalSeconds) -ForegroundColor Green
  "========== artifacts ==========" | Tee-Object -FilePath $log -Append
  Get-ChildItem -LiteralPath $outDir -Filter $artifactFilter -Recurse -ErrorAction SilentlyContinue |
    ForEach-Object { '{0}  {1:N1} MB' -f $_.FullName, ($_.Length / 1MB) } |
    Tee-Object -FilePath $log -Append
}
finally {
  $ErrorActionPreference = $oldEap
  Pop-Location
}
