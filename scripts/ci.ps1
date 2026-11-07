#requires -Version 5.1
<#
  R-09 发布流水线：一条命令完成版本校验、后端/前端质量门禁、构建、签名校验、
  产物归档、发布检查表生成与（可选）Git tag。

  Usage:
    powershell -ExecutionPolicy Bypass -File scripts\ci.ps1 -SkipBuild -SkipTests   # 只跑检查表
    powershell -ExecutionPolicy Bypass -File scripts\ci.ps1 -SkipTests              # 校验 + 构建
    powershell -ExecutionPolicy Bypass -File scripts\ci.ps1 -BuildAab -WithHap -Tag  # 全量发布
    powershell -ExecutionPolicy Bypass -File scripts\ci.ps1 -ApiBaseUrl https://api.your-domain

  Gates:
    -SkipTests      跳过 ruff/pytest/flutter analyze/flutter test
    -SkipBuild      跳过 APK（同时跳过签名校验/产物归档）
    -BuildAab       额外构建 Android App Bundle
    -WithHap        额外构建 HarmonyOS HAP（需 ohos 工具链）
    -Tag            质量门禁与构建全部通过且工作区干净时创建 v<versionName> 标签
    -AllowDirty     允许在脏工作区打 tag（默认禁止）
    -SkipChecklist  不生成发布检查表（不建议）
#>
[CmdletBinding()]
param(
  [switch]$SkipTests,
  [switch]$SkipBuild,
  [switch]$BuildAab,
  [switch]$WithHap,
  [switch]$Tag,
  [switch]$AllowDirty,
  [switch]$SkipChecklist,
  [string]$ApiBaseUrl = 'https://api.ailearning.example'
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$AppDir = Join-Path $Root 'app'
$BackendDir = Join-Path $Root 'backend'
$BuildRoot = Join-Path $Root 'build\release'

. (Join-Path $PSScriptRoot 'use-env.ps1') | Out-Null

function Get-PubspecVersion {
  $pubspec = Join-Path $AppDir 'pubspec.yaml'
  $match = Select-String -LiteralPath $pubspec -Pattern '^version:\s*(\d+)\.(\d+)\.(\d+)\+(\d+)\s*$' |
    Select-Object -First 1
  if (-not $match) { throw 'app\pubspec.yaml has no valid "version: x.y.z+build" line' }
  $g = $match.Matches[0].Groups
  $name = '{0}.{1}.{2}' -f $g[1].Value, $g[2].Value, $g[3].Value
  $code = [int]$g[1].Value * 10000 + [int]$g[2].Value * 100 + [int]$g[3].Value * 10 + [int]$g[4].Value
  return [pscustomobject]@{ Name = $name; Code = $code; Build = [int]$g[4].Value; Tag = "v$name" }
}

$Version = Get-PubspecVersion
$ReleaseDir = Join-Path $BuildRoot ("{0}+{1}" -f $Version.Name, $Version.Build)
$Results = [System.Collections.Generic.List[object]]::new()
$Artifacts = [System.Collections.Generic.List[object]]::new()

function Add-Result {
  param([string]$Name, [string]$Status, [string]$Detail)
  $Results.Add([pscustomobject]@{ Name = $Name; Status = $Status; Detail = $Detail })
  $color = switch ($Status) { 'PASS' { 'Green' } 'WARN' { 'Yellow' } 'SKIP' { 'DarkGray' } default { 'Red' } }
  Write-Host ("[{0}] {1} - {2}" -f $Status, $Name, $Detail) -ForegroundColor $color
}

function Invoke-Step {
  param([string]$Name, [scriptblock]$Block)
  Write-Host "`n========== $Name ==========" -ForegroundColor Cyan
  $watch = [System.Diagnostics.Stopwatch]::StartNew()
  try {
    & $Block
    $watch.Stop()
    Add-Result $Name 'PASS' ("{0:N1}s" -f $watch.Elapsed.TotalSeconds)
  } catch {
    $watch.Stop()
    Add-Result $Name 'FAIL' $_.Exception.Message
    throw
  }
}

function Test-FileList {
  param([string[]]$Paths)
  $missing = @($Paths | Where-Object { -not (Test-Path -LiteralPath (Join-Path $Root $_)) })
  return $missing
}

function Invoke-Checklist {
  $checks = [System.Collections.Generic.List[object]]::new()
  function Add-Check {
    param([string]$Item, [string]$Status, [string]$Detail, [bool]$Blocker)
    $checks.Add([pscustomobject]@{ Item = $Item; Status = $Status; Detail = $Detail; Blocker = $Blocker })
  }

  $missingStore = Test-FileList @(
    'release\store-assets\assets.json',
    'release\store-assets\listing.md',
    'release\store-assets\data-safety.md',
    'release\store-assets\audience-rating.md',
    'release\store-assets\huawei-privacy-label.md',
    'release\store-assets\icon-1024.png',
    'release\store-assets\feature-graphic-1024x500.png'
  )
  $shots = @(Get-ChildItem (Join-Path $Root 'release\store-assets\screenshots') -Filter '*.png' -ErrorAction SilentlyContinue)
  if ($missingStore.Count -eq 0 -and $shots.Count -ge 8) {
    Add-Check '应用市场素材（图标/Feature Graphic/8 张截图/文案）' 'PASS' ("screenshots={0}" -f $shots.Count) $true
  } else {
    Add-Check '应用市场素材（图标/Feature Graphic/8 张截图/文案）' 'FAIL' ("缺少: {0}; screenshots={1}" -f ($missingStore -join ', '), $shots.Count) $true
  }

  $legalMissing = Test-FileList @('docs\privacy.md', 'docs\release-plan.md')
  $legalDir = Join-Path $AppDir 'assets\legal'
  $privacyDoc = Join-Path $Root 'docs\privacy.md'
  $privacyText = if (Test-Path -LiteralPath $privacyDoc) { [System.IO.File]::ReadAllText($privacyDoc) } else { '' }
  if ($legalMissing.Count -eq 0 -and (Test-Path -LiteralPath $legalDir) -and $privacyText.Trim().Length -gt 200) {
    Add-Check '隐私政策/用户协议与法律文档' 'PASS' ("assets/legal={0}" -f (Test-Path -LiteralPath $legalDir)) $true
  } else {
    Add-Check '隐私政策/用户协议与法律文档' 'FAIL' ("缺少: {0}" -f ($legalMissing -join ', ')) $true
  }

  $copyright = Test-FileList @(
    'release\software-copyright\source-code.docx',
    'release\software-copyright\user-manual.docx',
    'release\software-copyright\metadata.json',
    'release\software-copyright\submission-checklist.md'
  )
  $registration = Join-Path $Root 'release\software-copyright\registration.txt'
  $regText = if (Test-Path -LiteralPath $registration) { [System.IO.File]::ReadAllText($registration) } else { '' }
  if ($copyright.Count -gt 0) {
    Add-Check '软件著作权申请材料' 'FAIL' ("缺少: {0}" -f ($copyright -join ', ')) $true
  } elseif ($regText -match '受理号：待填写' -or $regText -match '登记号：待填写') {
    Add-Check '软件著作权申请材料' 'WARN' '材料齐全，受理号/登记号待 PM 取得后回填' $false
  } else {
    Add-Check '软件著作权申请材料' 'PASS' '登记号已归档' $true
  }

  $filing = Join-Path $Root 'release\record-filing\checklist.md'
  if (-not (Test-Path -LiteralPath $filing)) {
    Add-Check 'ICP/APP 备案材料' 'FAIL' '缺少 release/record-filing/checklist.md' $true
  } else {
    $filingText = [System.IO.File]::ReadAllText($filing)
    $pending = @(Select-String -InputObject $filingText -Pattern '待填写|待 PM' -AllMatches).Count
    if ($pending -gt 0) {
      Add-Check 'ICP/APP 备案材料' 'WARN' '清单齐备，主体/域名/备案号等待 PM 回填' $false
    } else {
      Add-Check 'ICP/APP 备案材料' 'PASS' '备案信息已回填' $true
    }
  }

  $ledger = Join-Path $Root 'release\content-compliance\license-ledger.md'
  if (Test-Path -LiteralPath $ledger) {
    Add-Check '内容合规/版权与许可台账' 'PASS' 'license-ledger.md 已归档' $true
  } else {
    Add-Check '内容合规/版权与许可台账' 'FAIL' '缺少 release/content-compliance/license-ledger.md' $true
  }

  $keystoreProps = Test-Path -LiteralPath (Join-Path $Root 'keystore.properties')
  $keystoreOk = $false
  if ($keystoreProps) {
    $props = @{}
    Get-Content -LiteralPath (Join-Path $Root 'keystore.properties') | ForEach-Object {
      if ($_ -match '^(?<k>[^#=]+)=(?<v>.*)$') { $props[$Matches['k'].Trim()] = $Matches['v'].Trim() }
    }
    $keystoreOk = [bool]$props['storeFile'] -and (Test-Path -LiteralPath $props['storeFile'])
  }
  if ($keystoreProps -and $keystoreOk) {
    Add-Check 'Release 签名密钥（keystore.properties）' 'PASS' '签名配置与密钥文件就绪' $true
  } else {
    Add-Check 'Release 签名密钥（keystore.properties）' 'FAIL' '缺少签名配置或密钥文件' $true
  }

  $manifest = Join-Path $AppDir 'android\app\src\main\AndroidManifest.xml'
  if (Test-Path -LiteralPath $manifest) {
    $manifestText = [System.IO.File]::ReadAllText($manifest)
    $hasInternet = $manifestText -match 'android\.permission\.INTERNET'
    $hasLabel = $manifestText -match 'android:label'
    if ($hasInternet -and $hasLabel) {
      Add-Check 'Android Manifest（INTERNET/应用名）' 'PASS' '权限与应用名已声明' $true
    } else {
      Add-Check 'Android Manifest（INTERNET/应用名）' 'FAIL' ("internet={0} label={1}" -f $hasInternet, $hasLabel) $true
    }
  } else {
    Add-Check 'Android Manifest（INTERNET/应用名）' 'FAIL' '找不到 AndroidManifest.xml' $true
  }

  $signatureResult = $Results | Where-Object { $_.Name -eq '签名校验' } | Select-Object -First 1
  if ($signatureResult) {
    Add-Check 'Android 签名校验（CN=AiLearning）' $signatureResult.Status $signatureResult.Detail $true
  } else {
    Add-Check 'Android 签名校验（CN=AiLearning）' 'WARN' '本次未构建，跳过签名校验' $false
  }

  $apk = $Artifacts | Where-Object { $_.Kind -eq 'apk' } | Select-Object -First 1
  if ($apk) {
    Add-Check 'Android APK 产物' 'PASS' ("{0} ({1:N1} MB)" -f $apk.Name, ($apk.Size / 1MB)) $true
  } elseif ($SkipBuild) {
    Add-Check 'Android APK 产物' 'WARN' '本次 -SkipBuild，未构建 APK' $false
  } else {
    Add-Check 'Android APK 产物' 'FAIL' '未找到 app-release.apk' $true
  }

  $aab = $Artifacts | Where-Object { $_.Kind -eq 'aab' } | Select-Object -First 1
  if ($aab) {
    Add-Check 'Android AAB 产物' 'PASS' ("{0} ({1:N1} MB)" -f $aab.Name, ($aab.Size / 1MB)) $false
  } else {
    Add-Check 'Android AAB 产物' 'SKIP' '未启用 -BuildAab' $false
  }

  $hap = $Artifacts | Where-Object { $_.Kind -eq 'hap' } | Select-Object -First 1
  if ($hap) {
    Add-Check 'HarmonyOS HAP 产物' 'PASS' ("{0} ({1:N1} MB)" -f $hap.Name, ($hap.Size / 1MB)) $false
  } else {
    Add-Check 'HarmonyOS HAP 产物' 'SKIP' '未启用 -WithHap（需 ohos 工具链）' $false
  }

  $monitorEndpoint = Join-Path $BackendDir 'app\api\routes\monitor.py'
  $monitorMiddleware = Join-Path $BackendDir 'app\core\middleware.py'
  $monitorClient = Join-Path $AppDir 'lib\core\monitoring\crash_reporter.dart'
  if ((Test-Path $monitorEndpoint) -and (Test-Path $monitorMiddleware) -and (Test-Path $monitorClient)) {
    Add-Check '崩溃与错误监控接入' 'PASS' 'App 上报 + 后端落库/汇总链路已存在' $true
  } else {
    Add-Check '崩溃与错误监控接入' 'FAIL' '监控链路文件缺失' $true
  }

  $blockers = @($checks | Where-Object { $_.Blocker -and $_.Status -eq 'FAIL' })
  $warns = @($checks | Where-Object { $_.Status -eq 'WARN' })
  $verdict = if ($blockers.Count -gt 0) { 'BLOCKED' } elseif ($warns.Count -gt 0) { 'PASS-WITH-WARNINGS' } else { 'PASS' }

  New-Item -ItemType Directory -Force $ReleaseDir | Out-Null
  $checklistPath = Join-Path $ReleaseDir 'release-checklist.md'
  $lines = [System.Collections.Generic.List[string]]::new()
  $lines.Add('# 发布检查表（自动生成）')
  $lines.Add('')
  $lines.Add(("- 生成时间：{0}" -f (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')))
  $lines.Add(("- 版本：{0}（versionCode {1}）" -f $Version.Name, $Version.Code))
  $lines.Add(("- 结论：**{0}**（阻断项 {1}，待人工确认 {2}）" -f $verdict, $blockers.Count, $warns.Count))
  $lines.Add('')
  $lines.Add('| 检查项 | 状态 | 说明 |')
  $lines.Add('|---|---|---|')
  foreach ($check in $checks) {
    $lines.Add(("| {0} | {1} | {2} |" -f $check.Item, $check.Status, ($check.Detail -replace '\|', '\\|')))
  }
  $lines.Add('')
  $lines.Add('## 流水线步骤')
  $lines.Add('')
  $lines.Add('| 步骤 | 状态 | 详情 |')
  $lines.Add('|---|---|---|')
  foreach ($result in $Results) {
    $lines.Add(("| {0} | {1} | {2} |" -f $result.Name, $result.Status, ($result.Detail -replace '\|', '\\|')))
  }
  [System.IO.File]::WriteAllText($checklistPath, (($lines -join "`r`n") + "`r`n"))

  Write-Host "`n========== release checklist ==========" -ForegroundColor Cyan
  Write-Host ("verdict=$verdict blockers=$($blockers.Count) warnings=$($warns.Count)")
  Write-Host "report -> $checklistPath" -ForegroundColor Green
  Add-Result '发布检查表结论' 'PASS' ("{0} ({1}, blockers={2}, warnings={3})" -f $checklistPath, $verdict, $blockers.Count, $warns.Count)

  if ($blockers.Count -gt 0) {
    throw ("release checklist blocked: {0}" -f (($blockers | ForEach-Object { $_.Item }) -join '; '))
  }
}

function Save-Artifacts {
  New-Item -ItemType Directory -Force $ReleaseDir | Out-Null
  $artifactMeta = @()
  foreach ($artifact in $Artifacts) {
    Copy-Item -LiteralPath $artifact.Path -Destination (Join-Path $ReleaseDir $artifact.Name) -Force
    $artifactMeta += [ordered]@{
      kind = $artifact.Kind
      file = $artifact.Name
      bytes = $artifact.Size
      sha256 = (Get-FileHash -LiteralPath $artifact.Path -Algorithm SHA256).Hash.ToLowerInvariant()
    }
  }
  $metadata = [ordered]@{
    versionName = $Version.Name
    versionCode = $Version.Code
    buildNumber = $Version.Build
    generatedAt = (Get-Date).ToString('s')
    apiBaseUrl = $ApiBaseUrl
    gitCommit = (& git -C $Root rev-parse HEAD 2>$null)
    artifacts = $artifactMeta
  }
  $metadata | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $ReleaseDir 'metadata.json') -Encoding UTF8
  $signature = Get-ChildItem (Join-Path $Root 'build\signatures') -Filter 'signature-*.txt' -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($signature) {
    Copy-Item -LiteralPath $signature.FullName -Destination (Join-Path $ReleaseDir 'signature-info.txt') -Force
  }
  $sums = foreach ($artifact in $Artifacts) {
    $hash = (Get-FileHash -LiteralPath $artifact.Path -Algorithm SHA256).Hash.ToLowerInvariant()
    "{0}  {1}" -f $hash, $artifact.Name
  }
  [System.IO.File]::WriteAllLines((Join-Path $ReleaseDir 'SHA256SUMS.txt'), @($sums))
  Write-Host "[archive] -> $ReleaseDir" -ForegroundColor Green
}

Write-Host ("[ci] version={0} versionCode={1} api={2}" -f $Version.Name, $Version.Code, $ApiBaseUrl) -ForegroundColor Cyan

try {
  Invoke-Step '版本一致性' {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'sync-version.ps1') -Check
    if ($LASTEXITCODE -ne 0) { throw "sync-version -Check failed ($LASTEXITCODE)" }
  }

  if (-not $SkipTests) {
    $ruff = Join-Path $BackendDir '.venv\Scripts\ruff.exe'
    Invoke-Step '后端静态检查 (ruff)' {
      Push-Location $BackendDir
      try {
        if (Test-Path -LiteralPath $ruff) {
          & $ruff check --select E9,F app alembic tests
        } else {
          & python -m ruff check --select E9,F app alembic tests
        }
        if ($LASTEXITCODE -ne 0) { throw "ruff failed ($LASTEXITCODE)" }
      } finally { Pop-Location }
    }

    Invoke-Step '后端单元测试 (pytest)' {
      Push-Location $BackendDir
      try {
        & .\.venv\Scripts\python.exe -m pytest -q
        if ($LASTEXITCODE -ne 0) { throw "pytest failed ($LASTEXITCODE)" }
      } finally { Pop-Location }
    }

    Invoke-Step 'Flutter 静态分析 (flutter analyze)' {
      Push-Location $AppDir
      try {
        & flutter analyze
        if ($LASTEXITCODE -ne 0) { throw "flutter analyze failed ($LASTEXITCODE)" }
      } finally { Pop-Location }
    }

    Invoke-Step 'Flutter 单元测试 (flutter test)' {
      Push-Location $AppDir
      try {
        & flutter test
        if ($LASTEXITCODE -ne 0) { throw "flutter test failed ($LASTEXITCODE)" }
      } finally { Pop-Location }
    }
  } else {
    Add-Result '质量门禁' 'SKIP' '-SkipTests'
  }

  if (-not $SkipBuild) {
    Invoke-Step '构建 Android Release APK' {
      & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'build-apk.ps1') -NoPubGet -ApiBaseUrl $ApiBaseUrl
      if ($LASTEXITCODE -ne 0) { throw "build-apk failed ($LASTEXITCODE)" }
    }
    $apkPath = Join-Path $AppDir 'build\app\outputs\flutter-apk\app-release.apk'
    if (-not (Test-Path -LiteralPath $apkPath)) { throw "APK not found: $apkPath" }
    $Artifacts.Add([pscustomobject]@{ Kind = 'apk'; Path = $apkPath; Name = "AiLearning-$($Version.Name)-$($Version.Code).apk"; Size = (Get-Item $apkPath).Length })

    if ($BuildAab) {
      Invoke-Step '构建 Android App Bundle' {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'build-apk.ps1') -NoPubGet -BuildAab -ApiBaseUrl $ApiBaseUrl
        if ($LASTEXITCODE -ne 0) { throw "build-aab failed ($LASTEXITCODE)" }
      }
      $aabPath = Join-Path $AppDir 'build\app\outputs\bundle\release\app-release.aab'
      if (-not (Test-Path -LiteralPath $aabPath)) { throw "AAB not found: $aabPath" }
      $Artifacts.Add([pscustomobject]@{ Kind = 'aab'; Path = $aabPath; Name = "AiLearning-$($Version.Name)-$($Version.Code).aab"; Size = (Get-Item $aabPath).Length })
    }

    Invoke-Step '签名校验' {
      & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'signature-info.ps1') -Apk $apkPath
      if ($LASTEXITCODE -ne 0) { throw "signature-info failed ($LASTEXITCODE)" }
    }

    if ($WithHap) {
      Invoke-Step '构建 HarmonyOS HAP' {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'build-hap.ps1') -Release -ApiBaseUrl $ApiBaseUrl
        if ($LASTEXITCODE -ne 0) { throw "build-hap failed ($LASTEXITCODE)" }
      }
      $hap = Get-ChildItem (Join-Path $AppDir 'build\ohos') -Recurse -Filter '*.hap' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
      if (-not $hap) { throw 'HAP artifact not found under app\build\ohos' }
      $Artifacts.Add([pscustomobject]@{ Kind = 'hap'; Path = $hap.FullName; Name = "AiLearning-$($Version.Name)-$($Version.Code).hap"; Size = $hap.Length })
    }
  } else {
    Add-Result '构建/签名' 'SKIP' '-SkipBuild'
  }

  if ($Artifacts.Count -gt 0) {
    Invoke-Step '归档产物与校验和' { Save-Artifacts }
  }

  if (-not $SkipChecklist) {
    Invoke-Step '发布检查表' { Invoke-Checklist }
  }

  if ($Tag) {
    Invoke-Step 'Git Tag' {
      $dirty = (& git -C $Root status --porcelain)
      if ($dirty -and -not $AllowDirty) {
        throw '工作区存在未提交改动；提交后再打 tag，或显式使用 -AllowDirty'
      }
      $existing = (& git -C $Root tag -l $Version.Tag)
      if ($existing) { throw ("tag already exists: {0}" -f $Version.Tag) }
      & git -C $Root tag -a $Version.Tag -m ("release {0} (versionCode {1})" -f $Version.Name, $Version.Code)
      if ($LASTEXITCODE -ne 0) { throw "git tag failed ($LASTEXITCODE)" }
    }
  }

  Write-Host "`n[ci] ALL CHECKS PASSED -> $ReleaseDir" -ForegroundColor Green
} catch {
  Write-Host "`n[ci] FAILED: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}
