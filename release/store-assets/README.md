# 商店素材包（R-08）

> **用途**：Google Play / 华为 AppGallery（含 HarmonyOS NEXT 版）提审所需图片与文案。
> **生成方式**：`python scripts/make-store-assets.py --install-android --install-ohos`
> **数据性质**：全部为虚构示例数据（示例账号「小深」、示例家长、示例题目），不含教材封面、学校名称、真实学生姓名/手机号，每张截图底部标注「示例数据 · 仅用于商店展示」。

## 1. 素材清单

| 文件 | 尺寸 | 平台用途 |
|---|---|---|
| `icon-1024.png` | 1024×1024 | 母版（自适应图标 / 商店大图） |
| `icon-512.png` | 512×512 | Google Play 商店图标（32-bit PNG） |
| `icon-216.png` | 216×216 | 华为 AppGallery 应用图标 |
| `feature-graphic-1024x500.png` | 1024×500 | Google Play 特性图 |
| `screenshots/01-home.png` | 1080×1920 | 学习首页（今日计划 + 当前教材 + 快捷入口） |
| `screenshots/02-knowledge.png` | 1080×1920 | 知识点分层与掌握度 |
| `screenshots/03-question.png` | 1080×1920 | 答题页（题干、选项、解析提示） |
| `screenshots/04-practice.png` | 1080×1920 | 练习预览（题量、知识点覆盖、难度） |
| `screenshots/05-wrongbook.png` | 1080×1920 | 错题本（错因 + 复习计划） |
| `screenshots/06-report.png` | 1080×1920 | 学情报告（掌握度环、薄弱点、趋势） |
| `screenshots/07-parent.png` | 1080×1920 | 家长中心（时长、休息时段、青少年模式） |
| `screenshots/08-profile.png` | 1080×1920 | 我的（隐私政策、举报、注销入口） |

`assets.json` 记录每个文件的宽高、字节数与 sha256，归档与提审时用于核对，避免误传旧图。

## 2. 平台规格核对

| 项目 | Google Play | 华为 AppGallery |
|---|---|---|
| 图标 | 512×512 PNG，无圆角（商店自动裁切） | 216×216 PNG |
| 特性图 | 1024×500 PNG/JPG | 不要求 |
| 截图 | 2–8 张，320–3840 px，16:9 / 9:16 | 3–5 张，1080×1920 推荐 |
| 描述长度 | 名称 ≤30 字符；简短描述 ≤80 字符；完整描述 ≤4000 字符 | 名称 / 简介 / 详情按后台字数提示 |
| 隐私 URL | `https://<正式域名>/legal/privacy` | 同左 |

## 3. 已同步到客户端工程

| 目标 | 路径 | 值 |
|---|---|---|
| Android Launcher | `app/android/app/src/main/res/mipmap-{mdpi,hdpi,xhdpi,xxhdpi,xxxhdpi}/ic_launcher.png` | 48 / 72 / 96 / 144 / 192 |
| Android 应用名 | `app/android/app/src/main/AndroidManifest.xml` | `android:label="深爱学"` |
| Android 网络权限 | 同上 | release 源集显式声明 `INTERNET`（否则 release 包无法访问后端） |
| 鸿蒙应用名 | `app/ohos/AppScope/resources/base/element/string.json` | `深爱学` |
| 鸿蒙图标 | `app/ohos/AppScope/resources/base/media/app_icon.png` | 114×114 |

> 包名 `com.ailearning.ai_learning`、versionCode、签名 MD5 与 R-01/R-06 备案信息保持一致，不得因换图改名。

## 4. 合规红线自检

- [x] 截图无教材封面、出版社 logo、学校名称、班级名称
- [x] 示例学生为虚构昵称「小深」，无手机号、无真实姓名
- [x] 无「官方教材」「指定教辅」「名师」「提分保证」「押题」等禁用表述
- [x] 无广告位、无付费/课程售卖、无社交与排行榜
- [x] 特性图与截图均出现「内容仅供学习参考，与教材出版方无关」或免责说明
- [x] 不出现「深圳」「人教版」等可被理解为官方关联的标识（教材仅以「数学 · 三年级上册」呈现）
- [x] 图标与截图均不含真实二维码、客服电话或外链

## 5. 提审顺序

1. 用 `listing.md` 填报名称、简短描述、完整描述与更新说明；
2. 上传 `icon-512.png`（Play）或 `icon-216.png`（AppGallery）与 `feature-graphic-1024x500.png`；
3. 按 `data-safety.md` 填 Google Play Data Safety；
4. 按 `audience-rating.md` 填目标受众、Families 声明与 IARC 问卷；
5. 按 `huawei-privacy-label.md` 填 AppGallery 隐私标签；
6. 回填备案号 / 软著号后复核 `listing.md` 中的占位符；
7. 提审前重跑生成脚本一次，确认 `assets.json` 的 sha256 与上传文件一致。

## 6. 变更记录

| 日期 | 说明 |
|---|---|
| 2026-11-07 | 首次生成：图标 / 特性图 / 8 张截图；补齐 Data Safety、受众分级与华为隐私标签表单草稿 |
