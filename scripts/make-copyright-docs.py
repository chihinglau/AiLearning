"""R-05 软件著作权申请材料生成：源程序文档（60 页）+ 操作说明书。

用法：
    backend\\.venv\\Scripts\\python.exe scripts\\make-copyright-docs.py

输出目录：release/software-copyright/
    source-code.docx      源程序鉴别材料（前 30 页 + 后 30 页，每页 50 行）
    user-manual.docx      文档鉴别材料（操作说明书）
    metadata.json         登记申请表所需的软件信息
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Iterable

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "release" / "software-copyright"
SOURCE_DIRS = [ROOT / "backend" / "app", ROOT / "app" / "lib"]
SOURCE_SUFFIXES = {".py", ".dart"}
LINES_PER_PAGE = 50
TOTAL_PAGES = 60

SOFTWARE_NAME = "深爱学学习辅助软件"
VERSION = "V1.0"
COPYRIGHT_OWNER = "（待填写：著作权人）"
FINISH_DATE = "2026-11-07"


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for base in SOURCE_DIRS:
        files.extend(
            sorted(
                path
                for path in base.rglob("*")
                if path.is_file() and path.suffix in SOURCE_SUFFIXES
            )
        )
    return files


def collect_lines() -> tuple[list[str], int]:
    lines: list[str] = []
    total = 0
    for path in iter_source_files():
        rel = path.relative_to(ROOT).as_posix()
        lines.append(f"# ===== {rel} =====")
        text = path.read_text(encoding="utf-8", errors="replace")
        body = [line.rstrip() for line in text.splitlines()]
        lines.extend(body)
        lines.append("")
        total += len(body)
    return lines, total


def _set_run_font(run, name: str, size: float, bold: bool = False) -> None:
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)


def _setup_page(section) -> None:
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.1)
    section.bottom_margin = Cm(1.6)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(1.8)
    section.header_distance = Cm(1.0)
    section.footer_distance = Cm(0.8)


def _add_header_footer(section, page_no: int) -> None:
    header = section.header
    header.is_linked_to_previous = False
    paragraph = header.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(f"{SOFTWARE_NAME} {VERSION}    源程序")
    _set_run_font(run, "宋体", 9)

    footer = section.footer
    footer.is_linked_to_previous = False
    text = footer.paragraphs[0]
    text.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = text.add_run(f"第 {page_no} 页  共 {TOTAL_PAGES} 页")
    _set_run_font(run, "宋体", 9)


def build_source_document(lines: list[str], total_source_lines: int) -> None:
    pages = [lines[i : i + LINES_PER_PAGE] for i in range(0, len(lines), LINES_PER_PAGE)]
    if len(pages) > TOTAL_PAGES:
        head = pages[: TOTAL_PAGES // 2]
        tail = pages[-(TOTAL_PAGES // 2) :]
        used = head + tail
    else:
        used = pages

    doc = Document()
    first = doc.sections[0]
    _setup_page(first)

    for index, page_lines in enumerate(used, start=1):
        section = first if index == 1 else doc.add_section(WD_SECTION.NEW_PAGE)
        _setup_page(section)
        _add_header_footer(section, index)
        for line in page_lines:
            paragraph = doc.add_paragraph()
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
            paragraph.paragraph_format.line_spacing = Pt(12)
            run = paragraph.add_run(line.replace("\t", "    "))
            _set_run_font(run, "Courier New", 8)

    doc.core_properties.title = f"{SOFTWARE_NAME} {VERSION} 源程序"
    doc.core_properties.author = COPYRIGHT_OWNER
    out = OUT_DIR / "source-code.docx"
    doc.save(out)
    print(f"source-code.docx: {len(used)} 页 / 源程序 {total_source_lines} 行")


MANUAL_SECTIONS: list[tuple[str, list[str]]] = [
    (
        "1 软件概述",
        [
            "深爱学学习辅助软件是一款面向小学、初中、高中学生的 K12 学科学习辅助工具，"
            "覆盖教材同步学习、知识点讲解、智能练习、单元测试、期中期末与模考等场景，"
            "并为家长与教师提供学情查看与作业管理能力。",
            "软件以“教材—章节—知识点—题目”四级内容结构组织学习资源，学生绑定所在年级与教材后，"
            "系统按掌握度推荐下一步学习内容，形成“学—练—测—评”的完整闭环。",
            "本说明书用于说明软件的运行环境、安装启动、主要功能模块与操作流程，"
            "供软件著作权登记与用户使用参考。",
        ],
    ),
    (
        "2 运行环境",
        [
            "客户端：Android 8.0 及以上或 HarmonyOS 2.0 及以上智能手机；运行内存 2 GB 及以上；"
            "存储空间 200 MB 及以上；需可访问互联网。",
            "服务端：Linux 服务器（推荐 2 核 4 GB 及以上）；Python 3.11+ 运行环境；"
            "数据库支持 SQLite（开发调试）或 PostgreSQL 16（生产部署）；提供 HTTPS 访问。",
            "网络要求：客户端通过 HTTPS 访问服务端接口；首次启动需要联网完成政策同意与账号登录，"
            "已缓存内容可在弱网环境下离线查看。",
        ],
    ),
    (
        "3 安装与启动",
        [
            "1. 在应用商店搜索并下载“深爱学”，或通过安装包安装。",
            "2. 首次启动展示隐私政策与用户协议，须阅读并主动勾选“我已阅读并同意”后点击“同意并进入”；"
            "不同意将退出应用。",
            "3. 进入登录页，使用手机号与密码登录；新用户点击“注册”完成手机号注册。",
            "4. 注册时需选择学段与年级；小学、初中、高中学生按提示完成必填信息。"
            "未满 14 周岁的儿童账号需由家长确认后方可完整使用。",
        ],
    ),
    (
        "4 账号与登录",
        [
            "登录成功后进入应用主界面。主界面底部为“学习”“错题本”“我的”三个标签页。",
            "“我的”页提供个人信息、教材管理、家长中心、班级与作业、账号与安全、隐私政策、"
            "用户协议与联系我们等入口。",
            "账号与安全页展示今日学习时长、数据导出与账号注销入口。注销账号需二次确认，"
            "提交后账号立即停用并匿名化，全部登录凭证失效，家长绑定关系解除；"
            "平台将在 15 个工作日内完成删除或匿名化处理。",
            "数据导出：点击“导出我的数据”，系统生成当前账号的脱敏数据（含个人资料、学习统计、"
            "答题记录、错题、掌握度、练习与考试记录等），并复制到剪贴板便于保存。",
        ],
    ),
    (
        "5 教材绑定与学习首页",
        [
            "首次进入“学习”页时，系统按学段与年级推荐深圳地区使用的教材版本，"
            "学生可一键自动绑定，也可在“教材管理”中手动选择其他版本。",
            "教材绑定后，“学习”页展示当前教材、今日学习计划、继续学习入口、推荐任务与待办考试。",
            "学习首页按“复习到期 → 薄弱知识点 → 中等掌握度 → 继续学习 → 每日一练”的优先级推荐下一步任务，"
            "点击卡片即可进入对应知识点或练习。",
            "若教材版本与当前年级不匹配，系统会提示冲突并要求确认后再开始学习。",
        ],
    ),
    (
        "6 知识点学习",
        [
            "进入教材后可查看“单元—节—知识点”树形结构，每个知识点显示学习状态"
            "（未学习、学习中、待巩固、已掌握、复习中）与掌握度。",
            "知识点详情页提供讲解内容、前置知识点、最近学习时间与相关练习入口。",
            "点击“开始学习”记录学习行为；完成自测达到设定正确率后，知识点状态更新为“已掌握”。",
            "知识图谱页以图形方式展示知识点之间的前置关系，便于按顺序学习。",
        ],
    ),
    (
        "7 智能练习",
        [
            "在知识点、章节或教材范围内发起练习时，系统先展示练习预览，包括题量、知识点覆盖、"
            "预计时长与题型分布；题量不足时会给出提示。",
            "确认后进入答题页，逐题作答并即时判题；支持断点续答，中途退出后再次进入可继续上次进度。",
            "练习结算页展示正确率、用时、知识点表现与错题清单，并自动更新掌握度与错题本。",
            "家长可在家长中心为孩子设置每日学习时长；达到上限后，开始新的练习或考试会提示"
            "“今日学习时长已用完”，并展示解锁时间。",
        ],
    ),
    (
        "8 考试与报告",
        [
            "“考试”页提供单元测试、期中期末、真题与班级同卷模考；教师可向班级派发作业与模考。",
            "开始考试前展示试卷说明与限时；答题过程中显示剩余时间，超时自动交卷。",
            "客观题由系统自动判分，主观题支持学生自评并提交；教师可在批改页完成评分。",
            "考试报告展示总分、客观/主观得分、正确率、题型统计、知识点统计、错题与后续建议"
            "（错题重练、再考一次）。",
        ],
    ),
    (
        "9 错题本与复习",
        [
            "“错题本”按学科与时间汇集练习、考试中的错题，标注错误次数与最近错误时间。",
            "系统按记忆曲线安排复习计划，到期错题会在练习中按比例出现；完成复习后更新复习状态。",
            "错题详情支持查看原题、正确答案与解析，并可加入专项练习。",
        ],
    ),
    (
        "10 家长中心",
        [
            "家长使用手机号注册并绑定孩子账号，孩子确认后绑定生效；家长可切换查看多个孩子。",
            "家长中心展示孩子的学习统计、知识点掌握度、练习与考试记录、错题情况。",
            "家长可设置每日学习时长与青少年模式；关闭或调整后即时生效。",
        ],
    ),
    (
        "11 教师与班级",
        [
            "教师账号由学校管理员分配角色与权限；教师可查看所授班级、学生名单与班级学情。",
            "教师可创建作业与班级同卷模考，设置考试时间窗口，并在批改页完成主观题评分。",
            "班级统计页展示平均分、正确率、知识点薄弱项与成绩分布。",
        ],
    ),
    (
        "12 隐私与数据安全",
        [
            "软件遵循最小必要原则收集信息：手机号用于账号注册与登录，学习记录用于生成学情与推荐。",
            "隐私政策与用户协议在应用内与公网页面均可查看；政策版本升级后，用户需重新阅读并同意。",
            "数据传输采用 HTTPS；服务端对敏感错误信息统一脱敏，并对登录与注册接口实施频率限制。",
            "用户可随时导出个人数据或申请注销账号；注销后账号立即匿名化，相关数据按隐私政策留存期限处理。",
        ],
    ),
    (
        "13 常见问题",
        [
            "无法登录：请检查网络与手机号密码；连续多次失败会触发临时限制，稍后重试。",
            "题目加载失败：请确认已完成教材绑定且网络正常，必要时下拉刷新重试。",
            "提示今日学习时长已用完：由家长在家长中心调整每日时长，或次日自动恢复。",
            "忘记密码：请联系客服邮箱协助处理；儿童账号相关操作需家长确认。",
        ],
    ),
]


def build_user_manual() -> None:
    doc = Document()
    section = doc.sections[0]
    _setup_page(section)
    section.top_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(SOFTWARE_NAME)
    _set_run_font(run, "黑体", 22, bold=True)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("操作说明书")
    _set_run_font(run, "黑体", 18, bold=True)

    version = doc.add_paragraph()
    version.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = version.add_run(f"版本：{VERSION}")
    _set_run_font(run, "宋体", 12)

    owner = doc.add_paragraph()
    owner.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = owner.add_run(f"著作权人：{COPYRIGHT_OWNER}")
    _set_run_font(run, "宋体", 12)

    doc.add_paragraph()

    toc_title = doc.add_paragraph()
    run = toc_title.add_run("目  录")
    _set_run_font(run, "黑体", 15, bold=True)
    for heading, _ in MANUAL_SECTIONS:
        entry = doc.add_paragraph()
        entry.paragraph_format.space_after = Pt(2)
        run = entry.add_run(heading)
        _set_run_font(run, "宋体", 11)

    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    for heading, paragraphs in MANUAL_SECTIONS:
        head = doc.add_paragraph()
        head.paragraph_format.space_before = Pt(12)
        head.paragraph_format.space_after = Pt(6)
        run = head.add_run(heading)
        _set_run_font(run, "黑体", 14, bold=True)
        for text in paragraphs:
            body = doc.add_paragraph()
            body.paragraph_format.first_line_indent = Pt(24)
            body.paragraph_format.line_spacing = 1.5
            run = body.add_run(text)
            _set_run_font(run, "宋体", 11)

    footer = section.footer
    footer.is_linked_to_previous = False
    text = footer.paragraphs[0]
    text.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = text.add_run(f"{SOFTWARE_NAME} {VERSION}    操作说明书")
    _set_run_font(run, "宋体", 9)

    doc.core_properties.title = f"{SOFTWARE_NAME} {VERSION} 操作说明书"
    doc.core_properties.author = COPYRIGHT_OWNER
    out = OUT_DIR / "user-manual.docx"
    doc.save(out)
    print(f"user-manual.docx: {len(MANUAL_SECTIONS)} 章")


def build_metadata(total_source_lines: int, pages: int) -> None:
    metadata = {
        "软件全称": SOFTWARE_NAME,
        "版本号": VERSION,
        "开发完成日期": FINISH_DATE,
        "首次发表日期": "尚未发表",
        "著作权人": COPYRIGHT_OWNER,
        "开发方式": "独立开发",
        "权利取得方式": "原始取得",
        "软件用途": "K12 学生学科学习辅助：教材同步学习、知识点讲解、智能练习、单元测试与学情分析。",
        "技术特点": (
            "Flutter 跨端客户端 + FastAPI 服务端；教材—章节—知识点—题目四级内容结构；"
            "基于掌握度与记忆曲线的内容推荐、自适应组卷；RBAC 权限与数据范围控制；"
            "青少年模式每日时长管控与账号注销/数据导出合规能力。"
        ),
        "硬件环境": "客户端：Android/HarmonyOS 智能手机（RAM ≥2 GB）；服务端：x86_64 服务器（CPU 2 核、RAM ≥4 GB）。",
        "软件环境": (
            "客户端：Android 8.0+ / HarmonyOS 2.0+；"
            "服务端：Linux + Python 3.11+ + FastAPI + SQLAlchemy + PostgreSQL 16（或 SQLite）。"
        ),
        "编程语言": "Dart、Python、SQL",
        "源程序量": f"{total_source_lines} 行（提交前 30 页 + 后 30 页，共 {pages} 页，每页 50 行）",
        "申请材料": ["source-code.docx", "user-manual.docx", "本 metadata.json"],
        "生成日期": date.today().isoformat(),
    }
    out = OUT_DIR / "metadata.json"
    out.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("metadata.json: 已生成")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lines, total_source_lines = collect_lines()
    pages = min(TOTAL_PAGES, (len(lines) + LINES_PER_PAGE - 1) // LINES_PER_PAGE)
    build_source_document(lines, total_source_lines)
    build_user_manual()
    build_metadata(total_source_lines, pages)


if __name__ == "__main__":
    main()
