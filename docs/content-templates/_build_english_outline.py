# -*- coding: utf-8 -*-
"""生成英语（沪教牛津版 / 深圳·广州用，六三制）上册教材大纲基线。

来源说明见文件内「来源」章节：小学 1-4 上册与初中学段取自新版（2024 起）公开目录，
小学 5-6 上册取自电子课本网 2025/2026 秋版册次；小学阶段新版课时板块命名各年级不同，
仅在已验证的年级写板块名，未验证的只写单元名。
"""

import json
import re
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent / "baseline"
STAMP = "20261107"

CN = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九"}

# 初中（7 上/8 上）每单元固定五个板块，逐单元专属标题未全部取到，故只写已验证的板块结构名
A_E = "A Viewing and listening / B Speaking / C Reading & Grammar in use / D Writing & Discovery / E Project"

# 每个年级：(册次标签, 来源, [(单元名, 板块/课时说明)])
BOOKS = {
    1: ("一年级英语上册(2024秋版)", "教习网 沪教牛津版(六三制一起)(2024)一上课文目录 + 21世纪教育网课时资源命名", [
        ("Unit 1 What is your family like?", "Ready Go / Story / Practice / Communicate / Extend / Letters"),
        ("Unit 2 How are you today?", "Ready Go / Story / Practice / Communicate / Extend / Letters"),
        ("Unit 3 What do you take to school?", "Ready Go / Story / Practice / Communicate / Extend / Letters"),
        ("Unit 4 What can you do?", "Ready Go / Story / Practice / Communicate / Extend / Letters"),
        ("Unit 5 What is your favourite animal?", "Ready Go / Story / Practice / Communicate / Extend / Letters"),
        ("Unit 6 What colours can you see?", "Ready Go / Story / Practice / Communicate / Extend / Letters"),
    ]),
    2: ("二年级英语上册(2025秋版)", "教习网 沪教牛津版(六三制一起)(2024)二上课文目录 + 同步预习单课时命名", [
        ("Unit 1 What can you do with your five senses?", "Ready Go / Story / Practice / Communicate / Extend / Sounds"),
        ("Unit 2 What do you like about your family?", "Ready Go / Story / Practice / Communicate / Extend / Sounds"),
        ("Unit 3 What is your favourite toy?", "Ready Go / Story / Practice / Communicate / Extend / Letters"),
        ("Unit 4 What is around your home?", "Ready Go / Story / Practice / Communicate / Extend / Letters"),
        ("Unit 5 What do you like about farms?", "Ready Go / Story / Practice / Communicate / Extend / Letters"),
        ("Unit 6 How do people celebrate the Mid-Autumn Festival?", "Ready Go / Story / Practice / Communicate / Extend / Letters"),
    ]),
    3: ("三年级英语上册(2025秋版)", "教习网 三上课文目录 + 21世纪教育网《【2024新版】沪教版（三起）英语三年级上册》课时清单", [
        ("Unit 1 How do we feel?", "Get ready / Explore / Grammar in use / Communicate / Extend"),
        ("Unit 2 What's interesting about families?", "Get ready / Explore / Communicate / Extend"),
        ("Unit 3 What do we look like?", "Get ready / Explore / Communicate / Extend"),
        ("Unit 4 How do we have fun?", "Get ready / Explore / Grammar in use / Communicate / Extend"),
        ("Unit 5 What do we eat?", "Get ready / Explore / Grammar in use / Communicate / Extend"),
        ("Unit 6 What do we like about small animals?", "Get ready / Explore / Communicate / Extend"),
        ("Unit 7 What do we know about weather?", "Get ready / Explore & Grammar in use / Communicate / Extend"),
        ("Unit 8 Why do we like birthdays?", "Get ready / Explore / Grammar in use / Communicate / Extend"),
        ("Project 1 / Project 2", "项目实践（学期内穿插，不单独作为每日节次）"),
    ]),
    4: ("四年级英语上册(2026秋版)", "学科网 2026-2027 学年沪教版四年级上册（新教材）单元复习系列 + 教习网 四上（2024）课时清单", [
        ("Unit 1 Where do people live?", "Get ready / Explore / Communicate / Extend"),
        ("Unit 2 Where do animals live?", "Get ready / Explore / Communicate / Extend"),
        ("Unit 3 How do we use numbers?", "Get ready / Explore / Communicate / Extend"),
        ("Unit 4 What do we buy?", "Get ready / Explore / Communicate / Extend"),
        ("Unit 5 How are the seasons different?", "Get ready / Explore / Communicate / Extend"),
        ("Unit 6 What's amazing about plants?", "Get ready / Explore / Communicate / Extend"),
        ("Unit 7 How do we keep safe on the road?", "Get ready / Explore / Communicate / Extend"),
        ("Unit 8 What do our grandparents do?", "Get ready / Explore / Communicate / Extend"),
        ("Project 1 / Project 2", "项目实践（学期内穿插，不单独作为每日节次）"),
    ]),
    5: ("五年级英语上册(2026秋版)", "电子课本网 沪教版五年级英语上册(2026秋版)目录 http://www.dzkbw.com/books/hjb/yingyu/5s_2026/001.htm", [
        ("Unit 1 What do we do at the weekend?", "Get Ready / Explore / Communicate & Extend"),
        ("Unit 2 How do we stay healthy?", "Get Ready / Explore / Communicate & Extend"),
        ("Unit 3 What do you know about different countries?", "Get Ready / Explore / Communicate & Extend"),
        ("Unit 4 What's interesting about holidays?", "Get Ready / Explore / Communicate & Extend"),
        ("Unit 5 What are living things?", "Get Ready / Explore / Communicate & Extend"),
        ("Unit 6 Why should we take care of the Earth?", "Get Ready / Explore / Communicate & Extend"),
        ("Unit 7 How do we celebrate festivals?", "Get Ready / Explore / Communicate & Extend"),
        ("Unit 8 How does music make us feel?", "Get Ready / Explore / Communicate & Extend"),
        ("Project 1 / Project 2", "项目实践（学期内穿插，不单独作为每日节次）"),
    ]),
    6: ("六年级英语上册(2026秋版)", "电子课本网 沪教版六年级英语上册(2026秋版)目录 http://www.dzkbw.com/books/hjb/yingyu/6s_2026/001.htm", [
        ("Unit 1 Why do people move to new places?", "课时 1 / 课时 2 / 课时 3（板块名未公开，按 3 课时推进）"),
        ("Unit 2 Why do we make art?", "课时 1 / 课时 2 / 课时 3"),
        ("Unit 3 How should we protect ourselves?", "课时 1 / 课时 2 / 课时 3"),
        ("Unit 4 What makes things move?", "课时 1 / 课时 2 / 课时 3"),
        ("Unit 5 How do inventions change our lives?", "课时 1 / 课时 2 / 课时 3"),
        ("Unit 6 What is a city?", "课时 1 / 课时 2 / 课时 3"),
        ("Project 1 / Project 2", "项目实践（学期内穿插，不单独作为每日节次）"),
    ]),
    7: ("七年级英语上册(2024秋版)", "电子课本网 沪教版七年级英语上册(2024秋版)目录 http://www.dzkbw.com/books/hjb/yingyu/oxford7s_2024/001.htm", [
        ("Starter 1 English is fun", "—"),
        ("Starter 2 English worldwide", "—"),
        ("Starter 3 English matters", "—"),
        ("Starter 4 English learning styles", "—"),
        ("Unit 1 Trying new things", A_E),
        ("Unit 2 Strong mind", A_E),
        ("Unit 3 Jobs", A_E),
        ("Unit 4 Smart home", A_E),
        ("Unit 5 Films", A_E),
        ("Unit 6 Mountains and rivers", A_E),
    ]),
    8: ("八年级英语上册(2025秋版)", "电子课本网 沪教版八年级英语上册(2025秋版)目录 http://www.dzkbw.com/books/hjb/yingyu/oxford8s_2025/001.htm", [
        ("Unit 1 Water", "A Facts about water / B Water in everyday life / C The land of little water / D Water protection / E Our water use in a day"),
        ("Unit 2 Digital life", A_E),
        ("Unit 3 Curious minds", A_E),
        ("Unit 4 Then and now", A_E),
        ("Unit 5 Teamwork", A_E),
        ("Unit 6 Life in the future", A_E),
    ]),
    9: ("九年级英语上册(2026秋版)", "电子课本网 沪教版九年级英语上册(2026秋版)目录 http://www.dzkbw.com/books/hjb/yingyu/oxford9s_2026/001.htm", [
        ("Unit 1 Teenage life", "—"),
        ("Unit 2 People and their jobs", "—"),
        ("Unit 3 Travellers' tales", "—"),
        ("Unit 4 Folk customs", "—"),
        ("Unit 5 Buildings", "—"),
        ("Unit 6 Pollution", "—"),
    ]),
}

UNIT_RE = re.compile(r"^(Unit|Starter)\b", re.IGNORECASE)


def with_alias(name: str) -> str:
    """同时收录「Unit N 标题」与裸标题，避免每日文件只写标题时误判越界。"""
    m = re.match(r"^((?:Unit|Starter)\s+\d+)\s+(.+)$", name, re.IGNORECASE)
    if m:
        return f"{name} / {m.group(2)}"
    return name


def render() -> str:
    lines = [
        "# 英语（沪教牛津版·深圳用）上册教材大纲基线（小学 1-6 / 初中 7-9）",
        "",
        "## 一、口径",
        "",
        "- **教材完整性第一优先**：每日产出的 `section` 必须是本文件列出的单元名（或整行 ` / ` 分隔的任一项），越界即视为「超出教材范围」。",
        "- **以现行新教材为准**：深圳小学英语自 2024 秋起逐年换用新版（2024 版，六三制），初中同步；本文件按 2024/2025/2026 秋版册次取目录，不做新旧过渡映射。",
        "- **颗粒度**：单元 → 课时板块。板块名已验证的年级照实写；未验证的只写单元名或「课时 1-3」，不臆造板块名。",
        "- **版权边界**：本文件只记录目录标题（事实性短名），不含课文正文、对话、例题；每日题库须自拟题干，不照抄教材原文。",
        "- **一门课一天一节**：一个板块一天，知识点 3-6 个、题 18-28 道；单元内不跳做。",
        "",
        "## 二、来源",
        "",
        "| 年级 | 册次（版本年份） | 主要来源 |",
        "|---|---|---|",
    ]
    for g in sorted(BOOKS):
        label, source, _ = BOOKS[g]
        lines.append(f"| {g} | {label} | {source} |")
    lines += ["", "## 三、使用规则", "",
              "1. 每日选节顺序：按本文件表格从上到下推进，做过的节在台账登记，不回头重做。",
              "2. `section` 字段写本文件里的原名（英文原样，保留大小写与问号），不加书名号。",
              "3. 表格「课时板块」列用 ` / ` 分隔，任意一个都可单独作为一天的任务。",
              "4. 若某单元在本文件缺失，停手并在台账记「大纲待补：{单元名}」，不要自拟单元名。",
              "5. 英语单元较多且每单元板块固定，允许同一单元连做 2-3 天，但必须做完再进下一单元。",
              ""]
    for g in sorted(BOOKS):
        label, _, units = BOOKS[g]
        lines += [f"## {CN[g]}年级（{label}）", "",
                  "| 序 | 单元/章节 | 课时板块 |", "|---|---|---|"]
        for i, (name, stage) in enumerate(units, 1):
            lines.append(f"| {i} | {with_alias(name)} | {stage} |")
        lines.append("")
    lines += ["## 待补清单", "",
              "- 九年级上册：单元名已核对，A-E 板块名暂未取到（不影响按单元推进）。",
              "- 六年级上册：单元名与 3 课时结构确认，板块具体命名未公开。",
              "- 下册大纲：全部学科尚未采集。",
              ""]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    text = render()
    for name in (f"_outline_english_first_{STAMP}.md", "_outline_english_first_latest.md"):
        (OUT_DIR / name).write_text(text, encoding="utf-8")
    total = sum(len(v[2]) for v in BOOKS.values())
    print(f"[ok] english: 9 册 {total} 条 -> _outline_english_first_{STAMP}.md")


if __name__ == "__main__":
    main()
