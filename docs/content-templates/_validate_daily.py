"""每日教研 JSON 自检（不连数据库、不执行导入，纯标准库）。

用法（在任意目录执行，路径按实际填）：
    python _validate_daily.py math_g8_first_20261108.json
    python _validate_daily.py . --expect-subject math --expect-grade 8 --expect-version 北师大版 --expect-semester first
    python _validate_daily.py math_g1_first_20261108.json --kp-baseline _knowledge-points-baseline_20261107.json

加 --kp-baseline 后额外做重名检查（这是每日任务最容易踩的坑）：
    - 本文件新建的 point 名在库内已存在 → 错误：同 section 会覆盖旧讲解，
      不同 section 会被导入器自动改名成「…（要点）」、在库里造出语义重复；
    - 写作上要复用一个库内已有知识点，正确做法是本文件不声明它、题目直接按旧名挂载；
    - 题目挂载点库内不存在、或库内同名节点 ≥2 个（歧义，导入会拒绝）→ 错误。

退出码：0 = 全部通过；1 = 有错误（错误逐条列出，行号指向 JSON 结构位置）。
说明：本脚本按 backend/app/services/content_import.py 的校验口径实现，
      并额外补上 schema 校验查不出来的跨引用检查（前置知识、知识点挂载）。
"""

from __future__ import annotations

import argparse
import ast
import glob
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

# 纯元数据键：不参与内容比对（打 `_legacy` 标记只加这两个键）。
# 与 backend/app/services/content_import.py 的 METADATA_KEYS 保持一致——
# 改一处必须同步改另一处，否则 manifest 的「仅元数据变更」判定会失效。
_METADATA_KEYS = ("_legacy", "_legacy_note")

# ===== 答案机检：算式求值与选项闭合 =====
# 只解析「含运算符的等式」，把等号左边用 ast 安全求值后与右边比对。
# 目的：把「结构对了但算错了」这类自检盲区变成机器可判的错误。
ARITH_TOL = 1e-6
_EQ_RE = re.compile(r"(-?\d[\d\s\.\+\-\*×÷/\(\)]*?)\s*=\s*(-?\d+(?:\.\d+)?)")
_HAS_OP_RE = re.compile(r"\d\s*[+\-*×÷/]\s*\(?\s*-?\d")
_ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Load,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.USub,
    ast.UAdd,
)
# 解析里用来解释「这个选项为什么错」的反面算式，不参与验算
_WRONG_DEMO_WORDS = ("不对", "不正确", "错误", "弄反", "是错", "不能", "错", "不成立")


_CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def load_outline(
    path: Path,
) -> tuple[str | None, dict[int, set[str]], dict[int, set[tuple[str, str]]]]:
    """解析大纲基线 md。

    返回 (学科代码, {年级: 允许名集合}, {年级: (单元, 板块) 二元组集合})。

    学科代码取自文件名 `_outline_{subject}_…`。允许名集合兼容三种写法：单元名、
    板块名、`单元 / 板块` 复合名。pairs 只登记表格同一行里真实存在的
    「单元 × 板块」组合：英语等学科在多个单元里复用同名板块（Story / Extend …），
    扁平 set 会把 Unit 6 的 Story 误当成 Unit 1 的 Story，必须按二元组校验。
    """
    subject = None
    for token in re.split(r"[_\-. ]+", path.stem):
        if token in SUBJECTS:
            subject = token
            break
    grades: dict[int, set[str]] = {}
    pairs: dict[int, set[tuple[str, str]]] = {}
    current: int | None = None

    def parts_of(cell: str) -> list[str]:
        return [
            p.strip()
            for p in re.split(r"\s*/\s*", cell.replace("**", ""))
            if p.strip()
            and not p.strip().startswith("（")
            and len(p.strip()) <= 60
        ]

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#"):
            current = None
            for cn, num in _CN_NUM.items():
                if f"{cn}年级" in line:
                    current = num
                    grades.setdefault(current, set())
                    pairs.setdefault(current, set())
                    break
            continue
        if current is None or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if set(cells[0]) <= set("-: "):
            continue  # 分隔行
        first = cells[0].replace("**", "").strip()
        if first in ("序", "章", "单元", "年级"):
            continue  # 表头行
        # 两种表格：三列（序 | 名称 | 节）取第 2 列；两列（名称 | 节）取第 1 列
        numbered = first in ("—", "") or first.isdigit()
        name = cells[1] if numbered else first
        name = name.replace("**", "").strip()
        if name and name not in ("—", "节", "单元 / 板块", "节（课时）"):
            grades[current].add(name)
        # 节名串（「a / b / c」）拆开一并收，允许任务按节写 section
        for cell in cells[1:]:
            for part in re.split(r"\s*/\s*", cell.replace("**", "")):
                part = part.strip()
                if (
                    part
                    and part not in ("—", "节", "单元 / 板块", "待补")
                    and not part.startswith("（")
                    and len(part) <= 60
                ):
                    grades[current].add(part)
            for token in re.findall(r"`([^`]+)`", cell):
                grades[current].add(token)
        # 同一行的「单元」×「板块」二元组；复合名一并加入允许集合
        unit_cell = cells[1] if numbered else cells[0]
        sec_cell = (
            cells[2] if (numbered and len(cells) > 2)
            else (cells[1] if len(cells) > 1 else "")
        )
        for unit in parts_of(unit_cell):
            for sec in parts_of(sec_cell):
                pairs[current].add((unit, sec))
                grades[current].add(f"{unit} / {sec}")
    return (
        subject,
        {grade: names for grade, names in grades.items() if names},
        {grade: ps for grade, ps in pairs.items() if ps},
    )


def _sentence_at(text: str, index: int) -> str:
    """取包含 index 的分句，用于判断等式是不是「反面示例」。"""
    start = 0
    for mark in "。！？；\n":
        pos = text.rfind(mark, 0, index)
        if pos != -1:
            start = max(start, pos + 1)
    end = len(text)
    for mark in "。！？；\n":
        pos = text.find(mark, index)
        if pos != -1:
            end = min(end, pos)
    return text[start:end]


def safe_eval(expr: str) -> float | None:
    """把算式字符串安全求值；不认识的结构一律返回 None（宁可不判，不误杀）。"""
    expr = (
        expr.replace("×", "*")
        .replace("÷", "/")
        .replace("（", "(")
        .replace("）", ")")
        .strip()
    )
    if not expr or len(expr) > 80:
        return None
    if not re.fullmatch(r"[0-9\.\+\-\*/\(\) ]+", expr):
        return None
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            return None
    try:
        value = eval(compile(tree, "<eq>", "eval"), {"__builtins__": {}}, {})
    except (ZeroDivisionError, OverflowError):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)

SUBJECTS = {
    "chinese", "math", "english", "physics", "chemistry",
    "biology", "history", "geography", "politics",
}
Q_TYPES = {"choice", "multiple", "judge", "fill", "answer"}
SOURCE_TYPES = {"original", "adapted", "licensed", "public", "external"}
STATUSES = {"published", "draft", "offline"}
SEMESTERS = {"first", "second"}

# ===== 产出规格机检（2026-11-09 新增）=====
# 此前这些规格只写在任务指令与 04 手册里，脚本一条都不查，导致
# 「每知识点 0 题」「题量超出 18~28」「知识点 7 个以上」全都能通过自检。
# 口径原文：`_daily-task-instruction.md`「每日产出量：新增知识点 3~6 个；新增题目 18~28 道
# （每个知识点至少 4 道）」——按批次（一个文件）计，不按节计。
CHAPTER_Q_MIN, CHAPTER_Q_MAX = 18, 28      # 每个章节（一轮抓的批次）题量
POINTS_PER_FILE_MIN, POINTS_PER_FILE_MAX = 3, 6         # 每批次新增知识点数
MIN_Q_PER_POINT = 4                        # 每个声明的知识点至少挂几道题
DIFFICULTY_BUCKETS = (("1-2", (1, 2), 0.40), ("3", (3,), 0.40), ("4-5", (4, 5), 0.20))
DIFFICULTY_TOL_PP = 15                     # 难度配比容差（百分点）
_FRAGMENT_RE = re.compile(r"_r\d+\.json$", re.IGNORECASE)


class Checker:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warns: list[str] = []
        self.kp_baseline: dict | None = None      # {"math": {"1": {"名称": 次数}}}
        self.subject: str | None = None
        self.grade: int | None = None
        self.template_mode = False                 # 学科模板文件（math.json 等）的重名检查降级为提醒
        self.imported = False                      # 该文件已入库（重名/多选闭合降级为提醒）
        self.import_state = "unknown"              # unchanged / meta_only / changed / unknown（见 _manifest_import_state）
        self.imported_path = False                 # 该路径曾成功入库（内容被改过）：仅重名降级，避免自指误判
        self.legacy = False                        # 文件带 "_legacy": true（旧样章内容，占位章节清理前的产物）
        self.book = False                          # 整册归集文件（*_book.json）：「每日批次」规格不适用

    def _baseline_names(self) -> dict[str, int] | None:
        """返回本学科本年级的「名称 -> 库内出现次数」，基线不可用时返回 None。"""
        if not self.kp_baseline:
            return None
        return (self.kp_baseline.get(str(self.subject)) or {}).get(str(self.grade)) or {}

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warns.append(msg)

    # ---------- 结构层 ----------
    def check_top(self, data: dict, expects: dict) -> None:
        subject = data.get("subject")
        if subject not in SUBJECTS:
            self.err(f"subject 非法：{subject!r}，应为 {sorted(SUBJECTS)}")
        grade = data.get("grade")
        if not isinstance(grade, int) or isinstance(grade, bool) or not 1 <= grade <= 12:
            self.err(f"grade 必须是 1~12 整数，当前 {grade!r}")
        if not str(data.get("version") or "").strip():
            self.err("version 不能为空")
        if data.get("semester", "first") not in SEMESTERS:
            self.err(f"semester 只能是 first/second，当前 {data.get('semester')!r}")

        for key, expected in expects.items():
            if expected is None:
                continue
            actual = data.get(key, "first" if key == "semester" else None)
            if str(actual) != str(expected):
                self.err(f"{key} 与配置不符：文件为 {actual!r}，配置为 {expected!r}")

        if not isinstance(data.get("knowledge") or [], list):
            self.err("knowledge 必须是数组")
        if not isinstance(data.get("chapters") or [], list):
            self.err("chapters 必须是数组")
        if not (data.get("knowledge") or []) and not (data.get("chapters") or []):
            self.err("knowledge 与 chapters 不能同时为空")
        self.subject = str(subject) if subject else None
        self.grade = grade if isinstance(grade, int) else None
        # 2026-11-12：semester 必须落到实例上，否则章节范围校验永远取「学科」兜底键（= 上册大纲），
        # 下册册子会被整册误判为「不在本册教材大纲内」。
        self.semester = str(data.get("semester") or "first")

    # ---------- 来源字段 ----------
    def check_source(self, item: dict, label: str, *, is_question: bool) -> None:
        stype = item.get("source_type", "original")
        if stype not in SOURCE_TYPES:
            self.err(f"{label} source_type 非法：{stype!r}，应为 {sorted(SOURCE_TYPES)}")
            return
        if stype != "original" and not str(item.get("source_name") or "").strip():
            self.err(f"{label} source_type={stype} 时必须填 source_name")
        if stype == "licensed" and not str(item.get("license_note") or "").strip():
            self.err(f"{label} source_type=licensed 时必须填 license_note")
        if is_question and stype == "adapted" and not str(item.get("adapted_from") or "").strip():
            self.err(f"{label} source_type=adapted 时必须填 adapted_from")
        if is_question and stype == "external":
            if str(item.get("status", "published")) != "draft":
                self.err(f"{label} source_type=external 时 status 必须为 draft")
        if not is_question and str(item.get("adapted_from") or "").strip():
            self.warn(f"{label} 的 adapted_from 不会被导库保存（知识点不采集该字段）")

    # ---------- 知识树 ----------
    def check_knowledge(self, data: dict) -> tuple[set[str], set[str]]:
        sections: set[str] = set()
        points: set[str] = set()
        raw = data.get("knowledge") or []

        for item in raw:
            if not isinstance(item, dict):
                self.err("knowledge 中存在非对象条目")
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                self.err("knowledge 中存在空名称")
                continue
            node_type = item.get("node_type", "point")
            if node_type not in {"section", "point"}:
                self.err(f"知识点「{name}」node_type 只能是 section/point")
                continue
            if node_type == "section":
                if name in sections:
                    self.err(f"节名称重复：{name}")
                sections.add(name)
            else:
                if name in points:
                    self.err(f"知识点名称重复：{name}")
                points.add(name)
                if not str(item.get("parent") or "").strip():
                    self.err(f"知识点「{name}」缺少 parent")
                known = self._baseline_names()
                if known is not None:
                    hits = known.get(name, 0)
                    report = self.warn if (
                        self.template_mode or self.imported or self.imported_path
                    ) else self.err
                    if hits >= 2:
                        report(
                            f"知识点「{name}」库内同年级已有 {hits} 个同名节点（歧义），"
                            "按名称引用会失败，请换一个唯一名称"
                        )
                    elif hits == 1:
                        report(
                            f"知识点「{name}」库内已有同名节点：同一 section 下会覆盖它的讲解与来源，"
                            "其他 section 下导入器会自动改名成「…（要点）」并在库里造出一份语义重复；"
                            "要复用它就别在本文件声明（题目直接按旧名挂载即可），否则请换真正新增的名称"
                        )
                    if "（要点" in name:
                        self.warn(
                            f"知识点「{name}」带「（要点）」后缀，通常是从库内既有节点抄来的；"
                            "确认这是真新增而不是重复入库"
                        )
            self.check_source(item, f"知识点「{name}」", is_question=False)

        for item in raw:
            if not isinstance(item, dict) or item.get("node_type", "point") != "point":
                continue
            parent = str(item.get("parent") or "").strip()
            if parent and parent not in sections:
                self.err(
                    f"知识点「{item.get('name')}」的 parent「{parent}」未在同文件声明"
                    "（每日新增必须重新声明该 section）"
                )
            for pre in item.get("prerequisites") or []:
                pre = str(pre).strip()
                if pre and pre not in points and pre not in sections:
                    self.err(
                        f"知识点「{item.get('name')}」的前置「{pre}」不在本文件内"
                        "（跨文件引用会导致导入失败）"
                    )
        return sections, points

    # ---------- 题目 ----------
    def check_questions(self, data: dict, sections: set[str], points: set[str]) -> int:
        total = 0
        chapters: set[str] = set()
        for chapter in data.get("chapters") or []:
            if not isinstance(chapter, dict):
                self.err("chapters 中存在非对象条目")
                continue
            cname = str(chapter.get("name") or "").strip()
            if not cname:
                self.err("章节名为空")
                continue
            if cname in chapters:
                self.err(f"章节名称重复：{cname}")
            chapters.add(cname)
            order = chapter.get("order_index", 0)
            if not isinstance(order, int) or order <= 0:
                self.warn(f"章节「{cname}」order_index={order!r}，新建章节会被排到最前")

            seen: dict[tuple[str, str], str] = {}
            for question in chapter.get("questions") or []:
                if not isinstance(question, dict):
                    self.err(f"章节「{cname}」存在非对象题目")
                    continue
                total += 1
                qtype = question.get("q_type")
                stem = str(question.get("stem") or "").strip()
                if qtype not in Q_TYPES:
                    self.err(f"章节「{cname}」题型非法：{qtype!r}")
                    continue
                if not stem:
                    self.err(f"章节「{cname}」存在空题干")
                    continue
                label = f"题目「{stem[:24]}…」"

                dup_key = (str(qtype), stem)
                if dup_key in seen:
                    self.err(f"{label} 题干与本章节前一题重复（同题型同题干会被跳过）")
                seen[dup_key] = stem

                answer = question.get("answer")
                if not isinstance(answer, dict) or answer.get("value") in (None, ""):
                    self.err(f"{label} 缺少 answer.value")
                else:
                    self.check_answer(question, qtype, answer.get("value"), label)
                    self.check_arithmetic(question, qtype, answer.get("value"), label)

                difficulty = question.get("difficulty", 2)
                if (
                    not isinstance(difficulty, int)
                    or isinstance(difficulty, bool)
                    or not 1 <= difficulty <= 5
                ):
                    self.err(f"{label} difficulty={difficulty!r}，必须是 1~5 整数")

                kp = str(question.get("knowledge_point") or "").strip()
                if not kp:
                    self.err(f"{label} 缺少 knowledge_point")
                elif kp not in points and kp not in sections:
                    known = self._baseline_names()
                    if known is None:
                        self.warn(
                            f"{label} 挂载的「{kp}」不在本文件内，导入时将按名称到库中查找；"
                            "同年级同名节点存在多个会失败"
                        )
                    elif kp not in known:
                        self.err(
                            f"{label} 挂载的「{kp}」既不在本文件、库里也没有，导入会失败"
                        )
                    elif known[kp] >= 2:
                        self.err(
                            f"{label} 挂载的「{kp}」库内有 {known[kp]} 个同名节点（歧义），"
                            "导入会拒绝；请改挂本文件里新建的唯一 point"
                        )
                    else:
                        self.warn(
                            f"{label} 挂载的是库内已有知识点「{kp}」（唯一，可导入）"
                        )

                status = question.get("status", "published")
                if status not in STATUSES:
                    self.err(f"{label} status 非法：{status!r}")
                self.check_source(question, label, is_question=True)

                if qtype == "multiple":
                    analysis = str(question.get("analysis") or "")
                    keys = [
                        str(opt.get("key")).strip()
                        if isinstance(opt, dict)
                        else chr(ord("A") + index)
                        for index, opt in enumerate(question.get("options") or [])
                    ]
                    missing = [key for key in keys if key not in analysis]
                    report = self.warn if (self.template_mode or self.imported) else self.err
                    if missing:
                        report(
                            f"{label} 多选题解析未逐项写出字号与结果对照（缺 {','.join(missing)}），"
                            "答案可能未经验算；要求每个选项都写出「该项结果」"
                        )

                if len(stem) > 300:
                    self.warn(f"{label} 题干长度 {len(stem)} 字，客户端渲染可能不佳")
                for bad in ("如图", "上题", "上表", "见下图"):
                    if bad in stem:
                        self.err(f"{label} 题干含指代「{bad}」，客户端只能渲染题干")
                        break
        return total

    # ---------- 产出规格（题量 / 节均点 / 每点题量 / 难度配比） ----------
    def check_spec(self, data: dict, points: set[str], total: int) -> None:
        """2026-11-09 新增：把「只写在指令文档里」的四条规格变成机检。

        legacy 文件（占位章节清理前的旧样章）一律降级为提醒，避免历史数据刷屏。
        """

        def report(msg: str) -> None:
            if self.legacy:
                self.warn(msg + "｜[legacy] 旧样章内容，按提醒处理，不阻断")
            else:
                self.err(msg)

        # 1) 每个章节（一轮抓的批次）18~28 题
        for chapter in data.get("chapters") or []:
            if not isinstance(chapter, dict):
                continue
            cname = str(chapter.get("name") or "").strip()
            count = len(chapter.get("questions") or [])
            if count and not (CHAPTER_Q_MIN <= count <= CHAPTER_Q_MAX):
                report(
                    f"章节「{cname}」题量 {count} 道，超出每批次 "
                    f"{CHAPTER_Q_MIN}~{CHAPTER_Q_MAX} 道的规格"
                )

        # 2) 每批次新增知识点 3~6 个；section 下既无知识点也无题 → 导入会造空节
        section_names = [
            str(item.get("name") or "").strip()
            for item in (data.get("knowledge") or [])
            if isinstance(item, dict) and item.get("node_type") == "section"
        ]
        per_section = Counter()
        for item in data.get("knowledge") or []:
            if isinstance(item, dict) and item.get("node_type", "point") == "point":
                per_section[str(item.get("parent") or "").strip()] += 1
        for section in section_names:
            if per_section.get(section, 0):
                continue
            direct = 0
            for chapter in data.get("chapters") or []:
                for question in chapter.get("questions") or []:
                    if isinstance(question, dict) and str(question.get("knowledge_point") or "").strip() == section:
                        direct += 1
            if not direct:
                report(f"节「{section}」下既没有知识点也没有题（导入会造出一个空节）")

        # 3) 每个声明的知识点 ≥4 题（0 题也算不合规——此前是最大的盲区）
        used = Counter()
        for chapter in data.get("chapters") or []:
            for question in chapter.get("questions") or []:
                if isinstance(question, dict):
                    used[str(question.get("knowledge_point") or "").strip()] += 1
        if points and not self.book and not (POINTS_PER_FILE_MIN <= len(points) <= POINTS_PER_FILE_MAX):
            report(
                f"本批次新增知识点 {len(points)} 个，超出每批次 "
                f"{POINTS_PER_FILE_MIN}~{POINTS_PER_FILE_MAX} 个的规格"
            )
        for name in sorted(points):
            count = used.get(name, 0)
            if count == 0:
                report(
                    f"知识点「{name}」已声明但一道题都没有挂（等于 0 题，"
                    f"规格要求 ≥{MIN_Q_PER_POINT}）"
                )
            elif count < MIN_Q_PER_POINT:
                report(
                    f"知识点「{name}」只挂了 {count} 道题，低于每知识点 "
                    f"≥{MIN_Q_PER_POINT} 道的规格"
                )

        # 4) 难度配比 40/40/20（±容差，仅提醒）
        if total:
            buckets = Counter()
            for chapter in data.get("chapters") or []:
                for question in chapter.get("questions") or []:
                    if not isinstance(question, dict):
                        continue
                    level = question.get("difficulty", 2)
                    for label, values, _ in DIFFICULTY_BUCKETS:
                        if level in values:
                            buckets[label] += 1
            for label, _, target in DIFFICULTY_BUCKETS:
                percent = 100 * buckets.get(label, 0) / total
                deviation = percent - target * 100
                if abs(deviation) > DIFFICULTY_TOL_PP:
                    self.warn(
                        f"难度 {label} 级占比 {percent:.0f}%，偏离 {target * 100:.0f}% "
                        f"目标 {deviation:+.0f}pp（容差 ±{DIFFICULTY_TOL_PP}pp）"
                    )

        # 5) 题型齐备（仅提醒）
        present = {
            str(question.get("q_type"))
            for chapter in (data.get("chapters") or [])
            for question in (chapter.get("questions") or [])
            if isinstance(question, dict)
        }
        missing = sorted(Q_TYPES - present)
        if missing:
            self.warn(f"缺少题型：{','.join(missing)}（规格要求五种题型齐备）")

    def check_answer(self, question: dict, qtype: str, value, label: str) -> None:
        if qtype in ("choice", "multiple"):
            options = question.get("options") or []
            keys = []
            for index, option in enumerate(options):
                if isinstance(option, dict):
                    key = str(option.get("key") or "").strip()
                    text = str(option.get("text") or "").strip()
                else:
                    key, text = chr(ord("A") + index), str(option).strip()
                if not key or not text:
                    self.err(f"{label} 选项缺 key 或 text")
                keys.append(key)
            if len(keys) < 2 or len(set(keys)) != len(keys):
                self.err(f"{label} 需要 ≥2 个不重复选项，当前 {keys}")
            picked = value if isinstance(value, list) else [value]
            if qtype == "choice" and isinstance(value, list):
                self.err(f"{label} 单选题 answer.value 不能是数组（多选请用 multiple）")
            if qtype == "multiple" and not isinstance(value, list):
                self.err(f"{label} 多选题 answer.value 必须是数组")
            for item in picked:
                if str(item) not in keys:
                    self.err(f"{label} 答案「{item}」不在选项 {keys} 内")
        elif qtype == "judge":
            if str(value) not in {"T", "F"}:
                self.err(f"{label} 判断题 answer.value 只能是 \"T\"/\"F\"，当前 {value!r}")
        elif qtype == "fill":
            if isinstance(value, str) and not value.strip():
                self.err(f"{label} 填空题答案为空")
            if "略" in str(value):
                self.err(f"{label} 填空题答案含「略」，必须可唯一判定")
        elif qtype == "answer":
            if len(str(value).strip()) < 8:
                self.warn(f"{label} 主观题参考答案过短，建议补评分要点")

    def check_arithmetic(self, question: dict, qtype: str, value, label: str) -> None:
        """答案机检：解析里的等式必须算得对；数值型填空必须给算式。"""
        analysis = str(question.get("analysis") or "")
        equations = 0
        for match in _EQ_RE.finditer(analysis):
            lhs, rhs = match.group(1).strip(), match.group(2).strip()
            if not _HAS_OP_RE.search(lhs):
                continue
            sentence = _sentence_at(analysis, match.start())
            if any(bad in sentence for bad in _WRONG_DEMO_WORDS):
                continue  # 解析里故意写的错误示例（如「8+3=5 把总数弄反了」），不判错
            left = safe_eval(lhs)
            if left is None:
                continue
            equations += 1
            right = float(rhs)
            # 按等号右边的位数放宽：写成 0.333 但真值 0.333333 属于合法四舍五入，不算错。
            decimals = len(rhs.split(".")[1]) if "." in rhs else 0
            tol = max(ARITH_TOL, 0.5 * (10 ** (-decimals)))
            if abs(left - right) > tol:
                self.err(
                    f"{label} 解析中的算式不成立：{lhs} = {rhs}，实际为 {left:g}"
                    f"（超出 {tol:g} 的舍入容差，请核对答案）"
                )

        answer_text = "" if value is None else str(value).strip()
        if qtype == "fill" and re.fullmatch(r"-?\d+(?:\.\d+)?", answer_text):
            if not equations:
                self.warn(
                    f"{label} 填空题答案是数值「{answer_text}」，但解析里没有可求值的算式，"
                    "机检无法验算"
                )
        elif qtype in ("choice", "multiple"):
            # 答案若是纯数值选项，要求解析里出现对应的等式结论
            if re.fullmatch(r"-?\d+(?:\.\d+)?", answer_text) and not equations:
                self.warn(
                    f"{label} 答案「{answer_text}」是数值，但解析里没有算式，机检无法验算"
                )


def _manifest_has_path(path: Path, manifest: dict | None) -> bool:
    """manifest 里是否有该文件且曾导入成功（不看 sha）。用于「重名自指」的判定。"""
    if not manifest:
        return False
    parts = path.as_posix()
    for key, value in manifest.items():
        if not isinstance(value, dict):
            continue
        key_posix = str(key).replace("\\", "/").lstrip("./")
        if parts.endswith(key_posix) and value.get("status") == "ok":
            return True
    return False


def _content_sha256(doc: dict) -> str:
    """文档的**内容**哈希：剔除元数据键后按规范 JSON 序列化再哈希。

    与 backend/app/services/content_import.py 里的 content_sha256 同实现——
    改一处必须同步改另一处，否则 manifest 的「仅元数据变更」判定会失效。
    """
    payload = {k: v for k, v in doc.items() if k not in _METADATA_KEYS}
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _manifest_import_state(path: Path, raw: bytes, doc: dict,
                            manifest: dict | None) -> str:
    """该文件相对 manifest 的入库状态，三态：

    ``unchanged``  —— 字节与导入当刻一致（manifest 里 imported_sha256 == 当前 sha）；
                      正常「已入库」，重名/多选闭合按提醒处理。
    ``meta_only``  —— 字节变了但**内容**（剔除元数据键后）没变（如后来打了
                      ``_legacy`` 标记）；仍算「已入库」，但要明确提示已变更。
    ``changed``    —— 内容也变了 → 「文件已变更，未重导」，从严检查（重名报错）。
    ``unknown``    —— manifest 里没有这条记录 / 不是 ok 状态 → 视为未入库。

    manifest 三列语义（2026-11-08 第十一轮整改）：
      ``imported_sha256``       导入当刻的字节 sha，**永不改写**
      ``current_file_sha256``   盘上现值
      ``imported_content_sha256`` 导入当刻剔除元数据后的内容哈希
    旧版 manifest 只有 ``sha256`` 一列 → 按「字节一致才算已入库」处理（向后兼容）。
    """
    if not manifest:
        return "unknown"
    parts = path.as_posix()
    digest = hashlib.sha256(raw).hexdigest()
    for key, value in manifest.items():
        if not isinstance(value, dict):
            continue
        key_posix = str(key).replace("\\", "/").lstrip("./")
        if not parts.endswith(key_posix):
            continue
        if value.get("status") != "ok":
            continue
        imported_sha = str(value.get("imported_sha256") or value.get("sha256") or "")
        if not imported_sha:
            continue
        if imported_sha == digest:
            return "unchanged"
        imported_content = str(value.get("imported_content_sha256") or "")
        if imported_content and imported_content == _content_sha256(doc):
            return "meta_only"
        return "changed"
    return "unknown"


def validate_file(
    path: Path,
    expects: dict,
    kp_baseline: dict | None = None,
    manifest: dict | None = None,
    outlines: dict[str, tuple[dict[int, set[str]], dict[int, set[tuple[str, str]]]]] | None = None,
    version_map: dict | None = None,
) -> Checker:
    checker = Checker()
    checker.kp_baseline = kp_baseline
    raw = path.read_bytes()
    if raw[:3] == b"\xef\xbb\xbf":
        checker.err("文件带 UTF-8 BOM，导入时会解析失败，请保存为无 BOM 的 UTF-8")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        checker.err(f"文件不是合法 UTF-8：{exc}")
        return checker
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        checker.err(f"JSON 解析失败：{exc}")
        return checker
    if not isinstance(data, dict):
        checker.err("顶层必须是 JSON 对象")
        return checker

    # 版本口径按学科查表（各科并不统一：北师大版/人教版/牛津深圳版/部编版/湘教版），
    # 只在没显式传 --expect-version 时生效，避免「人教版」写死导致整批误报。
    if version_map and expects.get("version") is None:
        entry = (version_map.get(str(data.get("subject") or "")) or {})
        resolved = entry.get(str(data.get("grade"))) or entry.get("*") or entry.get("default")
        if resolved:
            expects = dict(expects)
            expects["version"] = resolved

    checker.check_top(data, expects)
    checker.template_mode = path.stem == str(data.get("subject") or "")
    checker.import_state = _manifest_import_state(path, raw, data, manifest)
    checker.imported = checker.import_state in ("unchanged", "meta_only")
    checker.imported_path = _manifest_has_path(path, manifest)
    checker.legacy = bool(data.get("_legacy"))
    checker.book = path.name.lower().endswith("_book.json")
    if checker.book:
        checker.warn(
            "整册归集文件（*_book.json）：「每批次知识点 3~6 个」「每知识点≥4 道」的每日规格不适用，"
            "只按章节题量、题量与结构层校验"
        )
    if checker.template_mode:
        checker.warn(
            "这是学科模板文件（名字就是学科代码），它本身就是库内容的来源；"
            "重名检查降级为提醒，不要拿它当每日产出文件"
        )
    if checker.legacy:
        checker.warn(
            "[legacy] 文件带 `_legacy` 标记：属于占位章节清理前的旧样章内容，"
            "章节名在教材目录上不存在；重导时按 chapter_aliases.json 处理"
            "（aliases 重定向到教材真实章节 / discard 整块丢弃），不会把旧版数据写回库"
        )
    sections, points = checker.check_knowledge(data)
    total = checker.check_questions(data, sections, points)
    checker.check_spec(data, points, total)
    if total > 200:
        checker.warn(f"题目总数 {total} 超过 200，建议按章节拆分")
    if _FRAGMENT_RE.search(path.name):
        checker.warn(
            f"[分片] 文件名带 `_rN` 后缀：导入清单只登记「不带 _rN 的那份」，"
            "分片不会进 manifest、也不会被导入；请改成带章节标识的文件名或合并成一册一文件"
        )

    allowed = None
    allowed_pairs: set[tuple[str, str]] = set()
    if outlines:
        # 按「学科:学期」取大纲，避免上册文件被下册大纲覆盖；旧式「学科」键仅作兜底
        sem = str(getattr(checker, "semester", "") or "")
        entry = outlines.get(f"{checker.subject}:{sem}") or outlines.get(str(checker.subject))
        if entry:
            if isinstance(entry, tuple):
                grade_map, pair_map = entry
                allowed_pairs = (
                    pair_map.get(checker.grade, set())
                    if isinstance(checker.grade, int) else set()
                )
            else:
                grade_map = entry
            if grade_map:
                allowed = grade_map.get(
                    checker.grade if isinstance(checker.grade, int) else -1
                )
    if allowed:
        chapter_names = [str(c.get("name") or "") for c in (data.get("chapters") or [])]
        unit_names = {unit for unit, _ in allowed_pairs}
        # 2026-11-12：板块名 → 归属单元集合。只有「同一个板块名横跨多个单元」才真的无法定位单元；
        # 小学（模块 × 单元）大纲下像「Unit 7 Seasons」这样的单元名本身唯一，不该被当成歧义板块拦下。
        sec_to_units: dict[str, set[str]] = {}
        for unit, sec in allowed_pairs:
            sec_to_units.setdefault(sec, set()).add(unit)
        for name in sorted(sections):
            reason = ""
            if name not in allowed:
                reason = "不在本册教材大纲内"
            elif " / " in name:
                unit, _, sec = name.partition(" / ")
                if allowed_pairs and (unit.strip(), sec.strip()) not in allowed_pairs:
                    reason = "该单元下没有这个板块（单元 × 板块 组合不存在）"
                elif chapter_names and checker.subject == "english":
                    if not any(
                        unit.strip() == cn or unit.strip() in cn or cn in unit.strip()
                        for cn in chapter_names
                    ):
                        reason = "复合名里的单元与本文件 chapters 的单元不一致"
            elif checker.subject == "english" and unit_names and name not in unit_names:
                owners = sec_to_units.get(name, set())
                if len(owners) > 1:
                    reason = (
                        "英语按板块推进时 section 必须写「Unit N 标题 / 板块」复合名；"
                        f"「{name}」这个纯板块名在 {len(owners)} 个单元重复，无法定位单元"
                    )
            if reason:
                msg = (
                    f"章节「{name}」{reason}（本册共 {len(allowed)} 个允许名、"
                    f"{len(allowed_pairs)} 个单元×板块组合，详见 baseline 下的大纲 md）；"
                    "跑出教材范围或串到别的单元会破坏教材完整性与不跳节约束"
                )
                if checker.legacy:
                    # legacy 文件：章节名是旧样章，占位章节清理后已迁移或整章删除，
                    # 不按新内容判失败，只提醒并说明重导时的处置口径。
                    checker.warn(
                        msg + "｜[legacy] 该文件已标 legacy（占位章节清理前的旧样章内容）："
                        "重导时按 chapter_aliases.json 处理——aliases 重定向到教材真实章节、"
                        "discard 整块丢弃，不会把旧版数据写回库"
                    )
                else:
                    checker.err(msg)

    print(f"文件：{path.name}")
    print(f"  节 {len(sections)} 个 / 知识点 {len(points)} 个 / 章节 {len(data.get('chapters') or [])} 个 / 题目 {total} 道")
    if checker.import_state == "unchanged":
        print("  [已入库] 与 manifest 的 imported_sha256 一致，重名/多选闭合按提醒处理（不阻断）")
    elif checker.import_state == "meta_only":
        print("  [已入库·仅元数据变更] 字节与导入当刻不同，但剔除元数据键后内容一致"
              "（如后来补打 `_legacy` 标记）；仍按已入库口径处理（不阻断）")
    elif checker.import_state == "changed":
        print("  [文件已变更·未重导] 内容与导入当刻不同（manifest 的 imported_content_sha256 对不上），"
              "按新版本从严检查（重名/多选闭合报错）")
    for msg in checker.warns:
        print(f"  [提醒] {msg}")
    for msg in checker.errors:
        print(f"  [错误] {msg}")
    print(f"  结论：{'通过' if not checker.errors else f'{len(checker.errors)} 处错误'}")
    return checker


def main() -> int:
    parser = argparse.ArgumentParser(description="每日教研 JSON 自检（不连数据库）")
    parser.add_argument("paths", nargs="+", help="JSON 文件或目录")
    parser.add_argument("--expect-subject", dest="subject")
    parser.add_argument("--expect-grade", dest="grade", type=int)
    parser.add_argument("--expect-version", dest="version")
    parser.add_argument("--expect-semester", dest="semester")
    parser.add_argument(
        "--kp-baseline",
        dest="kp_baseline",
        help="知识点名称基线 JSON（_knowledge-points-baseline_*.json），用于查重名/歧义",
    )
    parser.add_argument(
        "--manifest",
        dest="manifest",
        help="导入清单 _import-manifest.json；命中且 sha256 一致的文件视为已入库，重名/多选闭合降级为提醒",
    )
    parser.add_argument(
        "--outline",
        dest="outline",
        help="教材大纲基线 md（baseline/_outline_*.md）；给了就校验章节是否落在本册教材范围内",
    )
    parser.add_argument(
        "--version-map",
        dest="version_map",
        help=(
            "学科→版本映射 JSON（baseline/_subject-version-map.json）；"
            "不传 --expect-version 时按文件的 subject/grade 自动取版本，"
            "避免各科版本不同导致整批误报"
        ),
    )
    parser.add_argument(
        "--json-out",
        dest="json_out",
        help="机读汇总输出路径：逐文件通过/失败、错误与提醒条数、错误原文（2026-11-10 评审 P0-2）",
    )
    parser.add_argument(
        "--include-quarantined",
        dest="include_quarantined",
        action="store_true",
        help="目录模式下连 *.quarantined.json 一起校验（默认跳过隔离件；显式传路径时不受影响）",
    )
    args = parser.parse_args()

    OutlineEntry = tuple[dict[int, set[str]], dict[int, set[tuple[str, str]]]]
    outlines: dict[str, OutlineEntry] = {}
    outline_dir = Path(__file__).resolve().parent / "baseline"
    candidates = []
    if outline_dir.is_dir():
        candidates.extend(sorted(outline_dir.glob("_outline_*_latest.md")))
        candidates.extend(sorted(outline_dir.glob("_outline_*_2*.md")))
    if args.outline:
        candidates.append(Path(args.outline))  # 本次指定的大纲最后载入，优先于目录快照
    for candidate in candidates:
        if not candidate.is_file():
            if args.outline:
                print(f"大纲文件不存在，已跳过范围校验：{candidate}")
            continue
        subject, grade_map, pair_map = load_outline(candidate)
        if subject:
            sem = ""
            for token in re.split(r"[_\-. ]+", candidate.stem):
                if token in ("first", "second"):
                    sem = token
                    break
            entry = (grade_map, pair_map)
            outlines[f"{subject}:{sem}"] = entry
            outlines.setdefault(str(subject), entry)

    manifest = None
    manifest_path = Path(args.manifest) if args.manifest else None
    if manifest_path is None:
        for candidate in (
            Path("_import-manifest.json"),
            Path(__file__).resolve().parent / "_import-manifest.json",
        ):
            if candidate.is_file():
                manifest_path = candidate
                break
    if manifest_path and manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = data.get("files") if isinstance(data, dict) else None
        except json.JSONDecodeError:
            print(f"导入清单解析失败，已忽略：{manifest_path}")
            manifest = None

    kp_baseline = None
    if args.kp_baseline:
        baseline_path = Path(args.kp_baseline)
        if not baseline_path.is_file():
            print(f"知识点基线不存在：{args.kp_baseline}")
            return 1
        try:
            kp_baseline = json.loads(baseline_path.read_text(encoding="utf-8")).get("names")
        except (json.JSONDecodeError, AttributeError) as exc:
            print(f"知识点基线解析失败：{exc}")
            return 1
        if not kp_baseline:
            print("知识点基线里没有 names 字段")
            return 1

    expects = {
        "subject": args.subject,
        "grade": args.grade,
        "version": args.version,
        "semester": args.semester,
    }

    version_map = None
    if args.version_map:
        map_path = Path(args.version_map)
        if not map_path.is_file():
            print(f"版本映射不存在：{args.version_map}")
            return 1
        try:
            version_map = json.loads(map_path.read_text(encoding="utf-8")).get("versions")
        except (json.JSONDecodeError, AttributeError) as exc:
            print(f"版本映射解析失败：{exc}")
            return 1
        if not version_map:
            print("版本映射里没有 versions 字段")
            return 1

    files: list[Path] = []
    skipped_quarantined: list[str] = []
    for pattern in args.paths:
        target = Path(pattern)
        if target.is_dir():
            for p in sorted(glob.glob(str(target / "**" / "*.json"), recursive=True)):
                name = Path(p).name
                if name.startswith("_"):
                    continue
                if name.endswith(".quarantined.json") and not args.include_quarantined:
                    skipped_quarantined.append(name)
                    continue
                files.append(Path(p))
        elif target.is_file():
            files.append(target)  # 显式传入的路径照常校验，便于单独复核隔离件
        else:
            print(f"路径不存在：{pattern}")
            return 1
    if skipped_quarantined:
        print(f"[隔离] 目录扫描跳过 {len(skipped_quarantined)} 份 *.quarantined.json"
              f"（需要复核请显式传入路径或加 --include-quarantined）")
    if not files:
        print("没有找到可校验的 JSON")
        return 1

    results: list[dict] = []
    failed = 0
    for file in files:
        checker = validate_file(file, expects, kp_baseline, manifest, outlines, version_map)
        if checker.errors:
            failed += 1
        results.append({
            "path": str(file),
            "name": file.name,
            "passed": not checker.errors,
            "errors": len(checker.errors),
            "warnings": len(checker.warns),
            "error_messages": list(checker.errors),
            "import_state": checker.import_state,
            "book": checker.book,
        })

    summary = {
        "schema_version": 1,
        "source": "docs/content-templates/_validate_daily.py",
        "expects": expects,
        "totals": {
            "files": len(files),
            "passed": len(files) - failed,
            "failed": failed,
            "errors": sum(r["errors"] for r in results),
            "warnings": sum(r["warnings"] for r in results),
            "quarantined_skipped": len(skipped_quarantined),
        },
        "quarantined_skipped_names": sorted(skipped_quarantined),
        "files": results,
    }
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[机读汇总] {out}")
        print(f"  逐文件失败清单：{', '.join(r['name'] for r in results if not r['passed']) or '（无）'}")
    print(f"\n合计 {len(files)} 个文件，通过 {len(files) - failed} 个，失败 {failed} 个")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
