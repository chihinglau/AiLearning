"""每日教研 JSON 自检（不连数据库、不执行导入，纯标准库）。

⚠️ **这是 2026-11-08 自动化包的冻结快照，不再生效**。当前生效的校验器是
`docs/content-templates/_validate_daily.py`（见 `tasks.json` 的 `paths.validator`）。
差异（本快照 vs 现行版）：
  - 本快照的「已入库」判定是**单列 `sha256`**（第十一轮已废弃）——现行版是三列语义 +
    三态判定（`unchanged` / `meta_only` / `changed`，见 `_manifest_import_state`）；
  - 本快照**不识别** `_legacy` 标记（第十轮新增）。
仅作历史留痕，勿直接调用。

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
from pathlib import Path

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


def load_outline(path: Path) -> tuple[str | None, dict[int, set[str]]]:
    """解析大纲基线 md：返回 (学科代码, {年级: {允许的单元/章名}})。

    学科代码取自文件名 `_outline_{subject}_…`，用于保证数学大纲不会误拦语文/物理等别的学科。
    """
    subject = None
    for token in re.split(r"[_\-. ]+", path.stem):
        if token in SUBJECTS:
            subject = token
            break
    grades: dict[int, set[str]] = {}
    current: int | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#"):
            current = None
            for cn, num in _CN_NUM.items():
                if f"{cn}年级" in line:
                    current = num
                    grades.setdefault(current, set())
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
        if first in ("—", "") or first.isdigit():
            name = cells[1]
        else:
            name = first
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
    return subject, {grade: names for grade, names in grades.items() if names}


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


class Checker:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warns: list[str] = []
        self.kp_baseline: dict | None = None      # {"math": {"1": {"名称": 次数}}}
        self.subject: str | None = None
        self.grade: int | None = None
        self.template_mode = False                 # 学科模板文件（math.json 等）的重名检查降级为提醒
        self.imported = False                      # 该文件已按当前 sha256 成功入库（重名/多选闭合降级为提醒）
        self.imported_path = False                 # 该路径曾成功入库（内容被改过）：仅重名降级，避免自指误判

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


def _manifest_says_imported(path: Path, raw: bytes, manifest: dict | None) -> bool:
    """该文件是否已按当前内容成功入库。

    命中条件：manifest 里能找到同名相对路径、status=ok、且 sha256 与当前文件一致。
    一旦文件被改过（sha 变化），就视为「未入库的新版本」，从严检查。
    """
    if not manifest:
        return False
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
        if str(value.get("sha256") or "") == digest:
            return True
    return False


def validate_file(
    path: Path,
    expects: dict,
    kp_baseline: dict | None = None,
    manifest: dict | None = None,
    outlines: dict[str, dict[int, set[str]]] | None = None,
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

    checker.check_top(data, expects)
    checker.template_mode = path.stem == str(data.get("subject") or "")
    checker.imported = _manifest_says_imported(path, raw, manifest)
    checker.imported_path = _manifest_has_path(path, manifest)
    if checker.template_mode:
        checker.warn(
            "这是学科模板文件（名字就是学科代码），它本身就是库内容的来源；"
            "重名检查降级为提醒，不要拿它当每日产出文件"
        )
    sections, points = checker.check_knowledge(data)
    total = checker.check_questions(data, sections, points)
    if total > 200:
        checker.warn(f"题目总数 {total} 超过 200，建议按章节拆分")

    allowed = None
    if outlines:
        # 按「学科:学期」取大纲，避免上册文件被下册大纲覆盖；旧式「学科」键仅作兜底
        sem = str(getattr(checker, "semester", "") or "")
        grade_map = outlines.get(f"{checker.subject}:{sem}") or outlines.get(str(checker.subject))
        if grade_map:
            allowed = grade_map.get(checker.grade if isinstance(checker.grade, int) else -1)
    if allowed:
        for name in sorted(sections):
            if name not in allowed:
                report = self_warn = (
                    checker.warn
                    if (checker.template_mode or checker.imported or checker.imported_path)
                    else checker.err
                )
                report(
                    f"章节「{name}」不在本册教材大纲内（本册共 {len(allowed)} 个允许的单元/小节，"
                    "详见 baseline 下的大纲 md）；跑出教材范围会破坏教材完整性"
                )

    print(f"文件：{path.name}")
    print(f"  节 {len(sections)} 个 / 知识点 {len(points)} 个 / 章节 {len(data.get('chapters') or [])} 个 / 题目 {total} 道")
    if checker.imported:
        print("  [已入库] 与 manifest 的 sha256 一致，重名/多选闭合按提醒处理（不阻断）")
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
    args = parser.parse_args()

    outlines: dict[str, dict[int, set[str]]] = {}
    outline_dir = Path(__file__).resolve().parent / "baseline"
    candidates = []
    if args.outline:
        candidates.append(Path(args.outline))
    if outline_dir.is_dir():
        candidates.extend(sorted(outline_dir.glob("_outline_*_latest.md")))
        candidates.extend(sorted(outline_dir.glob("_outline_*_2*.md")))
    for candidate in candidates:
        if not candidate.is_file():
            if args.outline:
                print(f"大纲文件不存在，已跳过范围校验：{candidate}")
            continue
        subject, grade_map = load_outline(candidate)
        if subject:
            sem = ""
            for token in re.split(r"[_\-. ]+", candidate.stem):
                if token in ("first", "second"):
                    sem = token
                    break
            outlines[f"{subject}:{sem}"] = grade_map
            outlines.setdefault(str(subject), grade_map)

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

    files: list[Path] = []
    for pattern in args.paths:
        target = Path(pattern)
        if target.is_dir():
            files.extend(
                Path(p) for p in sorted(glob.glob(str(target / "**" / "*.json"), recursive=True))
                if not Path(p).name.startswith("_")
            )
        elif target.is_file():
            files.append(target)
        else:
            print(f"路径不存在：{pattern}")
            return 1
    if not files:
        print("没有找到可校验的 JSON")
        return 1

    failed = 0
    for file in files:
        if validate_file(file, expects, kp_baseline, manifest, outlines).errors:
            failed += 1
    print(f"\n合计 {len(files)} 个文件，通过 {len(files) - failed} 个，失败 {failed} 个")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
