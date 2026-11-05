# Session-level environment injection (dot-source me, do not run directly).
#   . .\scripts\use-env.ps1
#   . .\scripts\use-env.ps1 -Ohos            # OpenHarmony SDK (flutter_ohos default)
#   . .\scripts\use-env.ps1 -Ohos -HarmonyOS # HarmonyOS 26 SDK from DevEco (for AppGallery)
param([switch]$Ohos, [switch]$HarmonyOS)

if (-not $PSScriptRoot) { throw 'Dot-source this script from a PowerShell terminal: . .\scripts\use-env.ps1' }
$Root  = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Tools = Join-Path $Root '.tools'

$jdk = Join-Path $Tools 'jdk21'
if (-not (Test-Path (Join-Path $jdk 'bin\java.exe'))) { $jdk = Join-Path $Tools 'jdk17' }

$env:AIL_ROOT            = $Root
$env:JAVA_HOME           = $jdk
$env:ANDROID_HOME        = Join-Path $Tools 'android-sdk'
$env:ANDROID_SDK_ROOT    = $env:ANDROID_HOME
$env:PUB_CACHE           = Join-Path $Tools 'caches\pub-cache'
$env:GRADLE_USER_HOME    = Join-Path $Tools 'caches\gradle'
$env:FLUTTER_STORAGE_BASE_URL = 'https://storage.flutter-io.cn'
$env:PUB_HOSTED_URL      = 'https://pub.flutter-io.cn'

$paths = @(
  (Join-Path $env:JAVA_HOME 'bin'),
  (Join-Path $Tools 'flutter\bin'),
  (Join-Path $Tools 'android-sdk\platform-tools'),
  (Join-Path $Tools 'android-sdk\cmdline-tools\latest\bin')
)

if ($Ohos) {
  # flutter_ohos only reads OHOS_SDK_HOME / OHOS_HOME (not DEVECO_SDK_HOME).
  $paths = @((Join-Path $Tools 'flutter_ohos\bin')) + $paths
  $ohosToolchain = 'D:\HuaWei\OhosSdkForFlutter\26\toolchains'
  if ($HarmonyOS) {
    $hk       = 'D:\HuaWei\DevEco-Studio\sdk\default'
    $hkParent = 'D:\HuaWei\DevEco-Studio\sdk'
    $env:OHOS_SDK_HOME      = $hk
    $env:OHOS_HOME          = $hk
    $env:OHOS_BASE_SDK_HOME = $hk
    $env:DEVECO_SDK_HOME    = $hkParent
    $env:HOS_SDK_HOME       = $hkParent
    $ohosToolchain = Join-Path $hk 'openharmony\toolchains'
  } else {
    $env:OHOS_SDK_HOME = 'D:\HuaWei\OhosSdkForFlutter'
    $env:OHOS_HOME     = 'D:\HuaWei\OhosSdkForFlutter'
    $env:OHOS_BASE_SDK_HOME = 'D:\HuaWei\Sdk'
    $env:DEVECO_SDK_HOME = 'D:\HuaWei\Sdk'
    $env:HOS_SDK_HOME     = 'D:\HuaWei\Sdk'
  }
  foreach ($p in @(
      'D:\HuaWei\DevEco-Studio\tools\node',
      'D:\HuaWei\DevEco-Studio\tools\ohpm\bin',
      'D:\HuaWei\DevEco-Studio\tools\hvigor\bin',
      $ohosToolchain
    )) { if (Test-Path $p) { $paths += $p } else { Write-Warning "missing: $p" } }
  $env:PUB_CACHE = Join-Path $Tools 'caches\pub-cache-official'
}

$env:Path = (($paths | Where-Object { Test-Path $_ } | Select-Object -Unique) -join ';') + ';' + $env:Path
Write-Host "[env] AIL_ROOT=$env:AIL_ROOT"
Write-Host "[env] JAVA_HOME=$env:JAVA_HOME"
Write-Host "[env] ANDROID_HOME=$env:ANDROID_HOME"
if ($Ohos) { Write-Host '[env] HarmonyOS NEXT toolchain active' } else { Write-Host '[env] Android / Flutter stable active' }
