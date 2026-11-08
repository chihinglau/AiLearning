# -*- coding: utf-8 -*-
"""把 baseline/_raw/{subject}[_second].json 的目录原文，整理成可被 _validate_daily.py 解析的大纲 md。

用法：`python _build_outlines.py [subject|all] [first|second]`
产出：baseline/_outline_{subject}_{semester}_{YYYYMMDD}.md 与 _latest.md 副本。
只收事实性短标题（单元、章、节/课文名），不摘正文、例题、习题。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "baseline" / "_raw"
OUT = ROOT / "baseline"
STAMP = "20261107"

SUBJECTS = {
    "chinese": ("语文", "chinese"),
    "physics": ("物理", "physics"),
    "chemistry": ("化学", "chemistry"),
    "biology": ("生物", "biology"),
    "history": ("历史", "history"),
    "politics": ("道德与法治", "politics"),
    "geography": ("地理", "geography"),
    # math 不在此列：数学大纲由 _build_math_outline.py 生成（4-6 年级课时级来自学科网专辑，勿用本脚本覆盖）
}

UNIT_RE = re.compile(r"^第[一二三四五六七八九十]+单元")
CHAP_RE = re.compile(r"^第[一二三四五六七八九十]+章")
SECT_RE = re.compile(r"^(第[一二三四五六七八九十百]+节|第\d+节)")


def split_unit(label: str):
    """「第一单元·识字」→ 单元名、单元说明。"""
    if "·" in label:
        head, tail = label.split("·", 1)
        return f"{head} {tail}".strip(), tail.strip()
    return label.strip(), ""


def build_tree(items):
    """返回节点树：单元节点（子节点可为章），或无单元时的章节点。

    节点：{'name': str, 'children': [str 或 章节点]}
    """
    tree = []
    cur_unit = None
    cur_chap = None
    for raw in items:
        label = raw.strip()
        if not label or label in ("手机版", "电子课本网"):
            continue
        if UNIT_RE.match(label):
            name, _ = split_unit(label)
            cur_unit = {"name": name, "children": []}
            tree.append(cur_unit)
            cur_chap = None
            continue
        if CHAP_RE.match(label):
            node = {"name": label, "children": [], "is_chap": True}
            if cur_unit is None:
                tree.append(node)
            else:
                cur_unit["children"].append(node)
            cur_chap = node
            continue
        if cur_chap is not None:
            cur_chap["children"].append(label)
        elif cur_unit is not None:
            cur_unit["children"].append(label)
        # 单元与章都还没有的散项丢弃（多为导航残留）
    return tree


def with_alias(name: str) -> str:
    """单元/章名同时收录「带序号」与「裸名」两种写法，避免每日文件写裸名时误判越界。"""
    m = re.match(r"^(第[一二三四五六七八九十]+(?:单元|章))\s*(.+)$", name)
    if m:
        return f"{name} / {m.group(2)}"
    return name


def render(subject: str, display: str, books, semester: str = "first") -> str:
    sem_cn = "上册" if semester == "first" else "下册"
    lines = [f"# {display} {sem_cn}教材大纲基线（小学 1-6 / 初中 7-9）", ""]
    lines += [
        "## 一、口径",
        "",
        "- **教材完整性第一优先**：每日产出的 `section` 必须是本文件列出的单元名、章名或节/课文名之一，越界即视为「超出教材范围」。",
        "- **以现行新教材为准**：按现行册次取目录（秋季学期用秋版、春季学期用春版），不做新旧教材过渡映射。",
        "- **颗粒度**：单元/章 → 节（课文/课）两级；语文按「单元 → 课文/栏目」，理化生地按「单元 → 章 → 节」，政史按「单元 → 课」。",
        "- **版权边界**：本文件只记录目录标题（事实性短名），不含课文正文、例题、习题原文；每日题库须自拟题干，不照抄教材原题。",
        "- **一门课一天一节**：节内知识点 3-6 个、题 18-28 道；一节内容多可拆两天，但不跨节跳做。",
        "",
        "## 二、来源",
        "",
        "全部目录取自电子课本网（www.dzkbw.com）对应册次的目录锚点，逐册人工核对册次与版本年份：",
        "",
        "| 年级 | 册次（版本年份） | 来源 |",
        "|---|---|---|",
    ]
    for b in books:
        lines.append(f"| {b['grade']} | {b['label']} | {b['url']} |")
    lines += ["", "## 三、使用规则", "",
              "1. 每日选节顺序：按本文件表格从上到下推进，做过的节在台账登记，不回头重做。",
              "2. `section` 字段写本文件里的原名，不加书名号、不加「第X课时」。",
              "3. 表格中同一行「节/课文」列用 ` / ` 分隔，任意一个都可单独作为一天的任务。",
              "4. 若某节在本文件缺失，停手并在台账记「大纲待补：{节名}」，不要自拟节名。",
              ""]
    cn = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九"}
    for b in books:
        lines += [f"## {cn[b['grade']]}年级（{b['label']}）", ""]
        if "全一册" in b["label"]:
            lines += ["", "> 本册为**全一册**（上册秋季学期通常推进前 6 章左右）；大纲收录全册章节，以免后半册内容被误判越界，教研按台账顺序推进即可。", ""]
        lines += ["| 序 | 单元/章节 | 节/课文 |", "|---|---|---|"]
        tree = build_tree(b["items"])
        idx = 0
        for node in tree:
            children = node["children"]
            chaps = [c for c in children if isinstance(c, dict)]
            direct = [c for c in children if isinstance(c, str)]
            idx += 1
            lines.append(f"| {idx} | {with_alias(node['name'])} | {' / '.join(chaps[i]['name'] for i in range(len(chaps))) if chaps else (' / '.join(direct) if direct else '—')} |")
            for chap in chaps:
                idx += 1
                sects = " / ".join(chap["children"]) if chap["children"] else "—"
                lines.append(f"| {idx} | {with_alias(chap['name'])} | {sects} |")
            if chaps and direct:
                idx += 1
                lines.append(f"| {idx} | {with_alias(node['name'])}（其他栏目） | {' / '.join(direct)} |")
        lines.append("")
    if semester == "first":
        tail = [
            "- 英语（牛津深圳版）1-9：电子课本网无此版本，见 `_outline_english_first_latest.md`（另有来源）。",
            "- 数学 4-6 上册：本文件整数单元级，课时级见 `_outline_math_first_latest.md`（学科网同步专辑已补齐）。",
        ]
    else:
        tail = [
            "- 英语（牛津深圳版）1-9 下册：见 `_outline_english_second_latest.md`（另有来源，部分年级待补）。",
            "- 数学 4-6 下册：课时级节名待补（电子课本网侧栏只到单元）；本册按单元推进即可，不影响越界拦截。",
            "- 语文 4-6、9 年级下册：现行仍为 2019 版册次（新教材尚未推到该年级），属正常。",
        ]
    lines += ["## 待补清单", "", *tail, ""]
    return "\n".join(lines)


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    semester = sys.argv[2] if len(sys.argv) > 2 else "first"
    if only == "all":
        only = ""
    suffix = "" if semester == "first" else "_second"
    for subject, (display, _code) in SUBJECTS.items():
        if only and subject != only:
            continue
        src = RAW / f"{subject}{suffix}.json"
        if not src.exists():
            print(f"[skip] {subject} 无原始数据（{src.name}）")
            continue
        books = json.loads(src.read_text(encoding="utf-8"))
        text = render(subject, display, books, semester)
        path = OUT / f"_outline_{subject}_{semester}_{STAMP}.md"
        path.write_text(text, encoding="utf-8")
        (OUT / f"_outline_{subject}_{semester}_latest.md").write_text(text, encoding="utf-8")
        print(f"[ok] {subject}-{semester}: {len(books)} 册 -> {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
