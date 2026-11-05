# Build the HarmonyOS NEXT HAP for AiLearning (深爱学).
#
# Prerequisites:
#   - flutter_ohos (3.41.10-ohos / Dart 3.11.5) reachable via use-env.ps1 -Ohos
#   - app/ohos/ build-profile.json5: compatibleSdkVersion=26.0.0, runtimeOS=HarmonyOS
#   - oh-package.json5 modelVersion=6.0.0 ; module.json5 deviceTypes=["default"]
#   - A signing config (DevEco auto-sign / local cert). Pass -NoCodesign to skip.
#
# Usage:
#   .\scripts\build-hap.ps1                # debug HAP (arm64), auto-codesign
#   .\scripts\build-hap.ps1 -Release       # release HAP
#   .\scripts\build-hap.ps1 -NoCodesign    # skip codesign (compile-only)
param(
  [switch]$Release,
  [switch]$NoCodesign,
  [string]$ApiBaseUrl = 'http://10.0.2.2:18080'
)
$ErrorActionPreference = 'Stop'
$Root   = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$AppDir = Join-Path $Root 'app'

# HarmonyOS 26 SDK (with hms) is required for AppGallery-compatible HAPs.
. (Join-Path $PSScriptRoot 'use-env.ps1') -Ohos -HarmonyOS

$buildMode = if ($Release) { 'release' } else { 'debug' }
$codesign  = if ($NoCodesign) { '--no-codesign' } else { '' }

Write-Host "[build-hap] mode=$buildMode  flutter=$(flutter --version 2>$null | Select-Object -First 1)"

Push-Location $AppDir
try {
  flutter build hap --$buildMode $codesign --dart-define="API_BASE_URL=$ApiBaseUrl"
  $exit = $LASTEXITCODE
  if ($exit -eq 0) {
    Write-Host "[build-hap] OK -> app/build/ohos/$buildMode/  (entry-default-signed.hap)"
  } else {
    Write-Warning "[build-hap] flutter build hap exited $exit"
  }
  exit $exit
} finally {
  Pop-Location
}
