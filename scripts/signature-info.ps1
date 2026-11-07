#requires -Version 5.1
<#
  Export the release signing certificate fingerprints (MD5 / SHA-256) and
  verify the actual APK signature. The report is archived under build\signatures\
  (gitignored) for APP filing / store submission.

  Usage:
    powershell -ExecutionPolicy Bypass -File scripts\signature-info.ps1
    powershell -ExecutionPolicy Bypass -File scripts\signature-info.ps1 -Apk app\build\app\outputs\flutter-apk\app-release.apk
#>
[CmdletBinding()]
param(
  [string]$Apk
)
$ErrorActionPreference = 'Stop'
$Root = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot '..')).Path } else { (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..')).Path }
$Tools = Join-Path $Root '.tools'

$jdk = Join-Path $Tools 'jdk21'
if (-not (Test-Path (Join-Path $jdk 'bin\java.exe'))) { $jdk = Join-Path $Tools 'jdk17' }
if (-not (Test-Path (Join-Path $jdk 'bin\java.exe'))) { throw 'JDK not found under .tools; run scripts\setup-env.ps1 first' }
$env:JAVA_HOME = $jdk
$keytool = Join-Path $jdk 'bin\keytool.exe'

$propsPath = Join-Path $Root 'keystore.properties'
if (-not (Test-Path -LiteralPath $propsPath)) {
  throw 'keystore.properties not found; run scripts\make-release-keystore.ps1 first'
}
$props = @{}
Get-Content -LiteralPath $propsPath | ForEach-Object {
  if ($_ -match '^(?<key>[^#=]+)=(?<value>.*)$') {
    $props[$Matches['key'].Trim()] = $Matches['value'].Trim()
  }
}
foreach ($name in @('storeFile', 'storePassword', 'keyAlias')) {
  if (-not $props[$name]) { throw "keystore.properties is missing $name" }
}
$ks = $props['storeFile']
if (-not (Test-Path -LiteralPath $ks)) { throw "keystore file not found: $ks" }

$apksigner = Get-ChildItem (Join-Path $Tools 'android-sdk\build-tools') -Recurse -Filter apksigner.bat -ErrorAction SilentlyContinue |
  Sort-Object FullName -Descending | Select-Object -First 1
if (-not $apksigner) { throw 'apksigner.bat not found under .tools\android-sdk\build-tools' }

if (-not $Apk) {
  $latest = Get-ChildItem (Join-Path $Root 'app\build\app\outputs\flutter-apk') -Filter 'app-release*.apk' -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($latest) { $Apk = $latest.FullName }
}
if ($Apk -and -not (Test-Path -LiteralPath $Apk)) { throw "APK not found: $Apk" }
if (-not $Apk) {
  Write-Host '[signature-info] no release APK found; certificate fingerprints only' -ForegroundColor Yellow
}

$outDir = Join-Path $Root 'build\signatures'
New-Item -ItemType Directory -Force $outDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$outFile = Join-Path $outDir "signature-$stamp.txt"
$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add("generated_at=$((Get-Date).ToString('s'))")
$lines.Add("keystore=$ks")
$lines.Add("alias=$($props['keyAlias'])")

$oldEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$list = & $keytool -list -v -keystore $ks -alias $props['keyAlias'] -storepass $props['storePassword'] 2>&1
$listExit = $LASTEXITCODE
$ErrorActionPreference = $oldEap
if ($listExit -ne 0) { throw "keytool -list failed ($listExit)" }

$owner = ($list | Select-String -Pattern '^Owner:.*$' | Select-Object -First 1)
if (-not $owner) { throw 'failed to extract certificate owner from keytool output' }
if ($owner.Line -notmatch 'CN=AiLearning') {
  throw "unexpected certificate owner (expect CN=AiLearning): $($owner.Line)"
}

# JDK 21 keytool no longer prints the MD5 fingerprint, so compute both
# fingerprints from the exported DER certificate instead.
$tmpDer = Join-Path ([System.IO.Path]::GetTempPath()) ("ailearning-cert-{0}.der" -f $PID)
$ErrorActionPreference = 'Continue'
$export = & $keytool -exportcert -keystore $ks -alias $props['keyAlias'] -storepass $props['storePassword'] -file $tmpDer 2>&1
$exportExit = $LASTEXITCODE
$ErrorActionPreference = $oldEap
if ($exportExit -ne 0 -or -not (Test-Path -LiteralPath $tmpDer)) {
  throw "keytool -exportcert failed ($exportExit)"
}
$certBytes = [System.IO.File]::ReadAllBytes($tmpDer)
Remove-Item -LiteralPath $tmpDer -Force -ErrorAction SilentlyContinue

function Get-Fingerprint([byte[]]$bytes, [string]$algorithm) {
  $hash = [System.Security.Cryptography.HashAlgorithm]::Create($algorithm).ComputeHash($bytes)
  return (($hash | ForEach-Object { $_.ToString('X2') }) -join ':')
}
$md5 = Get-Fingerprint $certBytes 'MD5'
$sha256 = Get-Fingerprint $certBytes 'SHA256'

$lines.Add("owner=$($owner.Line.Trim())")
$lines.Add("md5=$md5")
$lines.Add("sha256=$sha256")

if ($Apk) {
  $ErrorActionPreference = 'Continue'
  $verify = & $apksigner.FullName verify --print-certs $Apk 2>&1
  $verifyExit = $LASTEXITCODE
  $ErrorActionPreference = $oldEap
  if ($verifyExit -ne 0) { throw "apksigner verify failed ($verifyExit): $Apk" }
  $lines.Add("apk=$Apk")
  foreach ($line in $verify) { $lines.Add([string]$line) }
  if (($verify -join "`n") -notmatch 'CN=AiLearning') {
    throw "APK is not signed with CN=AiLearning: $Apk"
  }
}

[System.IO.File]::WriteAllText($outFile, (($lines -join "`r`n") + "`r`n"))
Write-Host "`n========== signing info ==========" -ForegroundColor Cyan
$lines | ForEach-Object { Write-Host $_ }
Write-Host "`narchived -> $outFile" -ForegroundColor Green
