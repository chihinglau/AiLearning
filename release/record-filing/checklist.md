# R-06 ICP 备案 / APP 备案提交清单

> 包名 `com.ailearning.ai_learning`、签名 MD5/SHA-256 一经备案不可变更。
> 本清单中的待填项由 PM 在取得资质后补齐，并将备案号回填后端环境变量。

## 1. 主体与域名（待 PM 填写）

| 项目 | 填写值 |
|---|---|
| 备案主体 | 待填写（个人身份证 / 企业营业执照） |
| 主体证件号 | 待填写 |
| 网站/APP 名称 | 深爱学学习辅助软件（与软著名称一致） |
| 域名 | 待填写（如 `app.example.com`） |
| 服务器 IP / 接入商 | 待填写 |
| 隐私政策 URL | `https://<域名>/legal/privacy` |
| 用户协议 URL | `https://<域名>/legal/terms` |
| APP 信息接口 | `https://<域名>/app/info`（商店审核可用） |

## 2. APP 技术信息（已固化）

| 项目 | 值 | 来源 |
|---|---|---|
| 包名 / applicationId | `com.ailearning.ai_learning` | `app/android/app/build.gradle.kts` |
| versionName | `1.0.0` | `app/pubspec.yaml` |
| versionCode | `10001` | `releaseVersionCode` 规则（R-01） |
| 签名 MD5 | `EB:51:94:8B:3D:DB:AA:41:05:01:0E:40:E2:CC:72:95` | `scripts/signature-info.ps1`（R-01 归档） |
| 签名证书 | `CN=AiLearning`（release keystore，禁止更换） | `scripts/make-release-keystore.ps1` |
| SDK 清单 | 无第三方统计/推送/广告 SDK（仅网络与本地存储） | `app/pubspec.yaml` |
| 权限用途 | 网络访问（学习内容）、本地存储（离线缓存） | AndroidManifest / 鸿蒙 module.json5 |

> 复核命令：

```powershell
scripts\signature-info.ps1 -Apk app\build\app\outputs\flutter-apk\app-release.apk
```

## 3. 提交流程

1. **ICP 备案**：在接入商备案系统提交主体、域名与服务器信息，取得 ICP 备案号（预计 7~20 个工作日）。
2. **APP 备案**：在工信部 APP 备案系统（或通过接入商/商店代提交）填写 APP 名称、包名、签名 MD5、版本号、隐私政策 URL、SDK 情况。
3. **华为应用市场**：提交软著登记证书、ICP 备案号、APP 备案号、隐私政策 URL、签名证书指纹；核对包名与签名与已备案信息一致。
4. **小米应用商店**：同上，补充开发者实名与资质材料。
5. **回填**：取得 ICP 备案号与 APP 备案号后，写入 `deploy/.env`：

```ini
LEGAL_PUBLIC_BASE_URL=https://<域名>
ICP_RECORD_NO=粤ICP备XXXXXXXX号-X
APP_RECORD_NO=粤ICP备XXXXXXXX号-XA
SOFTWARE_COPYRIGHT_NO=2026SRXXXXXXX
```

6. **验证**：`https://<域名>/legal/privacy` 返回 HTML；`https://<域名>/app/info` 返回备案号；App「我的 → 关于」展示三项编号。
7. **归档**：备案号、APP 备案截图、商店审核回执存入 `release/record-filing/archive/`（含敏感信息，不入库）。

## 4. 固化纪律（不可变更项）

- 包名 `com.ailearning.ai_learning` 与 release 签名证书一经备案不得更换；更换需重新备案。
- versionCode 只允许递增，不得回退（`scripts/sync-version.ps1` 以 pubspec 为唯一来源）。
- 隐私政策 URL 与 APP 名称变更需同步更新备案信息，不得先发版后备案。
- 商店展示名称须与软著「深爱学学习辅助软件」、APP 备案名称保持一致；简称「深爱学」仅作展示补充。

## 5. 完成标准

- [ ] ICP 备案号取得并回填
- [ ] APP 备案号取得并回填
- [ ] 华为/小米商店备案信息与包名、签名一致
- [ ] `/legal/privacy`、`/legal/terms`、`/app/info` 公网可访问
- [ ] App「关于」页展示 ICP、APP 备案号与软著登记号
- [ ] 归档材料完成
