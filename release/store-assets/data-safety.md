# Google Play Data Safety 填报（R-08）

> 依据 `docs/privacy.md`（隐私政策源稿，版本 `2026.11.06`）与 R-04 的注销 / 导出实现如实申报。
> 填报原则：**宁可多申报，不可漏报**；当前无广告 SDK、无统计 SDK、不向第三方共享、不出售。

## 1. 数据收集总表

| Data Safety 分类 | 具体数据 | 是否收集 | 是否可选 | 是否共享 | 使用目的 | 加密传输 | 可删除 |
|---|---|---|---|---|---|---|---|---|
| Personal info → Phone number | 手机号 | 是 | 否（登录必需） | 否 | App functionality；Account management | 是 | 是 |
| Personal info → Name | 昵称 | 是 | 是（可留空） | 否 | App functionality | 是 | 是 |
| Personal info → Other info | 角色 / 学段 / 年级 | 是 | 否（学生必需） | 否 | App functionality；Personalization | 是 | 是 |
| App activity → App interactions | 教材绑定、答题记录、练习与测评、错题、掌握度、学习时长 | 是 | 否（核心功能） | 否 | App functionality；Personalization | 是 | 是 |
| App info and performance → Crash logs | 崩溃日志摘要（用户反馈或服务端日志） | 是 | 是（可在设置关闭诊断） | 否 | App functionality；Analytics（仅稳定性） | 是 | 是 |
| App info and performance → Diagnostics | App 版本、系统版本、设备型号 | 是 | 否 | 否 | App functionality；Analytics（仅兼容性） | 是 | 是 |
| Device or other IDs | IP 地址（安全审计日志） | 是 | 否 | 否 | App functionality；Security / Fraud prevention | 是 | 是 |
| Location / Contacts / Photos / Camera / Microphone / Health / Financial / Messages / Calendar / Web history / Files | — | 否 | — | 否 | — | — | — |

> 说明：
> - 云服务商仅作为**受托方**存储数据，不构成「共享」；
> - IP 仅在安全审计与异常登录识别时记录，留存 6 个月–2 年（`docs/privacy.md` §6.2）；
> - 若后续接入崩溃监控 SDK（R-09），需同步更新本表并重新提交 Data Safety。

## 2. 安全实践（Play Console → Data safety → Security practices）

| 问题 | 填写 |
|---|---|
| Is all of the user data collected by your app encrypted in transit? | **Yes**（全站 HTTPS/TLS，见 R-02） |
| Do you provide a way for users to request that their data be deleted? | **Yes** |
| 删除入口 | App 内「我的 → 账号与安全 → 注销账号」；15 个工作日内完成删除或匿名化 |
| 删除请求 URL（可选） | `https://<正式域名>/legal/privacy` |
| Committed to follow the Play Families policy? | **Yes**（见 `audience-rating.md`） |
| Independent security review? | **No**（当前未做第三方审计） |

## 3. Play Console 填报步骤

1. **App content → Data safety → Data collection and security**
   - 选择「Yes, this app collects user data」→ 按 §1 逐项添加；
   - 每项设置：Collected / Not shared / Required or Optional / 目的（App functionality、Personalization、Analytics、Security）；
   - 勾选「Encrypted in transit」与「Users can request data deletion」。
2. **Data types**：只勾选 §1 中标「是」的类型，其余保持不勾选。
3. **Data usage and handling**：全部选择「Not shared」，不勾选广告、不出售。
4. **Government requests**：按实际填写（当前无依法定程序对外提供记录）。
5. 保存后回到 App content 概览，确认 Data safety 状态为「Submitted」。

## 4. 与隐私政策一致性核对

| 隐私政策条款 | 内容 | Data Safety 对应项 | 核对 |
|---|---|---|---|
| §1.1 注册登录 | 手机号、密码哈希 | Phone number | 一致（密码不入表，按哈希存储） |
| §1.1 昵称 | 可选 | Name（Optional） | 一致 |
| §1.1 角色/学段/年级 | 学生必需 | Other info | 一致 |
| §1.2 学习记录 | 答题、错题、测评、时长 | App interactions | 一致 |
| §1.3 设备与日志 | 设备型号、系统版本、崩溃摘要、IP | Diagnostics / Crash logs / Device or other IDs | 一致 |
| §1.4 不收集 | 位置、通讯录、相机、麦克风、相册 | 全部为「否」 | 一致 |
| §5 第三方 SDK | 无广告 / 统计 / 推送 SDK | 无共享、无广告 | 一致 |
| §6.3 注销 | 15 个工作日 | 删除入口与 URL | 一致 |

## 5. 提审前检查

- [ ] Data Safety 与 `docs/privacy.md` 逐项一致，新增功能（如会员、推送）已重新申报
- [ ] 「Encrypted in transit」已勾选，且生产环境证书有效（R-02）
- [ ] 删除请求路径可实际走通（R-04 已验收，11 月复测）
- [ ] 隐私 URL 公网可访问，内容与 App 内置一致（R-03/R-06）
- [ ] 未将云服务商填写为「第三方共享」
