# -*- coding: utf-8 -*-
"""生成英语（沪教版·牛津深圳版，六三制）1-9 年级下册大纲。

电子课本网 /books/hjb/yingyu/ 对下册多数册次返回 503，故本脚本内置清单式目录：
- 1 年级：深圳用六三制 12 单元（Module 1-4），Module 结构 + Unit 名；
- 2 年级：沪教版二下 9 单元；
- 3 年级：沪教版（2024）新教材 Unit 1-8 + Project 1/2（学科网电子课本目录）；
- 4 年级：沪教版四下(2026春版) Unit 1-8 + Project 1/2（电子课本网 4x_2026）；
- 5、6 年级：六三制一起/三起 深圳用 Module 1-4 各 3 单元；
- 7 年级：沪教版七下(2025春版) Unit 1-6，A-E 五板块；
- 8 年级：沪教版八下(2026春版·牛津上海版) Unit 1-6，每单元 6 个语篇；
- 9 年级：沪教版九下新教材 Unit 1-6（Unit 2 标题待补）。
只收单元名、板块名与语篇标题等事实性短名，不摘正文。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "baseline"
STAMP = "20261107"

A_E = "A Viewing and listening / B Speaking / C Reading & Grammar in use / D Writing & Discovery / E Project"

BOOKS = {
    1: {
        "label": "一年级英语下册（沪教牛津版·深圳用，六三制）",
        "source": "http://www.dzkbw.com/books/hjb/yingyu/oxford1x/ + 《沪教牛津版（深圳用）一年级下册教学设计合集》课文目录",
        "rows": [
            ("Module 1 Using my five senses", ["Unit 1 Look and see", "Unit 2 Listen and hear", "Unit 3 Taste and smell", "Revision 1"]),
            ("Module 2 My favourite things", ["Unit 4 Toys I like", "Unit 5 Food I like", "Unit 6 Drinks I like", "Revision 2"]),
            ("Module 3 Things around us", ["Unit 7 Seasons", "Unit 8 Weather", "Unit 9 Clothes", "Revision 3"]),
            ("Module 4 Things we enjoy", ["Unit 10 Activities", "Unit 11 New Year's Day", "Unit 12 A boy and a wolf", "Revision 4"]),
        ],
    },
    2: {
        "label": "二年级英语下册（沪教牛津版，六三制）",
        "source": "教习网「沪教牛津版（六三制）二年级下册英语课文目录」",
        "rows": [
            ("Unit 1-9", ["Unit 1 Farm animals", "Unit 2 In the circus", "Unit 3 My room", "Unit 4 In the park",
                          "Unit 5 Wash with water", "Unit 6 Eating and drinking", "Unit 7 Hot summer",
                          "Unit 8 Time", "Unit 9 Revision"]),
        ],
    },
    3: {
        "label": "三年级英语下册（沪教版 2024 新教材）",
        "source": "学科网《沪教版（2024）英语三年级下册电子课本目录》",
        "rows": [
            ("Unit 1-8", [
                "Unit 1 How do we spend our free time?",
                "Unit 2 How do we make friends?",
                "Unit 3 What do we wear?",
                "Unit 4 What sounds can we hear?",
                "Unit 5 Where can we see colours?",
                "Unit 6 What are our homes like?",
                "Unit 7 What do we do at school?",
                "Unit 8 What do you do on Children's Day?",
                "Project 1 A friend album",
                "Project 2 A wind-bell",
            ]),
        ],
    },
    4: {
        "label": "四年级英语下册（沪教版 2026 春版）",
        "source": "http://www.dzkbw.com/books/hjb/yingyu/4x_2026/001.htm",
        "rows": [
            ("Unit 1-8", [
                "Unit 1 What is your daily schedule?",
                "Unit 2 What do we like about school?",
                "Unit 3 What's great about jobs?",
                "Unit 4 How can we make music?",
                "Unit 5 How do we make art?",
                "Unit 6 How do we measure time?",
                "Unit 7 How do things change?",
                "Unit 8 How do people get along with each other?",
                "Project 1 Different jobs",
                "Project 2 A guest house",
                "Unit checklist",
            ]),
        ],
    },
    5: {
        "label": "五年级英语下册（沪教牛津版·深圳用，六三制）",
        "source": "教习网「沪教牛津版（六三制一起）五年级下册英语课文目录」",
        "rows": [
            ("Module 1 Changes and differences", ["Unit 1 Tidy up!", "Unit 2 Our new home", "Unit 3 In the future", "Revision 1", "Project 1"]),
            ("Module 2 Work and play", ["Unit 4 Reading is fun", "Unit 5 At the weekend", "Unit 6 Holidays", "Revision 2", "Project 2"]),
            ("Module 3 Things we do", ["Unit 7 Open Day", "Unit 8 Buying clothes", "Unit 9 Seeing the doctor", "Revision 3", "Project 3"]),
            ("Module 4 Things we enjoy", ["Unit 10 Great inventions", "Unit 11 Chinese festivals", "Unit 12 The giant's garden", "Project 4"]),
        ],
    },
    6: {
        "label": "六年级英语下册（沪教牛津版·深圳用，六三制三起）",
        "source": "教习网「沪教牛津版（六三制三起）六年级下册英语课文目录」",
        "rows": [
            ("Module 1 Changes and differences", ["Unit 1 You and me", "Unit 2 Changes in our lives", "Unit 3 Our school in the future"]),
            ("Module 2 Work and play", ["Unit 4 Art", "Unit 5 Crafts", "Unit 6 PE lessons"]),
            ("Module 3 Things we do", ["Unit 7 Helping others", "Unit 8 Reading signs", "Unit 9 Reusing things"]),
            ("Module 4 Things we enjoy", ["Unit 10 Great storybooks", "Unit 11 Western festivals", "Unit 12 The five peas"]),
        ],
    },
    7: {
        "label": "七年级英语下册（沪教版 2025 春版·牛津上海版）",
        "source": "http://www.dzkbw.com/books/hjb/yingyu/oxford7x_2025/001.htm",
        "rows": [
            ("Unit 1 Music", [A_E]), ("Unit 2 Language and communication", [A_E]), ("Unit 3 A helping hand", [A_E]),
            ("Unit 4 Honesty", [A_E]), ("Unit 5 Wild animals", [A_E]), ("Unit 6 Trees", [A_E]),
        ],
    },
    8: {
        "label": "八年级英语下册（沪教版 2026 春版·牛津上海版）",
        "source": "http://www.dzkbw.com/books/hjb/yingyu/oxford8x_2026/001.htm",
        "rows": [
            ("Unit 1 Art and artists", ["Art in my view", "My choice of an art class", "A famous artist",
                                       "My favourite work of art", "Art in different forms", "Works of art around us"]),
            ("Unit 2 Great inventions and discoveries", ["Great ancient inventions", "Great modern inventions",
                                                        "Stories behind great discoveries",
                                                        "The most useful invention in my view", "A world of aircraft",
                                                        "The development and influences of a great invention"]),
            ("Unit 3 Money", ["Daily use of money", "Managing pocket money", "Money in the economy",
                              "Spending and saving habits", "The history of money", "A charity sale plan"]),
            ("Unit 4 Fashion", ["Fashion in the past", "Personal style", "Changing fashion", "My fashion attitude",
                                "Fashion in ancient times", "Fashion design"]),
            ("Unit 5 Natural disasters", ["Learning about natural disasters", "Staying safe from natural disasters",
                                          "Surviving natural disasters", "Reporting natural disasters",
                                          "The fate of cities in natural disasters", "Being prepared for natural disasters"]),
            ("Unit 6 Friendship", ["Beginning of friendship", "Ups and downs in friendship", "Power of friendship",
                                   "Memories with friends", "Two poems on friendship", "“Recipes” for friendship"]),
            ("Culture corner", ["Exploring China: Great works of art"]),
            ("Exploring the world: Africa", ["Exploring the world: Africa"]),
            ("Literature corner", ["A chapter to start with: The Time Machine",
                                   "A scene to act out: The Merchant of Venice",
                                   "A poem to savour: The Arrow and the Song"]),
        ],
    },
    9: {
        "label": "九年级英语下册（沪教版新教材，2027 春）",
        "source": "学科网《【上好课】2026-2027 学年九年级英语下册同步备课系列（新教材沪教版）》专辑目录",
        "rows": [
            ("Unit 1 Sport and sportsmanship", ["Section 1 Experiencing and understanding language",
                                                "Section 2 Exploring and applying rules (Grammar)",
                                                "Section 3 Expressing and communicating ideas",
                                                "Section 4 Extending and developing competencies"]),
            ("Unit 2 Finding balance in life", ["Section 1 Experiencing and understanding language",
                                                "Section 2 Exploring and applying rules (Grammar)",
                                                "Section 3 Expressing and communicating ideas",
                                                "Section 4 Extending and developing competencies"]),
            ("Unit 3 Protecting the environment", ["Section 1 Experiencing and understanding language",
                                                   "Section 2 Exploring and applying rules (Grammar)",
                                                   "Section 3 Expressing and communicating ideas",
                                                   "Section 4 Extending and developing competencies"]),
            ("Unit 4 Natural disasters", ["Section 1 Experiencing and understanding language",
                                          "Section 2 Exploring and applying rules (Grammar)",
                                          "Section 3 Expressing and communicating ideas",
                                          "Section 4 Extending and developing competencies"]),
            ("Unit 5 Great explorers and explorations", ["Section 1 Experiencing and understanding language",
                                                         "Section 2 Exploring and applying rules (Grammar)",
                                                         "Section 3 Expressing and communicating ideas",
                                                         "Section 4 Extending and developing competencies"]),
            ("Unit 6 Experiencing different cultures", ["Section 1 Experiencing and understanding language",
                                                        "Section 2 Exploring and applying rules (Grammar)",
                                                        "Section 3 Expressing and communicating ideas"]),
        ],
    },
}

CN = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九"}
POINTS = {1: 5, 2: 6, 3: 10, 4: 12, 5: 14, 6: 14, 7: 18, 8: 20, 9: 18}


def render() -> str:
    lines = ["# 英语 下册教材大纲基线（沪教版·牛津深圳版，1-9 年级）", "",
             "## 一、口径", "",
             "- **教材完整性第一优先**：每日产出的 `section` 必须是本文件列出的单元名、板块名或语篇标题之一，越界即视为「超出教材范围」。",
             "- **深圳用六三制**：小学按六三制（深圳）册次，初中按沪教版牛津上海版；**五四制（上海版）册次不得混用**。",
             "- **颗粒度**：1-6 年级「Module/单元 → Unit」，7-9 年级「Unit → 板块/语篇」。",
             "- **版权边界**：只记录单元名与板块标题（事实性短名），不含课文原文、词汇表、练习。",
             "- **一门课一天一个板块**：板块内知识点 3-6 个、题 18-28 道；单元内板块多可拆两天。",
             "",
             "## 二、来源", "",
             "| 年级 | 册次 | 来源 |", "|---|---|---|"]
    for g in range(1, 10):
        lines.append(f"| {g} | {BOOKS[g]['label']} | {BOOKS[g]['source']} |")
    lines += ["", "## 三、使用规则", "",
              "1. 按表格从上到下推进，做过的单元/板块在台账登记，不回头重做。",
              "2. `section` 写本文件里的原名（英文原名，保留大小写与问号）；「Revision N」「Project N」也算合法节点。",
              "3. A-E 五板块写作 `A Viewing and listening / B Speaking / C Reading & Grammar in use / D Writing & Discovery / E Project`，任选其一即可作一天任务。",
              "4. 文件名带学期后缀 `english_g{grade}_second_<日期>.json`。",
              ""]

    for g in range(1, 10):
        lines += [f"## {CN[g]}年级（{BOOKS[g]['label']}）", "", "| 序 | 单元/模块 | 板块/课时 |", "|---|---|---|"]
        idx = 0
        for unit, children in BOOKS[g]["rows"]:
            idx += 1
            lines.append(f"| {idx} | {unit} | {' / '.join(children) if children else '—'} |")
        lines.append("")

    lines += ["## 待补清单", "",
              "- 二年级下册：来源为教习网课文目录（沪教牛津版六三制二下，9 单元），建议开学前用实体书核对一次。",
              "- 教材版本仍在按年级推行新教材，2027 春后如册次更替，本文件需重取。",
              ""]
    return "\n".join(lines)


def main():
    text = render()
    p1 = OUT / f"_outline_english_second_{STAMP}.md"
    p1.write_text(text, encoding="utf-8")
    (OUT / "_outline_english_second_latest.md").write_text(text, encoding="utf-8")
    print(f"[ok] {p1.name} {len(text)} 字节")


if __name__ == "__main__":
    main()
